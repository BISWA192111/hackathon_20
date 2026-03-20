from __future__ import annotations

from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except Exception:  # pragma: no cover - optional fallback
    TfidfVectorizer = None
    cosine_similarity = None

from .catalog import SkillCatalog
from .types import AnalysisResult, DocumentProfile, ModuleDef, RoadmapStep


def _module_text(module: ModuleDef) -> str:
    return " ".join([module.title, module.description, " ".join(module.skills), " ".join(module.audience_tags)])


def _candidate_mastery(profile: DocumentProfile, skill_id: str) -> float:
    signal = profile.signals.get(skill_id)
    return signal.mastery if signal else 0.0


def _target_demand(profile: DocumentProfile, skill_id: str) -> float:
    signal = profile.signals.get(skill_id)
    if not signal:
        return 0.0
    return min(1.0, signal.mastery * 1.15)


def _skill_gap_map(resume: DocumentProfile, jd: DocumentProfile, catalog: SkillCatalog) -> Dict[str, Dict[str, float]]:
    gaps: Dict[str, Dict[str, float]] = {}
    for skill_id, target_signal in jd.signals.items():
        target = _target_demand(jd, skill_id)
        current = _candidate_mastery(resume, skill_id)
        gap = round(max(0.0, target - current), 3)
        if gap > 0:
            gaps[skill_id] = {
                "target": round(target, 3),
                "current": round(current, 3),
                "gap": gap,
                "importance": round(target_signal.weight, 3),
                "category_weight": 1.15 if catalog.skills[skill_id].category == "technical" else 1.05 if catalog.skills[skill_id].category == "operations" else 1.0,
            }
    return gaps


def _module_similarity_scores(jd_text: str, modules: List[ModuleDef]) -> Dict[str, float]:
    if not modules:
        return {}
    if TfidfVectorizer is None or cosine_similarity is None:
        return {module.module_id: 0.0 for module in modules}

    corpus = [jd_text] + [_module_text(module) for module in modules]
    vectorizer = TfidfVectorizer(stop_words="english")
    matrix = vectorizer.fit_transform(corpus)
    sims = cosine_similarity(matrix[0:1], matrix[1:]).flatten()
    return {module.module_id: float(score) for module, score in zip(modules, sims)}


def _module_mastery(profile: DocumentProfile, module: ModuleDef) -> float:
    if not module.skills:
        return 0.0
    return round(sum(_candidate_mastery(profile, skill_id) for skill_id in module.skills) / len(module.skills), 3)


def _select_initial_modules(
    gaps: Dict[str, Dict[str, float]],
    catalog: SkillCatalog,
    role_family: str,
    similarity_scores: Dict[str, float],
) -> List[Tuple[str, float]]:
    scored_modules: List[Tuple[str, float]] = []
    for module_id, module in catalog.modules.items():
        covered = [skill_id for skill_id in module.skills if skill_id in gaps]
        if not covered:
            continue
        gap_score = sum(gaps[skill_id]["gap"] * gaps[skill_id]["importance"] * gaps[skill_id]["category_weight"] for skill_id in covered)
        similarity = similarity_scores.get(module_id, 0.0)
        audience_bonus = 0.12 if role_family in module.audience_tags or "general" in module.audience_tags else 0.0
        depth_penalty = 0.02 * len(module.prerequisites)
        total = gap_score + (0.35 * similarity) + audience_bonus - depth_penalty
        scored_modules.append((module_id, total))

    scored_modules.sort(key=lambda item: item[1], reverse=True)
    return scored_modules


def _reachable_prerequisites(module_id: str, catalog: SkillCatalog) -> List[str]:
    required: List[str] = []
    seen = set()
    stack = list(catalog.modules[module_id].prerequisites)
    while stack:
        prereq_id = stack.pop()
        if prereq_id in seen:
            continue
        seen.add(prereq_id)
        if prereq_id in catalog.modules:
            required.append(prereq_id)
            stack.extend(catalog.modules[prereq_id].prerequisites)
    return required


def _topological_order(module_ids: List[str], catalog: SkillCatalog) -> List[str]:
    module_set = set(module_ids)
    indegree = {module_id: 0 for module_id in module_set}
    graph = defaultdict(list)

    for module_id in module_set:
        for prereq in catalog.modules[module_id].prerequisites:
            if prereq in module_set:
                graph[prereq].append(module_id)
                indegree[module_id] += 1

    queue = deque([module_id for module_id in catalog.module_order if module_id in module_set and indegree[module_id] == 0])
    ordered: List[str] = []
    seen = set()

    while queue:
        current = queue.popleft()
        if current in seen:
            continue
        seen.add(current)
        ordered.append(current)
        for nxt in graph[current]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)

    for module_id in catalog.module_order:
        if module_id in module_set and module_id not in ordered:
            ordered.append(module_id)
    return ordered


def _choose_capstone(role_family: str) -> Optional[str]:
    if role_family == "technical":
        return "M402"
    if role_family == "operations":
        return "M403"
    return "M404"


