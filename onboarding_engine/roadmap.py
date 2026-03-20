from __future__ import annotations

from collections import defaultdict, deque
from typing import Dict, List, Optional, Set, Tuple

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except Exception:  # pragma: no cover
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
        if gap <= 0:
            continue
        category_weight = (
            1.15 if catalog.skills[skill_id].category == "technical" else 1.08 if catalog.skills[skill_id].category == "operations" else 1.0
        )
        gaps[skill_id] = {
            "target": round(target, 3),
            "current": round(current, 3),
            "gap": gap,
            "importance": round(target_signal.weight, 3),
            "category_weight": category_weight,
        }
    return gaps


def _module_similarity_scores(jd_text: str, modules: List[ModuleDef]) -> Dict[str, float]:
    if not modules or TfidfVectorizer is None or cosine_similarity is None:
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


def _gap_priority(gaps: Dict[str, Dict[str, float]], skill_id: str) -> float:
    payload = gaps.get(skill_id)
    if not payload:
        return 0.0
    return payload["gap"] * payload["importance"] * payload["category_weight"]


def _prereq_closure(module_id: str, catalog: SkillCatalog) -> List[str]:
    closure: List[str] = []
    stack = list(catalog.modules[module_id].prerequisites)
    seen = set()
    while stack:
        prereq_id = stack.pop()
        if prereq_id in seen:
            continue
        seen.add(prereq_id)
        if prereq_id in catalog.modules:
            closure.append(prereq_id)
            stack.extend(catalog.modules[prereq_id].prerequisites)
    return closure


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


def _role_relevant_modules(catalog: SkillCatalog, role_family: str) -> Set[str]:
    selected = set()
    for module_id, module in catalog.modules.items():
        if role_family in module.audience_tags or "general" in module.audience_tags:
            selected.add(module_id)
    return selected


def _select_modules_adaptive(
    gaps: Dict[str, Dict[str, float]],
    catalog: SkillCatalog,
    role_family: str,
    similarity_scores: Dict[str, float],
) -> Tuple[List[str], Dict[str, float], List[Dict[str, str]]]:
    """Weighted marginal-gain selector with prerequisite-aware cost."""
    role_modules = _role_relevant_modules(catalog, role_family)
    remaining_gap_skills = set(gaps.keys())
    total_gap_weight = sum(_gap_priority(gaps, skill_id) for skill_id in remaining_gap_skills)
    coverage_target = total_gap_weight * 0.9

    selected = set()
    selected_list: List[str] = []
    module_priority_scores: Dict[str, float] = {}
    selection_trace: List[Dict[str, str]] = []
    covered_weight = 0.0

    candidate_ids = [module_id for module_id in catalog.module_order if module_id in role_modules]
    max_steps = max(5, min(10, len(gaps) + 3))
    step = 0

    while step < max_steps and candidate_ids and remaining_gap_skills and covered_weight < coverage_target:
        step += 1
        best_module_id = None
        best_total_score = -1.0
        best_detail = ""
        best_new_skills: List[str] = []

        for module_id in candidate_ids:
            if module_id in selected:
                continue
            module = catalog.modules[module_id]
            module_skills = [skill_id for skill_id in module.skills if skill_id in gaps]
            if not module_skills:
                continue

            new_skills = [skill_id for skill_id in module_skills if skill_id in remaining_gap_skills]
            if not new_skills:
                continue

            marginal_gap_gain = sum(_gap_priority(gaps, skill_id) for skill_id in new_skills)
            similarity = similarity_scores.get(module_id, 0.0)
            audience_bonus = 0.1 if role_family in module.audience_tags else 0.04 if "general" in module.audience_tags else 0.0

            closure = [pr for pr in _prereq_closure(module_id, catalog) if pr not in selected]
            closure_hours = sum(catalog.modules[pr].duration_hours for pr in closure)
            duration_cost = module.duration_hours + (0.55 * closure_hours)
            if duration_cost <= 0:
                duration_cost = 0.1

            total_score = (marginal_gap_gain + (0.3 * similarity) + audience_bonus) / duration_cost
            if total_score > best_total_score:
                best_total_score = total_score
                best_module_id = module_id
                best_new_skills = new_skills
                best_detail = (
                    f"gain={marginal_gap_gain:.3f}, sim={similarity:.3f}, audience_bonus={audience_bonus:.2f}, "
                    f"duration_cost={duration_cost:.2f}, score={total_score:.3f}"
                )

        if not best_module_id:
            break

        selected.add(best_module_id)
        selected_list.append(best_module_id)
        module_priority_scores[best_module_id] = round(best_total_score, 3)

        closure_ids = _prereq_closure(best_module_id, catalog)
        for prereq_id in closure_ids:
            if prereq_id not in selected:
                selected.add(prereq_id)
                selected_list.append(prereq_id)
                module_priority_scores[prereq_id] = round(max(0.01, best_total_score * 0.4), 3)

        for skill_id in best_new_skills:
            if skill_id in remaining_gap_skills:
                covered_weight += _gap_priority(gaps, skill_id)
                remaining_gap_skills.remove(skill_id)

        selection_trace.append(
            {
                "stage": "module_pick",
                "detail": f"Selected {best_module_id} with {best_detail}. Newly covered skills: {', '.join(best_new_skills)}",
            }
        )

    return selected_list, module_priority_scores, selection_trace


