from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

try:
    from supabase import Client, create_client
except Exception:  # pragma: no cover
    Client = None
    create_client = None


class SupabaseStorage:
    """Thin persistence wrapper for onboarding runs."""

    def __init__(
        self,
        url: Optional[str] = None,
        key: Optional[str] = None,
        table_name: str = "onboarding_runs",
    ):
        self.url = url or os.getenv("SUPABASE_URL")
        self.key = key or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        self.table_name = table_name
        self.client: Optional[Client] = None
        self.last_error: Optional[str] = None

        if self.url and self.key and create_client is not None:
            try:
                self.client = create_client(self.url, self.key)
            except Exception as exc:  # pragma: no cover
                self.last_error = str(exc)

    @property
    def enabled(self) -> bool:
        return self.client is not None

    def save_analysis(
        self,
        response: Dict[str, Any],
        source_type: str,
        candidate_name: Optional[str] = None,
        input_meta: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        if not self.enabled:
            return None

        payload = {
            "candidate_name": candidate_name,
            "source_type": source_type,
            "recommended_role_family": response.get("recommended_role_family"),
            "metrics": response.get("metrics", {}),
            "gaps": response.get("gaps", []),
            "roadmap": response.get("roadmap", []),
            "trace": response.get("trace", []),
            "quality_checks": response.get("quality_checks", {}),
            "advanced_metrics": response.get("advanced_metrics", {}),
            "market_insights": response.get("market_insights", {}),
            "resume_signals": response.get("resume_signals", []),
            "jd_signals": response.get("jd_signals", []),
            "input_meta": input_meta or {},
        }

        try:
            result = self.client.table(self.table_name).insert(payload).execute()
            data = getattr(result, "data", None) or []
            if data and isinstance(data, list):
                row = data[0]
                return str(row.get("id") or row.get("run_id") or "")
            return None
        except Exception as exc:
            self.last_error = str(exc)
            return None

    def list_runs(self, limit: int = 20) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []
        try:
            result = (
                self.client.table(self.table_name)
                .select("id,created_at,candidate_name,source_type,recommended_role_family,metrics")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            data = getattr(result, "data", None) or []
            return data if isinstance(data, list) else []
        except Exception as exc:
            self.last_error = str(exc)
            return []

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return None
        try:
            result = self.client.table(self.table_name).select("*").eq("id", run_id).limit(1).execute()
            data = getattr(result, "data", None) or []
            if isinstance(data, list) and data:
                return data[0]
            return None
        except Exception as exc:
            self.last_error = str(exc)
            return None

    def compare_runs(self, run_ids: List[str]) -> Dict[str, Any]:
        if not self.enabled:
            return {"runs": [], "comparison": {}, "available": False}
        if not run_ids:
            return {"runs": [], "comparison": {}, "available": True}
        try:
            result = self.client.table(self.table_name).select("id,created_at,candidate_name,metrics").in_("id", run_ids).execute()
            rows = getattr(result, "data", None) or []
            if not isinstance(rows, list):
                rows = []
            metrics_rows = []
            for row in rows:
                metrics = row.get("metrics", {}) or {}
                metrics_rows.append(
                    {
                        "id": row.get("id"),
                        "candidate_name": row.get("candidate_name"),
                        "created_at": row.get("created_at"),
                        "hours_saved": metrics.get("hours_saved"),
                        "coverage_ratio": metrics.get("coverage_ratio"),
                        "readiness_score": metrics.get("readiness_score"),
                    }
                )

            best = None
            if metrics_rows:
                best = max(metrics_rows, key=lambda item: (item.get("hours_saved") or 0, item.get("coverage_ratio") or 0))

            return {
                "available": True,
                "runs": metrics_rows,
                "comparison": {
                    "best_run_id": best.get("id") if best else None,
                    "best_hours_saved": best.get("hours_saved") if best else None,
                    "best_coverage_ratio": best.get("coverage_ratio") if best else None,
                },
            }
        except Exception as exc:
            self.last_error = str(exc)
            return {"runs": [], "comparison": {}, "available": False}

    def status(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "table_name": self.table_name,
            "url_configured": bool(self.url),
            "key_configured": bool(self.key),
            "last_error": self.last_error,
        }