def build_analysis_result(resume: DocumentProfile, jd: DocumentProfile, catalog: SkillCatalog) -> AnalysisResult:
    gaps = _skill_gap_map(resume, jd, catalog)
    similarity_scores = _module_similarity_scores(jd.text, list(catalog.modules.values()))
    role_family = jd.role_family if jd.role_family != "general" else resume.role_family
    scored_modules = _select_initial_modules(gaps, catalog, role_family, similarity_scores)
    top_limit = max(4, min(8, (len(gaps) + 1) // 2 + 2))
    initial_order = [module_id for module_id, score in scored_modules if score >= 0.08][:top_limit]

    selected: Dict[str, ModuleDef] = {}
    selected_ids: List[str] = []

    for module_id in initial_order:
        module = catalog.modules[module_id]
        if module_id not in selected:
            selected[module_id] = module
            selected_ids.append(module_id)
        for prereq_id in _reachable_prerequisites(module_id, catalog):
            if prereq_id not in selected:
                selected[prereq_id] = catalog.modules[prereq_id]
                selected_ids.append(prereq_id)

    capstone = _choose_capstone(role_family)
    if capstone and capstone in catalog.modules and capstone not in selected:
        selected[capstone] = catalog.modules[capstone]
        selected_ids.append(capstone)
        for prereq_id in _reachable_prerequisites(capstone, catalog):
            if prereq_id not in selected:
                selected[prereq_id] = catalog.modules[prereq_id]
                selected_ids.append(prereq_id)

    ordered_ids = _topological_order(selected_ids, catalog)

    roadmap: List[RoadmapStep] = []
    trace: List[Dict[str, str]] = []
    total_hours = 0.0
    covered_gap_skills = set()

    for module_id in ordered_ids:
        module = catalog.modules[module_id]
        readiness = _module_mastery(resume, module)
        addressed = [skill_id for skill_id in module.skills if skill_id in gaps]
        demand_score = round(sum(gaps.get(skill_id, {}).get("gap", 0.0) for skill_id in addressed), 3)
        similarity = round(similarity_scores.get(module_id, 0.0), 3)

        if not module.prerequisites:
            phase = "foundation"
        elif len(module.prerequisites) == 1:
            phase = "core"
        else:
            phase = "validation"

        reason_parts = []
        if addressed:
            reason_parts.append(f"addresses {', '.join(addressed)}")
        if readiness >= 0.72 and not addressed:
            reason_parts.append("candidate already shows partial mastery, so this is a fast-track refresher")
        elif module.prerequisites:
            reason_parts.append(f"requires {', '.join(module.prerequisites)} before advanced application")
        else:
            reason_parts.append("foundational entry point for the selected role path")

        roadmap.append(
            RoadmapStep(
                module_id=module_id,
                title=module.title,
                phase=phase,
                reason="; ".join(reason_parts),
                skills_addressed=addressed,
                estimated_hours=module.duration_hours,
                readiness_score=readiness,
                demand_score=demand_score,
                similarity_score=similarity,
                prerequisites=module.prerequisites,
            )
        )
        total_hours += module.duration_hours
        covered_gap_skills.update(addressed)

    if not roadmap:
        roadmap.append(
            RoadmapStep(
                module_id="M001",
                title="Team Orientation and Success Criteria",
                phase="foundation",
                reason="default orientation path when no explicit gaps are detected",
                skills_addressed=[],
                estimated_hours=2.0,
                readiness_score=0.0,
                demand_score=0.0,
                similarity_score=0.0,
                prerequisites=[],
            )
        )
        total_hours = 2.0

    coverage_ratio = 1.0 if not gaps else round(len(covered_gap_skills) / len(gaps), 3)
    readiness_score = round(sum(_candidate_mastery(resume, skill_id) for skill_id in jd.signals.keys()) / max(len(jd.signals), 1), 3)
    optimized_hours = round(total_hours, 2)
    baseline_hours = round(sum(module.duration_hours for module in catalog.modules.values() if role_family in module.audience_tags or "general" in module.audience_tags), 2)
    hours_saved = round(max(0.0, baseline_hours - optimized_hours), 2)
    residual_gap = round(sum(gap["gap"] for gap in gaps.values()) / max(len(gaps), 1), 3)

    trace.extend(
        [
            {
                "stage": "role_family",
                "detail": f"Detected target role family: {role_family}",
            },
            {
                "stage": "skill_gap",
                "detail": f"Identified {len(gaps)} explicit skill gaps from the job description.",
            },
            {
                "stage": "roadmap_strategy",
                "detail": "Selected modules by maximizing gap coverage, semantic relevance, and prerequisite consistency.",
            },
            {
                "stage": "grounding_guard",
                "detail": "All recommended modules are retrieved from the approved local course catalog.",
            },
            {
                "stage": "efficiency",
                "detail": f"Optimized path estimates {optimized_hours} hours versus {baseline_hours} baseline hours, saving {hours_saved} hours.",
            },
        ]
    )

    metrics = {
        "coverage_ratio": coverage_ratio,
        "readiness_score": readiness_score,
        "optimized_hours": optimized_hours,
        "baseline_hours": baseline_hours,
        "hours_saved": hours_saved,
        "residual_gap": residual_gap,
    }

    return AnalysisResult(
        resume=resume,
        jd=jd,
        gaps=gaps,
        roadmap=roadmap,
        trace=trace,
        metrics=metrics,
        recommended_role_family=role_family,
    )
