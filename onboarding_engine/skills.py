from __future__ import annotations

import re
from collections import Counter
from typing import Dict, List, Optional

from .catalog import SkillCatalog
from .types import DocumentProfile, SkillSignal


SOURCE_LEVEL_HINTS = {
    "resume": {
        "expert": 0.97,
        "lead": 0.92,
        "senior": 0.88,
        "advanced": 0.84,
        "proficient": 0.78,
        "strong": 0.74,
        "hands-on": 0.72,
        "working knowledge": 0.66,
        "familiar": 0.55,
        "basic": 0.42,
        "introductory": 0.35,
    },
    "jd": {
        "must have": 0.95,
        "required": 0.92,
        "essential": 0.9,
        "strong": 0.84,
        "proven": 0.8,
        "preferred": 0.68,
        "desired": 0.62,
        "nice to have": 0.5,
        "bonus": 0.45,
        "familiar": 0.55,
        "working knowledge": 0.6,
    },
}


def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[\u2010-\u2015]", "-", text)
    text = re.sub(r"[^a-z0-9+/.\-\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _make_pattern(alias: str) -> re.Pattern[str]:
    escaped = re.escape(alias.lower().strip())
    return re.compile(rf"(?<!\w){escaped}(?!\w)")


def _window(text: str, start: int, end: int, radius: int = 90) -> str:
    left = max(0, start - radius)
    right = min(len(text), end + radius)
    return text[left:right].strip()


def _years_in_window(window: str) -> Optional[float]:
    match = re.search(r"(\d+(?:\.\d+)?)\+?\s+years?", window)
    if match:
        return float(match.group(1))
    return None


def _base_mastery(source: str, window: str, alias: str) -> float:
    hints = SOURCE_LEVEL_HINTS[source]
    score = 0.3 if source == "resume" else 0.5
    lower = window.lower()

    for phrase, value in hints.items():
        if phrase in lower:
            score = max(score, value)

    years = _years_in_window(lower)
    if years is not None:
        if years >= 7:
            score = max(score, 0.96)
        elif years >= 5:
            score = max(score, 0.9)
        elif years >= 3:
            score = max(score, 0.8)
        elif years >= 1:
            score = max(score, 0.65)

    alias_bonus = min(0.18, len(alias.split()) * 0.04)
    score = min(0.98, score + alias_bonus)
    return round(score, 3)


def _confidence(window: str, alias: str, source: str) -> float:
    lower = window.lower()
    confidence = 0.6
    if alias.lower() in lower:
        confidence += 0.15
    if "experience" in lower or "hands-on" in lower:
        confidence += 0.1
    if source == "jd" and ("must have" in lower or "required" in lower or "essential" in lower):
        confidence += 0.15
    if source == "resume" and ("project" in lower or "built" in lower or "led" in lower):
        confidence += 0.12
    return round(min(1.0, confidence), 3)


def _best_signal_for_skill(text: str, source: str, skill_id: str, label: str, aliases: List[str]) -> Optional[SkillSignal]:
    best: Optional[SkillSignal] = None
    normalized = _normalize(text)
    source_multiplier = 1.0 if source == "resume" else 1.15

    for alias in [label, *aliases]:
        alias = alias.strip()
        if not alias:
            continue
        pattern = _make_pattern(alias)
        for match in pattern.finditer(normalized):
            window = _window(normalized, match.start(), match.end())
            mastery = _base_mastery(source, window, alias)
            confidence = _confidence(window, alias, source)
            signal = SkillSignal(
                skill_id=skill_id,
                label=label,
                source=source,
                evidence=window[:220],
                mastery=round(min(1.0, mastery * source_multiplier), 3),
                confidence=confidence,
                weight=round(min(1.0, confidence * mastery), 3),
            )
            if best is None or signal.weight > best.weight:
                best = signal

    return best


def _role_family_from_counts(signals: Dict[str, SkillSignal], catalog: SkillCatalog) -> str:
    counts = Counter()
    for skill_id in signals:
        category = catalog.skills[skill_id].category
        counts[category] += 1

    technical = counts["technical"]
    operations = counts["operations"]
    general = counts["general"]

    if technical >= operations and technical >= general:
        return "technical"
    if operations >= technical and operations >= general:
        return "operations"
    return "general"


def extract_profile(text: str, source: str, catalog: SkillCatalog) -> DocumentProfile:
    signals: Dict[str, SkillSignal] = {}
    for skill_id, skill in catalog.skills.items():
        signal = _best_signal_for_skill(text, source, skill_id, skill.label, skill.aliases)
        if signal:
            signals[skill_id] = signal

    role_family = _role_family_from_counts(signals, catalog)
    summary = {
        "skill_count": float(len(signals)),
        "avg_mastery": round(sum(item.mastery for item in signals.values()) / max(len(signals), 1), 3),
        "avg_confidence": round(sum(item.confidence for item in signals.values()) / max(len(signals), 1), 3),
    }
    return DocumentProfile(source=source, text=text, signals=signals, role_family=role_family, summary=summary)


def evidence_rows(profile: DocumentProfile) -> List[dict]:
    rows = []
    for signal in profile.signals.values():
        rows.append(
            {
                "skill": signal.label,
                "skill_id": signal.skill_id,
                "mastery": signal.mastery,
                "confidence": signal.confidence,
                "weight": signal.weight,
                "evidence": signal.evidence,
            }
        )
    rows.sort(key=lambda row: (row["weight"], row["mastery"]), reverse=True)
    return rows


def blend_profile_with_diagnostic(
    profile: DocumentProfile,
    diagnostic_items: List[dict],
    catalog: SkillCatalog,
) -> DocumentProfile:
    if not diagnostic_items:
        return profile

    merged = dict(profile.signals)

    for item in diagnostic_items:
        raw_skill_id = str(item.get("skill_id", "")).strip()
        if raw_skill_id not in catalog.skills:
            continue

        raw_rating = item.get("self_rating", item.get("rating", 0.0))
        try:
            rating = float(raw_rating)
        except (TypeError, ValueError):
            continue

        if rating > 1.0:
            rating = rating / 100.0
        rating = max(0.0, min(1.0, rating))

        raw_confidence = item.get("confidence", 0.7)
        try:
            diag_conf = float(raw_confidence)
        except (TypeError, ValueError):
            diag_conf = 0.7
        if diag_conf > 1.0:
            diag_conf = diag_conf / 100.0
        diag_conf = max(0.35, min(0.98, diag_conf))

        existing = merged.get(raw_skill_id)
        if existing:
            blended_mastery = round((existing.mastery * 0.65) + (rating * 0.35), 3)
            blended_confidence = round(max(existing.confidence, (existing.confidence * 0.7) + (diag_conf * 0.3)), 3)
            evidence = f"{existing.evidence} | diagnostic self-rating {int(rating * 100)}%"
        else:
            blended_mastery = round(rating, 3)
            blended_confidence = round(0.6 + (diag_conf * 0.25), 3)
            evidence = f"diagnostic self-rating {int(rating * 100)}%"

        merged[raw_skill_id] = SkillSignal(
            skill_id=raw_skill_id,
            label=catalog.skills[raw_skill_id].label,
            source="diagnostic",
            evidence=evidence[:220],
            mastery=blended_mastery,
            confidence=min(1.0, blended_confidence),
            weight=round(min(1.0, blended_mastery * blended_confidence), 3),
        )

    role_family = _role_family_from_counts(merged, catalog)
    summary = {
        "skill_count": float(len(merged)),
        "avg_mastery": round(sum(item.mastery for item in merged.values()) / max(len(merged), 1), 3),
        "avg_confidence": round(sum(item.confidence for item in merged.values()) / max(len(merged), 1), 3),
    }
    return DocumentProfile(
        source=profile.source,
        text=profile.text,
        signals=merged,
        role_family=role_family,
        summary=summary,
    )
