from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen


class AzureOpenAIAssistant:
    """Generates coaching suggestions from analysis outputs."""

    def __init__(
        self,
        chat_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout_seconds: int = 20,
    ):
        self.chat_url = chat_url or os.getenv("AZURE_OPENAI_CHAT_URL")
        self.api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
        self.timeout_seconds = timeout_seconds
        self.last_error: Optional[str] = None

    @property
    def enabled(self) -> bool:
        return bool(self.chat_url and self.api_key)

    def _post_chat(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("Assistant is not configured.")

        req = Request(
            self.chat_url,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "api-key": self.api_key,
            },
        )
        with urlopen(req, timeout=self.timeout_seconds) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)

    @staticmethod
    def _extract_text(api_response: Dict[str, Any]) -> str:
        choices = api_response.get("choices", [])
        if not choices:
            return ""
        message = choices[0].get("message", {})
        content = message.get("content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            chunks = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if text:
                        chunks.append(text)
            return "\n".join(chunks)
        return ""

    @staticmethod
    def _extract_json_block(text: str) -> Optional[Dict[str, Any]]:
        if not text:
            return None
        cleaned = text.strip()
        if cleaned.startswith("{") and cleaned.endswith("}"):
            try:
                return json.loads(cleaned)
            except Exception:
                return None

        block_match = re.search(r"\{[\s\S]*\}", cleaned)
        if not block_match:
            return None
        try:
            return json.loads(block_match.group(0))
        except Exception:
            return None

    def _fallback(self, response_payload: Dict[str, Any], reason: str) -> Dict[str, Any]:
        gaps = response_payload.get("gaps", [])[:5]
        roadmap = response_payload.get("roadmap", [])[:4]
        metrics = response_payload.get("metrics", {}) or {}

        suggestions = []
        for item in gaps:
            suggestions.append(
                {
                    "title": f"Close {item.get('skill', item.get('skill_id', 'skill'))} gap",
                    "rationale": f"Current {item.get('current', 0):.2f} vs target {item.get('target', 0):.2f}.",
                    "action": "Use the first roadmap module addressing this gap and schedule a practical assignment.",
                    "priority": "high",
                }
            )

        if roadmap:
            first = roadmap[0]
            suggestions.append(
                {
                    "title": "Start with first milestone",
                    "rationale": f"{first.get('module_id')} unlocks prerequisites for downstream modules.",
                    "action": "Complete this module in the first learning week and validate with a task artifact.",
                    "priority": "high",
                }
            )

        if (metrics.get("hours_saved") or 0) < 5:
            suggestions.append(
                {
                    "title": "Increase path efficiency",
                    "rationale": "Projected time savings are low.",
                    "action": "Use fast-track mode for modules where readiness score is above 0.75.",
                    "priority": "medium",
                }
            )

        return {
            "enabled": self.enabled,
            "source": "fallback",
            "summary": "Generated deterministic coaching tips from skill gaps and roadmap structure.",
            "suggestions": suggestions[:6],
            "follow_up_questions": [
                "Which module should be converted to hands-on practice first?",
                "What competency check will confirm readiness for the target role?",
            ],
            "error": reason,
        }

    def suggest_for_analysis(self, response_payload: Dict[str, Any], max_suggestions: int = 6) -> Dict[str, Any]:
        max_suggestions = max(1, min(max_suggestions, 10))
        if not self.enabled:
            return self._fallback(response_payload, reason="assistant_not_configured")

        metrics = response_payload.get("metrics", {})
        gaps = response_payload.get("gaps", [])[:8]
        roadmap = response_payload.get("roadmap", [])[:10]
        trace = response_payload.get("trace", [])[:5]

        system_prompt = (
            "You are an onboarding coach assistant. Return strict JSON only. "
            "JSON schema: {summary:string, suggestions:[{title:string,rationale:string,action:string,priority:string}], "
            "follow_up_questions:[string]}. No markdown."
        )
        user_prompt = json.dumps(
            {
                "task": "Provide concise, practical coaching suggestions for a candidate onboarding plan.",
                "constraints": {
                    "max_suggestions": max_suggestions,
                    "priorities_allowed": ["high", "medium", "low"],
                    "grounded_to_roadmap": True,
                },
                "analysis": {
                    "recommended_role_family": response_payload.get("recommended_role_family"),
                    "metrics": metrics,
                    "gaps": gaps,
                    "roadmap": roadmap,
                    "trace": trace,
                },
            },
            ensure_ascii=True,
        )

        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "max_completion_tokens": 900,
        }

        try:
            api_response = self._post_chat(payload)
            raw_text = self._extract_text(api_response)
            parsed = self._extract_json_block(raw_text)
            if not parsed:
                return self._fallback(response_payload, reason="assistant_parse_failed")

            suggestions = parsed.get("suggestions", [])
            if not isinstance(suggestions, list):
                suggestions = []

            normalized = []
            for item in suggestions[:max_suggestions]:
                if not isinstance(item, dict):
                    continue
                normalized.append(
                    {
                        "title": str(item.get("title", "")).strip()[:120],
                        "rationale": str(item.get("rationale", "")).strip()[:400],
                        "action": str(item.get("action", "")).strip()[:400],
                        "priority": str(item.get("priority", "medium")).strip().lower()[:10],
                    }
                )

            follow_ups = parsed.get("follow_up_questions", [])
            if not isinstance(follow_ups, list):
                follow_ups = []

            return {
                "enabled": True,
                "source": "azure_openai",
                "summary": str(parsed.get("summary", "")).strip()[:240],
                "suggestions": normalized,
                "follow_up_questions": [str(q).strip()[:180] for q in follow_ups[:4]],
                "error": None,
            }
        except (HTTPError, URLError, TimeoutError, RuntimeError, ValueError) as exc:
            self.last_error = str(exc)
            return self._fallback(response_payload, reason=str(exc))

    def suggest_from_question(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None,
        max_suggestions: int = 5,
    ) -> Dict[str, Any]:
        context_payload = {
            "recommended_role_family": (context or {}).get("recommended_role_family"),
            "metrics": (context or {}).get("metrics", {}),
            "gaps": (context or {}).get("gaps", []),
            "roadmap": (context or {}).get("roadmap", []),
            "trace": (context or {}).get("trace", []),
        }
        context_payload["question"] = question
        return self.suggest_for_analysis(context_payload, max_suggestions=max_suggestions)