def _phase_for_module(module_id: str, module: ModuleDef, capstone_id: Optional[str]) -> str:
    if capstone_id and module_id == capstone_id:
        return "capstone"
    if not module.prerequisites:
        return "foundation"
    if len(module.prerequisites) == 1:
        return "core"
    return "specialization"


def build_analysis_result(resume: DocumentProfile, jd: DocumentProfile, catalog: SkillCatalog) -> AnalysisResult:
    gaps = _skill_gap_map(resume, jd, catalog)
    similarity_scores = _module_similarity_scores(jd.text, list(catalog.modules.values()))
    role_family = jd.role_family if jd.role_family != "general" else resume.role_family

    selected_ids, module_priority_scores, selection_trace = _select_modules_adaptive(gaps, catalog, role_family, similarity_scores)
    capstone = _choose_capstone(role_family)
    if capstone and capstone in catalog.modules and capstone not in selected_ids:
        selected_ids.append(capstone)
        module_priority_scores[capstone] = module_priority_scores.get(capstone, 0.2)
        for prereq_id in _prereq_closure(capstone, catalog):
            if prereq_id not in selected_ids:
                selected_ids.append(prereq_id)
                module_priority_scores[prereq_id] = module_priority_scores.get(prereq_id, 0.1)

    ordered_ids = _topological_order(selected_ids, catalog)

    roadmap: List[RoadmapStep] = []
    trace: List[Dict[str, str]] = []
    total_hours = 0.0
    covered_gap_skills = set()
    role_module_set = _role_relevant_modules(catalog, role_family)

    for module_id in ordered_ids:
        module = catalog.modules[module_id]
        readiness = _module_mastery(resume, module)
        addressed = [skill_id for skill_id in module.skills if skill_id in gaps]
        demand_score = round(sum(gaps.get(skill_id, {}).get("gap", 0.0) for skill_id in addressed), 3)
        similarity = round(similarity_scores.get(module_id, 0.0), 3)
        priority = round(module_priority_scores.get(module_id, 0.0), 3)
        phase = _phase_for_module(module_id, module, capstone)
        learning_mode = "fast-track" if readiness >= 0.72 else "deep-dive"

        reason_parts = []
        if addressed:
            reason_parts.append(f"closes gaps in {', '.join(addressed)}")
        if module.prerequisites:
            reason_parts.append(f"depends on {', '.join(module.prerequisites)}")
        if learning_mode == "fast-track":
            reason_parts.append("candidate already has partial mastery so delivery can be compressed")
        reason_parts.append(f"priority score {priority:.2f}")

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
                priority_score=priority,
                learning_mode=learning_mode,
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
                priority_score=0.0,
                learning_mode="fast-track",
                prerequisites=[],
            )
        )
        total_hours = 2.0

    coverage_ratio = 1.0 if not gaps else round(len(covered_gap_skills) / len(gaps), 3)
    readiness_score = round(sum(_candidate_mastery(resume, skill_id) for skill_id in jd.signals.keys()) / max(len(jd.signals), 1), 3)
    optimized_hours = round(total_hours, 2)
    baseline_hours = round(sum(catalog.modules[module_id].duration_hours for module_id in role_module_set), 2)
    hours_saved = round(max(0.0, baseline_hours - optimized_hours), 2)
    residual_gap = round(sum(gap["gap"] for gap in gaps.values()) / max(len(gaps), 1), 3)

    trace.extend(
        [
            {"stage": "role_family", "detail": f"Detected target role family: {role_family}"},
            {"stage": "skill_gap", "detail": f"Identified {len(gaps)} explicit skill gaps from the job description."},
            {
                "stage": "adaptive_selector",
                "detail": "Used weighted marginal-gain selection with prerequisite-aware cost to balance impact and time.",
            },
        ]
    )
    trace.extend(selection_trace)
    trace.extend(
        [
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
