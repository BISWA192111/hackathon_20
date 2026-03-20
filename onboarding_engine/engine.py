from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Union

from .catalog import SkillCatalog, load_catalog
from .parsing import extract_text_from_bytes
from .roadmap import build_analysis_result
from .skills import blend_profile_with_diagnostic, extract_profile
from .types import AnalysisResult


class OnboardingEngine:
    def __init__(self, catalog_path: Union[str, Path]):
        self.catalog_path = Path(catalog_path)
        self.catalog: SkillCatalog = load_catalog(self.catalog_path)

    def analyze_texts(
        self,
        resume_text: str,
        jd_text: str,
        diagnostic_items: Optional[List[dict]] = None,
    ) -> AnalysisResult:
        resume = extract_profile(resume_text, "resume", self.catalog)
        if diagnostic_items:
            resume = blend_profile_with_diagnostic(resume, diagnostic_items, self.catalog)
        jd = extract_profile(jd_text, "jd", self.catalog)
        return build_analysis_result(resume, jd, self.catalog)

    def analyze_files(
        self,
        resume_name: str,
        resume_data: bytes,
        jd_name: str,
        jd_data: bytes,
        diagnostic_items: Optional[List[dict]] = None,
    ) -> AnalysisResult:
        resume_text = extract_text_from_bytes(resume_name, resume_data)
        jd_text = extract_text_from_bytes(jd_name, jd_data)
        return self.analyze_texts(resume_text, jd_text, diagnostic_items=diagnostic_items)
