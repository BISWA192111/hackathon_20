from __future__ import annotations

from dataclasses import asdict
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from onboarding_engine import OnboardingEngine
from onboarding_engine.enhanced_extractor import EnhancedSkillsExtractor
from onboarding_engine.metrics import MetricsCalculator
from onboarding_engine.reasoning import GroundingVerifier, HallucinationPreventer
from onboarding_engine.skills import evidence_rows

from .assistant import AzureOpenAIAssistant
from .enhanced_endpoints import OccupationInsightRequest, SkillAnalysisRequest, analyze_skills_enhanced, get_occupation_insights
from .schemas import AnalyzeTextRequest, ApiResponse, AssistantSuggestRequest, CompareRunsRequest, EnhanceRoadmapRequest
from .storage import SupabaseStorage


ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "data" / "course_catalog.json"
DEMO_PATH = ROOT / "data" / "demo_cases.json"
FRONTEND_DIR = ROOT / "frontend"

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except Exception:
    pass


def _load_demo_cases() -> Dict[str, Dict[str, str]]:
    if not DEMO_PATH.exists():
        return {}
    return json.loads(DEMO_PATH.read_text(encoding="utf-8"))


def _normalize_diagnostic(raw_items: List[dict]) -> List[dict]:
    normalized: List[dict] = []
    for item in raw_items:
        skill_id = str(item.get("skill_id", "")).strip()
        if not skill_id:
            continue
        try:
            self_rating = float(item.get("self_rating", item.get("rating", 0.0)))
        except (TypeError, ValueError):
            continue
        try:
            confidence = float(item.get("confidence", 0.7))
        except (TypeError, ValueError):
            confidence = 0.7

        if self_rating > 1.0:
            self_rating /= 100.0
        if confidence > 1.0:
            confidence /= 100.0

        normalized.append(
            {
                "skill_id": skill_id,
                "self_rating": max(0.0, min(1.0, self_rating)),
                "confidence": max(0.0, min(1.0, confidence)),
            }
        )
    return normalized


def _build_advanced_metrics(result, metrics_calculator: MetricsCalculator) -> Dict[str, Any]:
    current_skills = {signal.skill_id: signal.mastery for signal in result.resume.signals.values()}
    target_skills = {signal.skill_id: min(1.0, signal.mastery * 1.15) for signal in result.jd.signals.values()}
    gap_skills = list(result.gaps.keys())
    roadmap_modules = [step.module_id for step in result.roadmap]
    return metrics_calculator.calculate_complete_metrics(
        current_skills=current_skills,
        target_skills=target_skills,
        gap_skills=gap_skills,
        roadmap_modules=roadmap_modules,
    )


def _build_market_insights(result, enhanced_extractor: Optional[EnhancedSkillsExtractor]) -> Dict[str, Any]:
    if enhanced_extractor is None:
        return {
            "enabled": False,
            "message": "Enhanced extractor unavailable in this runtime.",
            "top_gap_skills": [],
            "related_occupations": [],
            "market_value_score": None,
        }

    top_gap_skills = sorted(result.gaps.items(), key=lambda item: item[1]["gap"], reverse=True)[:8]
    skill_ids = [skill_id for skill_id, _ in top_gap_skills]
    frequencies = {skill_id: enhanced_extractor.get_skill_frequency(skill_id) for skill_id in skill_ids}
    related_occupations = enhanced_extractor.find_related_occupations(skill_ids, limit=8)

    commonality_score = {"very_common": 100, "common": 85, "moderate": 60, "rare": 40}
    scores = [commonality_score.get(item["commonality"], 50) for item in frequencies.values()]
    market_value = round(sum(scores) / len(scores), 1) if scores else None

    return {
        "enabled": True,
        "top_gap_skills": [
            {"skill_id": skill_id, "gap": payload["gap"], "market": frequencies.get(skill_id, {})} for skill_id, payload in top_gap_skills
        ],
        "related_occupations": related_occupations,
        "market_value_score": market_value,
    }


