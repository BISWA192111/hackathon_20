from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DiagnosticItem(BaseModel):
    skill_id: str = Field(..., min_length=1)
    self_rating: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)


class AnalyzeTextRequest(BaseModel):
    candidate_name: Optional[str] = Field(default=None, max_length=120)
    resume_text: str = Field(..., min_length=10)
    jd_text: str = Field(..., min_length=10)
    diagnostic: List[DiagnosticItem] = Field(default_factory=list)


class CompareRunsRequest(BaseModel):
    run_ids: List[str] = Field(..., min_length=2, max_length=10)


class AssistantSuggestRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000)
    run_id: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    max_suggestions: int = Field(default=5, ge=1, le=10)


class EnhanceRoadmapRequest(BaseModel):
    user_message: str = Field(..., min_length=1, max_length=1000)
    context: Dict[str, Any] = Field(default_factory=dict)
    session_id: Optional[str] = None


class ApiResponse(BaseModel):
    recommended_role_family: str
    metrics: Dict[str, float]
    gaps: List[Dict[str, Any]]
    roadmap: List[Dict[str, Any]]
    trace: List[Dict[str, str]]
    resume_signals: List[Dict[str, Any]]
    jd_signals: List[Dict[str, Any]]
    quality_checks: Dict[str, Any]
    grounding_verification: Optional[Dict[str, Any]] = None
    grounding_guard: Optional[Dict[str, Any]] = None
    advanced_metrics: Optional[Dict[str, Any]] = None
    market_insights: Optional[Dict[str, Any]] = None
    storage: Optional[Dict[str, Any]] = None
    assistant: Optional[Dict[str, Any]] = None
