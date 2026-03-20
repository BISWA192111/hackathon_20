from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class SkillSignal:
    skill_id: str
    label: str
    source: str
    evidence: str
    mastery: float
    confidence: float
    weight: float


@dataclass(frozen=True)
class SkillDef:
    skill_id: str
    label: str
    category: str
    aliases: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ModuleDef:
    module_id: str
    title: str
    description: str
    skills: List[str]
    prerequisites: List[str]
    duration_hours: float
    difficulty: int
    audience_tags: List[str]


@dataclass
class DocumentProfile:
    source: str
    text: str
    signals: Dict[str, SkillSignal]
    role_family: str
    summary: Dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class RoadmapStep:
    module_id: str
    title: str
    phase: str
    reason: str
    skills_addressed: List[str]
    estimated_hours: float
    readiness_score: float
    demand_score: float
    similarity_score: float
    prerequisites: List[str]


@dataclass
class AnalysisResult:
    resume: DocumentProfile
    jd: DocumentProfile
    gaps: Dict[str, Dict[str, float]]
    roadmap: List[RoadmapStep]
    trace: List[Dict[str, str]]
    metrics: Dict[str, float]
    recommended_role_family: str