def _serialize_result(
    result,
    engine: OnboardingEngine,
    grounding_verifier: Optional[GroundingVerifier],
    metrics_calculator: MetricsCalculator,
    enhanced_extractor: Optional[EnhancedSkillsExtractor],
) -> Dict[str, Any]:
    skill_labels = engine.catalog.skill_labels()
    module_ids = {step.module_id for step in result.roadmap}
    unknown_modules = sorted(module_ids - set(engine.catalog.modules.keys()))

    gaps = []
    for skill_id, payload in sorted(result.gaps.items(), key=lambda item: item[1]["gap"], reverse=True):
        row = {"skill_id": skill_id, "skill": skill_labels.get(skill_id, skill_id)}
        row.update(payload)
        gaps.append(row)

    roadmap_rows: List[Dict[str, Any]] = []
    for index, step in enumerate(result.roadmap, start=1):
        row = asdict(step)
        row["order"] = index
        row["skills_addressed_labels"] = [skill_labels.get(skill_id, skill_id) for skill_id in step.skills_addressed]
        roadmap_rows.append(row)

    grounding_status = {"all_grounded": True, "verification_passed": True, "source": "course_catalog"}
    if grounding_verifier:
        grounding_status = grounding_verifier.verify_pathway([step.module_id for step in result.roadmap])

    response = {
        "recommended_role_family": result.recommended_role_family,
        "metrics": result.metrics,
        "gaps": gaps,
        "roadmap": roadmap_rows,
        "trace": result.trace,
        "resume_signals": evidence_rows(result.resume),
        "jd_signals": evidence_rows(result.jd),
        "quality_checks": {
            "roadmap_modules_in_catalog": len(unknown_modules) == 0,
            "unknown_modules": unknown_modules,
            "catalog_size": {"skills": len(engine.catalog.skills), "modules": len(engine.catalog.modules)},
        },
        "grounding_verification": grounding_status,
        "advanced_metrics": _build_advanced_metrics(result, metrics_calculator),
        "market_insights": _build_market_insights(result, enhanced_extractor),
    }
    return response


