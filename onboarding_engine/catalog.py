from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Union

from .types import ModuleDef, SkillDef


@dataclass
class SkillCatalog:
    skills: Dict[str, SkillDef]
    modules: Dict[str, ModuleDef]
    module_order: List[str]

    def skill_labels(self) -> Dict[str, str]:
        return {skill_id: skill.label for skill_id, skill in self.skills.items()}


def _load_raw_catalog(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Course catalog not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_catalog(path: Union[str, Path]) -> SkillCatalog:
    raw = _load_raw_catalog(Path(path))
    skills = {
        item["skill_id"]: SkillDef(
            skill_id=item["skill_id"],
            label=item["label"],
            category=item["category"],
            aliases=item.get("aliases", []),
        )
        for item in raw["skills"]
    }
    modules = {
        item["module_id"]: ModuleDef(
            module_id=item["module_id"],
            title=item["title"],
            description=item["description"],
            skills=item.get("skills", []),
            prerequisites=item.get("prerequisites", []),
            duration_hours=float(item.get("duration_hours", 0)),
            difficulty=int(item.get("difficulty", 1)),
            audience_tags=item.get("audience_tags", []),
        )
        for item in raw["modules"]
    }
    module_order = [item["module_id"] for item in raw["modules"]]
    return SkillCatalog(skills=skills, modules=modules, module_order=module_order)
