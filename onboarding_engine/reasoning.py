"""
Grounding Verification and Reasoning Trace System.
Ensures recommendations remain constrained to the approved catalog.
"""

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class ReasoningStep:
    """Single step in the reasoning process"""
    phase: str  # 'extraction', 'gap_analysis', 'module_selection', 'ranking'
    description: str
    details: Dict
    confidence: float  # 0.0 to 1.0


@dataclass
class GroundingCheck:
    """Verification that a recommendation is grounded"""
    module_id: str
    module_title: str
    is_grounded: bool
    source: str  # 'course_catalog'
    confidence: float


class GroundingVerifier:
    """Ensures all recommendations are grounded in the course catalog."""

    def __init__(
        self,
        grounding_db_path: str = "data/grounding_db.json",
        catalog_path: str = "data/course_catalog.json",
    ):
        catalog_path_obj = Path(catalog_path)
        grounding_path_obj = Path(grounding_db_path)

        if not catalog_path_obj.exists():
            raise FileNotFoundError(f"Catalog file not found: {catalog_path_obj}")

        self.catalog = json.loads(catalog_path_obj.read_text(encoding="utf-8"))
        self.grounding_db = {}
        if grounding_path_obj.exists():
            try:
                self.grounding_db = json.loads(grounding_path_obj.read_text(encoding="utf-8"))
            except Exception:
                self.grounding_db = {}

        self.valid_modules = {m["module_id"] for m in self.catalog["modules"]}
        self.valid_skills = {s["skill_id"] for s in self.catalog["skills"]}
        self.module_map = {m["module_id"]: m for m in self.catalog["modules"]}
    
    def verify_module(self, module_id: str) -> GroundingCheck:
        """Verify that a module exists in the catalog."""
        is_grounded = module_id in self.valid_modules
        module = self.module_map.get(module_id, {})

        return GroundingCheck(
            module_id=module_id,
            module_title=module.get("title", "Unknown"),
            is_grounded=is_grounded,
            source="course_catalog" if is_grounded else "unknown",
            confidence=1.0 if is_grounded else 0.0,
        )
    
    def verify_skill(self, skill_id: str) -> bool:
        """Verify that a skill exists in the catalog."""
        return skill_id in self.valid_skills
    
    def verify_pathway(self, module_ids: List[str]) -> Dict:
        """Verify that an entire pathway is grounded."""
        checks = [self.verify_module(m_id) for m_id in module_ids]
        all_grounded = all(c.is_grounded for c in checks)

        return {
            "is_valid": all_grounded,
            "all_grounded": all_grounded,
            "verification_passed": all_grounded,
            "total_modules": len(module_ids),
            "grounded_modules": sum(1 for c in checks if c.is_grounded),
            "source": "course_catalog",
            "module_checks": [asdict(c) for c in checks],
        }
    
    def get_module_info(self, module_id: str) -> Optional[Dict]:
        """Get module information from grounding DB/catalo g if present."""
        modules_map = self.grounding_db.get("modules", {})
        if isinstance(modules_map, dict) and module_id in modules_map:
            return modules_map[module_id]
        return self.module_map.get(module_id)