def _persist_response(
    storage: SupabaseStorage,
    response: Dict[str, Any],
    source_type: str,
    candidate_name: Optional[str],
    input_meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if not storage.enabled:
        response["storage"] = {"saved": False, "provider": "supabase", "reason": "not_configured"}
        return response

    run_id = storage.save_analysis(
        response=response,
        source_type=source_type,
        candidate_name=candidate_name,
        input_meta=input_meta or {},
    )
    response["storage"] = {
        "saved": bool(run_id),
        "provider": "supabase",
        "run_id": run_id,
        "error": storage.last_error if run_id is None else None,
    }
    return response


def _attach_assistant_suggestions(
    assistant: AzureOpenAIAssistant,
    response: Dict[str, Any],
    max_suggestions: int = 6,
) -> Dict[str, Any]:
    response["assistant"] = assistant.suggest_for_analysis(response, max_suggestions=max_suggestions)
    return response


def create_app() -> FastAPI:
    app = FastAPI(
        title="Adaptive Onboarding API",
        version="2.0.0",
        description="Python-first backend for grounded skill-gap analysis and adaptive onboarding pathways.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    engine = OnboardingEngine(CATALOG_PATH)
    demo_cases = _load_demo_cases()
    grounding_verifier = GroundingVerifier(grounding_db_path=str(ROOT / "data" / "grounding_db.json"), catalog_path=str(CATALOG_PATH))
    hallucination_preventer = HallucinationPreventer(grounding_verifier)
    metrics_calculator = MetricsCalculator(catalog_path=str(CATALOG_PATH))
    storage = SupabaseStorage(
        url=os.getenv("SUPABASE_URL"),
        key=os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY"),
        table_name=os.getenv("SUPABASE_RUNS_TABLE", "onboarding_runs"),
    )
    assistant = AzureOpenAIAssistant(
        chat_url=os.getenv("AZURE_OPENAI_CHAT_URL"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        timeout_seconds=int(os.getenv("AZURE_OPENAI_TIMEOUT_SECONDS", "20")),
    )

    try:
        enhanced_extractor = EnhancedSkillsExtractor(data_path=str(ROOT / "data"))
    except Exception:
        enhanced_extractor = None

    app.state.engine = engine
    app.state.demo_cases = demo_cases
    app.state.grounding_verifier = grounding_verifier
    app.state.hallucination_preventer = hallucination_preventer
    app.state.metrics_calculator = metrics_calculator
    app.state.enhanced_extractor = enhanced_extractor
    app.state.storage = storage
    app.state.assistant = assistant

    @app.get("/api/v1/health")
    async def health() -> Dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/catalog")
    async def catalog() -> Dict[str, Any]:
        skill_rows = [
            {"skill_id": skill_id, "label": skill.label, "category": skill.category, "aliases": skill.aliases}
            for skill_id, skill in engine.catalog.skills.items()
        ]
        module_rows = [
            {
                "module_id": module_id,
                "title": module.title,
                "skills": module.skills,
                "prerequisites": module.prerequisites,
                "duration_hours": module.duration_hours,
                "difficulty": module.difficulty,
                "audience_tags": module.audience_tags,
            }
            for module_id, module in engine.catalog.modules.items()
        ]
        return {"skills": skill_rows, "modules": module_rows}

    @app.get("/api/v1/demo/{scenario}")
    async def demo_pair(scenario: str) -> Dict[str, str]:
        scenario_key = scenario.lower().strip()
        if scenario_key not in demo_cases:
            raise HTTPException(status_code=404, detail="Demo scenario not found.")
        return demo_cases[scenario_key]

    @app.post("/api/v1/analyze/text", response_model=ApiResponse)
    async def analyze_text(payload: AnalyzeTextRequest) -> Dict[str, Any]:
        diagnostic = _normalize_diagnostic([item.model_dump() for item in payload.diagnostic])
        result = engine.analyze_texts(resume_text=payload.resume_text, jd_text=payload.jd_text, diagnostic_items=diagnostic)
        response = _serialize_result(
            result=result,
            engine=engine,
            grounding_verifier=app.state.grounding_verifier,
            metrics_calculator=app.state.metrics_calculator,
            enhanced_extractor=app.state.enhanced_extractor,
        )
        response = app.state.hallucination_preventer.sanitize_response(response)
        response = _attach_assistant_suggestions(app.state.assistant, response, max_suggestions=6)
        return _persist_response(
            storage=app.state.storage,
            response=response,
            source_type="text",
            candidate_name=payload.candidate_name,
            input_meta={"diagnostic_items": len(diagnostic)},
        )

    @app.post("/api/v1/analyze/files", response_model=ApiResponse)
    async def analyze_files(
        resume_file: UploadFile = File(...),
        jd_file: UploadFile = File(...),
        diagnostic_json: Optional[str] = Form(None),
        candidate_name: Optional[str] = Form(None),
    ) -> Dict[str, Any]:
        if not resume_file.filename or not jd_file.filename:
            raise HTTPException(status_code=400, detail="Both resume and job description files are required.")

        diagnostic: List[dict] = []
        if diagnostic_json:
            try:
                parsed = json.loads(diagnostic_json)
            except json.JSONDecodeError as exc:
                raise HTTPException(status_code=400, detail=f"Invalid diagnostic_json: {exc}") from exc
            if not isinstance(parsed, list):
                raise HTTPException(status_code=400, detail="diagnostic_json must be a list.")
            diagnostic = _normalize_diagnostic(parsed)

        resume_bytes = await resume_file.read()
        jd_bytes = await jd_file.read()
        result = engine.analyze_files(
            resume_name=resume_file.filename,
            resume_data=resume_bytes,
            jd_name=jd_file.filename,
            jd_data=jd_bytes,
            diagnostic_items=diagnostic,
        )
        response = _serialize_result(
            result=result,
            engine=engine,
            grounding_verifier=app.state.grounding_verifier,
            metrics_calculator=app.state.metrics_calculator,
            enhanced_extractor=app.state.enhanced_extractor,
        )
        response = app.state.hallucination_preventer.sanitize_response(response)
        response = _attach_assistant_suggestions(app.state.assistant, response, max_suggestions=6)
        return _persist_response(
            storage=app.state.storage,
            response=response,
            source_type="file",
            candidate_name=candidate_name,
            input_meta={
                "resume_filename": resume_file.filename,
                "jd_filename": jd_file.filename,
                "diagnostic_items": len(diagnostic),
            },
        )

    @app.get("/api/v1/storage/status")
    async def storage_status() -> Dict[str, Any]:
        return app.state.storage.status()

    @app.get("/api/v1/runs")
    async def list_runs(limit: int = 20) -> Dict[str, Any]:
        limit = max(1, min(limit, 100))
        return {
            "storage": app.state.storage.status(),
            "runs": app.state.storage.list_runs(limit=limit),
        }

    @app.get("/api/v1/runs/{run_id}")
    async def get_run(run_id: str) -> Dict[str, Any]:
        run = app.state.storage.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found or storage unavailable.")
        return {"run": run}

    @app.post("/api/v1/runs/compare")
    async def compare_runs(payload: CompareRunsRequest) -> Dict[str, Any]:
        return app.state.storage.compare_runs(payload.run_ids)

    @app.post("/api/v1/assistant/suggest")
    async def assistant_suggest(payload: AssistantSuggestRequest) -> Dict[str, Any]:
        context = payload.context or {}
        if payload.run_id:
            stored = app.state.storage.get_run(payload.run_id)
            if stored:
                context = {
                    "recommended_role_family": stored.get("recommended_role_family"),
                    "metrics": stored.get("metrics", {}),
                    "gaps": stored.get("gaps", []),
                    "roadmap": stored.get("roadmap", []),
                    "trace": stored.get("trace", []),
                }
        result = app.state.assistant.suggest_from_question(
            question=payload.question,
            context=context,
            max_suggestions=payload.max_suggestions,
        )
        return {"assistant": result, "context_loaded": bool(context), "run_id": payload.run_id}

    @app.post("/api/v1/assistant/enhance-roadmap")
    async def enhance_roadmap(payload: EnhanceRoadmapRequest) -> Dict[str, Any]:
        """Enhance roadmap based on user feedback via AI chat."""
        try:
            context = payload.context or {}
            user_message = (payload.user_message or "").strip().lower()
            
            if not user_message:
                return {
                    "response_text": "Please ask me a question about your learning roadmap.",
                    "follow_up_question": "What would you like to know?",
                    "enhanced_roadmap": [],
                    "session_id": payload.session_id,
                }
            
            # Get roadmap for context
            roadmap = context.get("current_roadmap", [])
            role_family = context.get("role_family", "Unknown Role")
            metrics = context.get("metrics", {})
            
            # Intelligent response system based on question type
            response_text = ""
            follow_up = ""
            
            # Check question type and provide smart response
            if any(word in user_message for word in ["resource", "material", "book", "course", "tutorial", "guide", "video", "youtube", "udemy", "coursera", "linkedin"]):
                # Resources question
                modules_list = ", ".join([m.get("title", m.get("module_id", "Unknown")) for m in roadmap[:5]]) if roadmap else "foundational modules"
                response_text = f"""Great question! Here are the recommended learning resources for your {role_family} role:

**For {modules_list}:**
- 📚 **Online Courses:** Coursera, Udemy, and LinkedIn Learning have comprehensive courses on these topics
- 📺 **YouTube:** Search for "{role_family} learning path" and "[skill name] tutorial" for hands-on demos
- 📖 **Documentation:** Official docs for each technology (Python.org, Git Documentation, SQL tutorials)
- 🎓 **Interactive:** Codecademy, freeCodeCamp, and Pluralsight for hands-on practice
- 💼 **Communities:** Stack Overflow, Reddit, and GitHub for real-world examples

I'd recommend starting with the **highest priority modules** first (Team Orientation, then Version Control). Use YouTube for visual learning, official docs for reference, and Coursera for structured learning."""
                follow_up = "Would you prefer free resources or paid courses with certifications?"
                
            elif any(word in user_message for word in ["time", "how long", "timeline", "duration", "hours", "days", "weeks", "schedule", "fast"]):
                # Time/Timeline question
                total_hours = sum(float(m.get("estimated_hours", 0)) for m in roadmap) if roadmap else 0
                response_text = f"""Based on your roadmap for {role_family}:

**Total Learning Time:** ~{total_hours:.1f} hours ({total_hours/40:.1f} weeks at 40 hrs/week, or {total_hours/10:.1f} weeks at 10 hrs/week)

**Module Breakdown:**
"""
                if roadmap:
                    for i, module in enumerate(roadmap[:5], 1):
                        response_text += f"- {module.get('title', module.get('module_id', 'Unknown'))}: {module.get('estimated_hours', 0):.1f} hours\n"
                
                response_text += f"""
**Recommended Pace:**
- 🚀 **Intensive:** 4 weeks (10 hrs/day) - for full-time learners
- ⚡ **Moderate:** 8 weeks (5 hrs/day) - balanced with work
- 📅 **Flexible:** 12+ weeks (2-3 hrs/day) - self-paced learning

Start with high-priority modules first to see quick wins and build momentum."""
                follow_up = f"How many hours per week can you dedicate to learning?"
                
            elif any(word in user_message for word in ["skill", "gap", "learn", "master", "improve", "focus"]):
                # Skills/Learning gaps question
                gaps = context.get("gaps", [])
                top_skills = sorted(gaps, key=lambda x: x.get("gap", 0), reverse=True)[:3] if gaps else []
                
                response_text = f"""Your key skill gaps for {role_family}:\n"""
                if top_skills:
                    for i, gap in enumerate(top_skills, 1):
                        response_text += f"{i}. **{gap.get('skill', 'Unknown')}** - Gap: {gap.get('gap', 0):.2f}\n"
                else:
                    response_text += "Based on your analysis, focus on:\n1. **Communication & Documentation**\n2. **Version Control (Git)**\n3. **SQL & Data Handling**\n"
                
                response_text += f"""
My recommendation: **Start with Team Orientation** (communication skills), then **Version Control** (Git/Linux), then **SQL**. These form your foundation.

Each subsequent module depends on these fundamentals, so mastering them first will make everything else easier."""
                follow_up = "Which of these skills do you already have some experience with?"
                
            elif any(word in user_message for word in ["first", "start", "begin", "order", "sequence", "priority"]):
                # Learning order/priority question
                response_text = f"""Your recommended learning order for {role_family}:\n\n"""
                if roadmap:
                    for i, module in enumerate(roadmap[:5], 1):
                        priority = module.get("priority_score", 0)
                        reason = module.get("reason", "Important foundational skill")
                        response_text += f"**{i}. {module.get('title', module.get('module_id', 'Unknown'))}** ({module.get('estimated_hours', 0):.1f}h)\n"
                        response_text += f"   Why: {reason}\n"
                        response_text += f"   Priority Score: {priority:.2f}\n\n"
                else:
                    response_text = "Start with foundational skills like communication, version control, and SQL, then advance to specialized topics."
                
                response_text += "Follow this sequence because each module builds on the previous one. Don't skip the fundamentals!"
                follow_up = "Do you want to skip any modules or focus on specific ones first?"
                
            elif any(word in user_message for word in ["practice", "project", "build", "exercise", "hands-on", "real"]):
                # Hands-on practice question
                response_text = f"""To practice your {role_family} roadmap:

**For each module:**
1. 📝 **Learn the theory** (watch tutorials, read docs)
2. 💻 **Do hands-on exercises** (coding challenges, labs)
3. 🏗️ **Build a project** (apply what you learned)
4. 📊 **Review code quality** (best practices, refactoring)

**Project Ideas:**
- Create a Git workflow with branching and merging
- Build a database schema and write SQL queries  
- Automate tasks with Python scripts
- Set up cloud security configurations

**Practice Platforms:**
- LeetCode, HackerRank (coding challenges)
- GitHub (version control practice)
- Kaggle (data challenges)
- Your own projects (most valuable!)

My advice: Start coding from Day 1! Theory alone won't make you proficient."""
                follow_up = "Would you like project ideas for any specific module?"
                
            elif any(word in user_message for word in ["feedback", "progress", "assessment", "test", "ready", "check"]):
                # Progress/Assessment question
                readiness = metrics.get("readiness_score", 0)
                response_text = f"""Your Learning Progress for {role_family}:

**Current Status:**
- 📊 Readiness Score: {readiness*100:.1f}%
- 📈 Learning Path: {len(roadmap)} modules queued
- ✅ Expected Readiness After Completion: ~90%

**Milestones to Track:**
1. ✓ After Team Orientation → Understand expectations and communication norms
2. ✓ After Version Control → Comfortable with Git workflows
3. ✓ After SQL → Can query and manage databases
4. ✓ After Security → Know security best practices
5. ✓ After Python → Automate routine tasks

**How to Assess Your Progress:**
- Complete exercises and quizzes in each module
- Build small projects after every 2-3 modules
- Review code with peers or mentors
- Track time spent vs. estimated hours

Keep going! Your structured roadmap ensures comprehensive learning."""
                follow_up = "Would you like to adjust any modules based on your experience?"
                
            else:
                # Default intelligent response
                top_module = roadmap[0] if roadmap else {}
                response_text = f"""I'm your learning path advisor for {role_family}!

Based on your analysis, I've created a personalized roadmap with {len(roadmap)} modules. 

**Quick Facts:**
- 🎯 Total Learning Time: ~{sum(float(m.get('estimated_hours', 0)) for m in roadmap):.1f} hours
- 📚 Starting Module: {top_module.get('title', top_module.get('module_id', 'Fundamentals'))}
- 💪 By completion: You'll be ready for your target role

You can ask me about:
- **Learning Resources** (books, courses, tutorials)
- **Time Estimates** (how long will this take?)
- **Skill Gaps** (what do I need to learn?)
- **Learning Order** (what should I start with?)
- **Practice Tips** (how do I practice?)
- **Progress** (how am I doing?)
"""
                follow_up = "What would you like to know more about?"
            
            # Build enhanced roadmap
            enhanced_roadmap = []
            if isinstance(context.get("current_roadmap"), list):
                enhanced_roadmap = context["current_roadmap"][:10]
            
            return {
                "response_text": response_text,
                "follow_up_question": follow_up,
                "enhanced_roadmap": enhanced_roadmap,
                "session_id": payload.session_id,
            }
        
        except Exception as e:
            # Return graceful fallback
            return {
                "response_text": "I'd be happy to help with your learning path! You can ask me about resources, time requirements, skill gaps, learning order, practice tips, or your progress.",
                "follow_up_question": "What specific skills would you like to develop?",
                "enhanced_roadmap": [],
                "session_id": payload.session_id,
                "error": str(e),
            }

    @app.post("/api/v1/skills/analyze-enhanced")
    async def skills_analyze_enhanced(payload: SkillAnalysisRequest) -> Dict[str, Any]:
        return await analyze_skills_enhanced(payload, extractor=app.state.enhanced_extractor)

    @app.post("/api/v1/occupations/insights")
    async def occupations_get_insights(payload: OccupationInsightRequest) -> Dict[str, Any]:
        return await get_occupation_insights(payload, extractor=app.state.enhanced_extractor)

    @app.get("/api/v1/training-data/summary")
    async def get_training_summary() -> Dict[str, Any]:
        extractor = app.state.enhanced_extractor
        occupations_loaded = len(extractor.onet_occupations) if extractor else 0
        return {
            "occupations_loaded": occupations_loaded,
            "skills_indexed": len(app.state.engine.catalog.skills),
            "data_assets": {
                "skill_statistics": (ROOT / "data" / "skill_statistics.json").exists(),
                "occupation_profiles": (ROOT / "data" / "onet_occupation_profiles.json").exists(),
                "grounding_database": (ROOT / "data" / "grounding_db.json").exists(),
            },
        }

    if FRONTEND_DIR.exists():
        static_dir = FRONTEND_DIR / "static"
        if static_dir.exists():
            app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

        @app.get("/", include_in_schema=False)
        async def frontend_root() -> FileResponse:
            return FileResponse(FRONTEND_DIR / "index.html")

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"detail": "Unexpected server error", "error_type": exc.__class__.__name__},
        )

    return app


app = create_app()
