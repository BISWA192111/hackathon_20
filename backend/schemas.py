from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DiagnosticItem(BaseModel):
    skill_id: str = Field(..., min_length=1)
    self_rating: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)


class AnalyzeTextRequest(BaseModel):
    resume_text: str = Field(..., min_length=10)
    jd_text: str = Field(..., min_length=10)
    diagnostic: List[DiagnosticItem] = Field(default_factory=list)


class ApiResponse(BaseModel):
    recommended_role_family: str
    metrics: Dict[str, float]
    gaps: List[Dict[str, Any]]
    roadmap: List[Dict[str, Any]]
    trace: List[Dict[str, str]]
    resume_signals: List[Dict[str, Any]]
    jd_signals: List[Dict[str, Any]]
    quality_checks: Dict[str, Any]
