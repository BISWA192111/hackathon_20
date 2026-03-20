"""
Enhanced skill extraction using curated catalog + optional O*NET artifacts.
This module is intentionally deterministic and degrades gracefully when data files are missing.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Dict, List, Optional

from fuzzywuzzy import fuzz


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9+/.\-\s]", " ", text.lower())).strip()


class EnhancedSkillsExtractor:
    def __init__(self, data_path: str = "data"):
        self.data_path = Path(data_path)
        self.catalog = self._load_json("course_catalog.json", default={"skills": [], "modules": []})
        self.onet_profiles = self._load_json("onet_occupation_profiles.json", default=[])
        self.skill_stats = self._load_json("skill_statistics.json", default={})
        self.onet_vocab = self._load_json("onet_skill_vocabulary.json", default={})

        self.skill_map = {item["skill_id"]: item for item in self.catalog.get("skills", [])}
        self.alias_map = self._build_alias_map(self.catalog.get("skills", []))
        self.onet_occupations = self._build_occupation_map(self.onet_profiles)

    def _load_json(self, filename: str, default):
        path = self.data_path / filename
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default

    @staticmethod
    def _build_alias_map(skills: List[dict]) -> Dict[str, str]:
        alias_map: Dict[str, str] = {}
        for skill in skills:
            skill_id = skill["skill_id"]
            label = str(skill.get("label", "")).strip().lower()
            if label:
                alias_map[label] = skill_id
            for alias in skill.get("aliases", []):
                alias_clean = str(alias).strip().lower()
                if alias_clean:
                    alias_map[alias_clean] = skill_id
        return alias_map

    @staticmethod
    def _build_occupation_map(raw_profiles) -> Dict[str, dict]:
        if isinstance(raw_profiles, list):
            return {str(item.get("code", idx)): item for idx, item in enumerate(raw_profiles)}
        if isinstance(raw_profiles, dict):
            mapped = {}
            for key, value in raw_profiles.items():
                if isinstance(value, dict):
                    mapped[str(key)] = value
            return mapped
        return {}

    def _context_from_text(self, normalized_text: str) -> str:
        technical_keywords = {"python", "sql", "api", "cloud", "linux", "testing", "code", "developer"}
        operations_keywords = {"safety", "inventory", "equipment", "quality", "shift", "sop", "compliance"}
        technical_hits = sum(1 for word in technical_keywords if word in normalized_text)
        operations_hits = sum(1 for word in operations_keywords if word in normalized_text)
        if technical_hits > operations_hits:
            return "technical"
        if operations_hits > technical_hits:
            return "operations"
        return "general"

    def extract_with_confidence(self, text: str, context: str = "general") -> Dict[str, Dict]:
        normalized_text = _normalize_text(text)
        found: Dict[str, Dict] = {}

        detected_context = self._context_from_text(normalized_text)
        requested_context = context if context in {"technical", "operations", "general"} else detected_context
        tokens = normalized_text.split()

        for alias, skill_id in self.alias_map.items():
            if not alias:
                continue

            score = 0.0
            sources: List[str] = []

            exact_pattern = re.compile(rf"(?<!\w){re.escape(alias)}(?!\w)")
            if exact_pattern.search(normalized_text):
                score = max(score, 0.94)
                sources.append("alias_exact")

            alias_token_len = len(alias.split())
            if alias_token_len > 1 and len(tokens) >= alias_token_len:
                for idx in range(0, len(tokens) - alias_token_len + 1):
                    window = " ".join(tokens[idx : idx + alias_token_len])
                    fuzzy = fuzz.token_set_ratio(alias, window) / 100.0
                    if fuzzy >= 0.9:
                        score = max(score, 0.85)
                        sources.append("alias_fuzzy")
                        break
            else:
                for token in tokens:
                    fuzzy = fuzz.ratio(alias, token) / 100.0
                    if fuzzy >= 0.92:
                        score = max(score, 0.8)
                        sources.append("token_fuzzy")
                        break

            if score <= 0:
                continue

            skill = self.skill_map.get(skill_id, {})
            category = str(skill.get("category", "general"))
            if category == requested_context:
                score = min(1.0, score + 0.06)
            elif requested_context != "general" and category != requested_context:
                score = max(0.0, score - 0.04)

            if skill_id not in found:
                found[skill_id] = {
                    "name": skill.get("label", skill_id),
                    "confidence": round(score, 3),
                    "sources": sorted(set(sources)),
                    "category": category,
                    "context_match": category == requested_context,
                }
            else:
                found[skill_id]["confidence"] = round(max(found[skill_id]["confidence"], score), 3)
                found[skill_id]["sources"] = sorted(set(found[skill_id]["sources"] + sources))
                found[skill_id]["context_match"] = found[skill_id]["context_match"] or (category == requested_context)

        return dict(sorted(found.items(), key=lambda item: item[1]["confidence"], reverse=True))

    def get_skill_frequency(self, skill_id: str) -> Dict:
        occurrences = self.skill_stats.get("occurrences", {})
        raw_item = occurrences.get(skill_id, 0.0)
        if isinstance(raw_item, dict):
            frequency = float(raw_item.get("frequency", 0.0))
        else:
            try:
                frequency = float(raw_item)
            except Exception:
                frequency = 0.0

        return {"job_frequency": round(frequency, 4), "commonality": self._classify_commonality(frequency)}

    @staticmethod
    def _classify_commonality(frequency: float) -> str:
        if frequency >= 0.5:
            return "very_common"
        if frequency >= 0.3:
            return "common"
        if frequency >= 0.1:
            return "moderate"
        return "rare"

    def _occupation_skill_names(self, profile: dict) -> List[str]:
        names: List[str] = []
        for item in profile.get("skills", []):
            if isinstance(item, dict):
                name = str(item.get("name", "")).strip().lower()
            else:
                name = str(item).strip().lower()
            if name:
                names.append(name)
        return names

    def find_related_occupations(self, skills: List[str], limit: int = 10) -> List[Dict]:
        if not skills or not self.onet_occupations:
            return []

        skill_names = [self.skill_map.get(skill_id, {}).get("label", skill_id).lower() for skill_id in skills]
        results: List[Dict] = []

        for code, profile in self.onet_occupations.items():
            occ_skill_names = self._occupation_skill_names(profile)
            if not occ_skill_names:
                continue

            match_count = 0
            for skill_name in skill_names:
                if any(skill_name in occ_skill for occ_skill in occ_skill_names):
                    match_count += 1

            if match_count <= 0:
                continue

            score = match_count / max(len(skill_names), 1)
            results.append(
                {
                    "code": code,
                    "title": profile.get("title", "Unknown"),
                    "family": profile.get("family", "general"),
                    "match_count": match_count,
                    "score": round(score, 3),
                }
            )

        results.sort(key=lambda item: (item["score"], item["match_count"]), reverse=True)
        return results[:limit]

    def _find_occupations_by_title(self, title_query: str, limit: int = 5) -> List[dict]:
        query = title_query.strip().lower()
        if not query:
            return []
        matched = []
        for _, profile in self.onet_occupations.items():
            title = str(profile.get("title", "")).lower()
            if not title:
                continue
            score = fuzz.token_set_ratio(query, title)
            if score >= 70 or query in title:
                matched.append((score, profile))
        matched.sort(key=lambda item: item[0], reverse=True)
        return [profile for _, profile in matched[:limit]]

    def enhance_skill_profile(self, current_skills: Dict[str, float], target_role: Optional[str] = None) -> Dict:
        recommendations = {"strengths": [], "development_areas": [], "complementary_skills": []}
        for skill_id, mastery in current_skills.items():
            if skill_id not in self.skill_map:
                continue
            payload = {"skill_id": skill_id, "skill_name": self.skill_map[skill_id]["label"], "mastery": round(float(mastery), 3)}
            if mastery >= 0.75:
                recommendations["strengths"].append(payload)
            elif mastery < 0.5:
                recommendations["development_areas"].append(payload)

        if target_role:
            occupation_matches = self._find_occupations_by_title(target_role, limit=1)
            if occupation_matches:
                top_occ = occupation_matches[0]
                occ_skills = self._occupation_skill_names(top_occ)
                for skill_id, skill in self.skill_map.items():
                    if skill_id in current_skills:
                        continue
                    skill_label = skill.get("label", "").lower()
                    if any(skill_label in occ_skill for occ_skill in occ_skills):
                        recommendations["complementary_skills"].append(
                            {
                                "skill_id": skill_id,
                                "skill_name": skill.get("label", skill_id),
                                "rarity": self.get_skill_frequency(skill_id)["commonality"],
                            }
                        )
        recommendations["complementary_skills"] = recommendations["complementary_skills"][:10]
        return recommendations