class ReasoningTracer:
    """Captures and formats reasoning steps."""

    def __init__(self):
        self.steps: List[ReasoningStep] = []
    
    def add_step(self, phase: str, description: str, details: Dict, confidence: float = 1.0):
        """Add a reasoning step"""
        step = ReasoningStep(
            phase=phase,
            description=description,
            details=details,
            confidence=confidence
        )
        self.steps.append(step)
    
    def skill_extraction_step(self, source_type: str, found_skills: List[str], 
                              skill_labels: Dict[str, str], confidence: float):
        """Log skill extraction step"""
        self.add_step(
            phase='skill_extraction',
            description=f'Extracted {len(found_skills)} skills from {source_type}',
            details={
                'source': source_type,
                'skills_found': len(found_skills),
                'skill_list': [
                    {'skill_id': s, 'label': skill_labels.get(s, 'Unknown')}
                    for s in found_skills
                ]
            },
            confidence=confidence
        )
    
    def gap_analysis_step(self, current_skills: List[str], target_skills: List[str],
                          gap_skills: List[str], metric: float):
        """Log gap analysis step"""
        self.add_step(
            phase='gap_analysis',
            description=f'Identified {len(gap_skills)} skill gaps',
            details={
                'current_skills_count': len(current_skills),
                'target_skills_count': len(target_skills),
                'gap_count': len(gap_skills),
                'gap_coverage_score': metric
            },
            confidence=0.95
        )
    
    def module_selection_step(self, selected_module_id: str, module_title: str,
                              rationale: str, skill_coverage: List[str],
                              relevance_score: float):
        """Log module selection step"""
        self.add_step(
            phase='module_selection',
            description=f'Selected module: {module_title}',
            details={
                'module_id': selected_module_id,
                'module_title': module_title,
                'rationale': rationale,
                'covers_skills': skill_coverage,
                'skills_covered_count': len(skill_coverage),
                'relevance_score': relevance_score
            },
            confidence=relevance_score
        )
    
    def ranking_step(self, modules_ranked: List[Dict], total_duration: float,
                     hours_saved: float):
        """Log module ranking step"""
        self.add_step(
            phase='ranking',
            description=f'Ranked {len(modules_ranked)} modules in optimal order',
            details={
                'modules_count': len(modules_ranked),
                'total_duration_hours': total_duration,
                'hours_saved': hours_saved,
                'optimization_factor': hours_saved / total_duration if total_duration > 0 else 0
            },
            confidence=0.9
        )
    
    def get_trace(self) -> List[Dict]:
        """Get formatted reasoning trace"""
        return [asdict(step) for step in self.steps]
    
    def get_summary(self) -> str:
        """Get human-readable summary"""
        lines = ["=== REASONING TRACE ===\n"]
        for i, step in enumerate(self.steps, 1):
            lines.append(f"Step {i}: {step.phase.upper()}")
            lines.append(f"  {step.description}")
            lines.append(f"  Confidence: {step.confidence:.1%}\n")
        return "\n".join(lines)


class HallucinationPreventer:
    """Prevents non-catalog modules/skills from leaking into responses."""

    def __init__(self, grounding_verifier: GroundingVerifier):
        self.verifier = grounding_verifier
    
    def validate_modules(self, modules: List[str]) -> Tuple[List[str], List[str]]:
        """
        Separate valid and invalid modules
        Return: (valid_modules, invalid_modules)
        """
        valid = []
        invalid = []
        for m_id in modules:
            if self.verifier.verify_module(m_id).is_grounded:
                valid.append(m_id)
            else:
                invalid.append(m_id)
        return valid, invalid
    
    def validate_skills(self, skills: List[str]) -> Tuple[List[str], List[str]]:
        """
        Separate valid and invalid skills
        Return: (valid_skills, invalid_skills)
        """
        valid = []
        invalid = []
        for s_id in skills:
            if self.verifier.verify_skill(s_id):
                valid.append(s_id)
            else:
                invalid.append(s_id)
        return valid, invalid
    
    def sanitize_response(self, response: Dict) -> Dict:
        """Ensure response contains only grounded recommendations."""
        roadmap_rows = response.get("roadmap", [])
        cleaned_roadmap = []
        invalid_modules = []

        for row in roadmap_rows:
            if isinstance(row, dict):
                module_id = str(row.get("module_id", "")).strip()
            else:
                module_id = str(row).strip()
                row = {"module_id": module_id}

            if not module_id:
                continue
            if self.verifier.verify_module(module_id).is_grounded:
                cleaned_roadmap.append(row)
            else:
                invalid_modules.append(module_id)

        response["roadmap"] = cleaned_roadmap

        gap_rows = response.get("gaps", [])
        cleaned_gaps = []
        invalid_gaps = []
        for item in gap_rows:
            if not isinstance(item, dict):
                continue
            skill_id = str(item.get("skill_id", "")).strip()
            if not skill_id:
                continue
            if self.verifier.verify_skill(skill_id):
                cleaned_gaps.append(item)
            else:
                invalid_gaps.append(skill_id)
        response["gaps"] = cleaned_gaps

        response["grounding_guard"] = {
            "all_modules_grounded": len(invalid_modules) == 0,
            "invalid_modules_removed": invalid_modules,
            "invalid_skills_removed": invalid_gaps,
            "grounding_source": "course_catalog.json",
        }

        return response
