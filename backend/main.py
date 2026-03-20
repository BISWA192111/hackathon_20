from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from onboarding_engine import OnboardingEngine
from onboarding_engine.skills import evidence_rows

from .schemas import AnalyzeTextRequest, ApiResponse


ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "data" / "course_catalog.json"
DEMO_PATH = ROOT / "data" / "demo_cases.json"
FRONTEND_DIR = ROOT / "frontend"


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

        if self_rating > 1.0:
            self_rating /= 100.0
        self_rating = max(0.0, min(1.0, self_rating))

        try:
            confidence = float(item.get("confidence", 0.7))
        except (TypeError, ValueError):
            confidence = 0.7

        if confidence > 1.0:
            confidence /= 100.0
        confidence = max(0.0, min(1.0, confidence))

        normalized.append(
            {
                "skill_id": skill_id,
                "self_rating": self_rating,
                "confidence": confidence,
            }
        )
    return normalized


def _serialize_result(result, engine: OnboardingEngine) -> Dict[str, Any]:
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

    return {
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
            "catalog_size": {
                "skills": len(engine.catalog.skills),
                "modules": len(engine.catalog.modules),
            },
        },
    }


def create_app() -> FastAPI:
    app = FastAPI(
        title="Adaptive Onboarding API",
        version="1.0.0",
        description="Python-first backend for skill-gap analysis and adaptive onboarding roadmap generation.",
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

    app.state.engine = engine
    app.state.demo_cases = demo_cases

    @app.get("/api/v1/health")
    async def health() -> Dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/catalog")
    async def catalog() -> Dict[str, Any]:
        skill_rows = []
        for skill_id, skill in engine.catalog.skills.items():
            skill_rows.append(
                {
                    "skill_id": skill_id,
                    "label": skill.label,
                    "category": skill.category,
                    "aliases": skill.aliases,
                }
            )
        module_rows = []
        for module_id, module in engine.catalog.modules.items():
            module_rows.append(
                {
                    "module_id": module_id,
                    "title": module.title,
                    "skills": module.skills,
                    "prerequisites": module.prerequisites,
                    "duration_hours": module.duration_hours,
                    "difficulty": module.difficulty,
                    "audience_tags": module.audience_tags,
                }
            )
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
        result = engine.analyze_texts(
            resume_text=payload.resume_text,
            jd_text=payload.jd_text,
            diagnostic_items=diagnostic,
        )
        return _serialize_result(result, engine)

    @app.post("/api/v1/analyze/files", response_model=ApiResponse)
    async def analyze_files(
        resume_file: UploadFile = File(...),
        jd_file: UploadFile = File(...),
        diagnostic_json: Optional[str] = Form(None),
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
        return _serialize_result(result, engine)

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
            content={
                "detail": "Unexpected server error",
                "error_type": exc.__class__.__name__,
            },
        )

    return app


app = create_app()
