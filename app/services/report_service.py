"""
Automation reporting service.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.config import settings
from app.core.logging import logger


class ReportService:
    """Persist and read simple automation reports."""

    def save_outreach_report(self, summary: dict[str, Any], *, trigger: str, schedule_name: str) -> dict[str, str]:
        now = datetime.now(timezone.utc)
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        slug = self._slugify(schedule_name or "auto_outreach")
        json_path = settings.REPORT_DIR / f"{timestamp}_{slug}.json"
        csv_path = settings.REPORT_DIR / f"{timestamp}_{slug}.csv"

        report_payload = {
            "generated_at": now.isoformat(),
            "trigger": trigger,
            "schedule_name": schedule_name,
            "summary": summary,
            "quality_funnel": self._build_quality_funnel(summary),
            "validation_reasons": summary.get("validation_reasons", {}),
            "top_prospects_contacted": self._select_top_prospects(summary.get("results", [])),
            "failure_reasons": self._build_failure_reasons(summary.get("results", [])),
        }
        json_path.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        results = summary.get("results", [])
        pd.DataFrame(results).to_csv(csv_path, index=False, encoding="utf-8-sig")

        logger.info(f"Saved outreach report: {json_path}")
        return {"json_path": str(json_path), "csv_path": str(csv_path)}

    def list_reports(self, limit: int = 20) -> list[dict[str, Any]]:
        reports: list[dict[str, Any]] = []
        for path in sorted(settings.REPORT_DIR.glob("*.json"), reverse=True)[:limit]:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                summary = payload.get("summary", {})
                reports.append(
                    {
                        "path": str(path),
                        "generated_at": payload.get("generated_at"),
                        "trigger": payload.get("trigger"),
                        "schedule_name": payload.get("schedule_name"),
                        "raw_found": summary.get("raw_found", summary.get("leads_found", 0)),
                        "leads_found": summary.get("leads_found", 0),
                        "validated_leads": summary.get("validated_leads", 0),
                        "validation_skipped": summary.get("validation_skipped", 0),
                        "contact_ready": summary.get("contact_ready", 0),
                        "leads_saved": summary.get("leads_saved", 0),
                        "email_sent": summary.get("email_sent", 0),
                        "sms_sent": summary.get("sms_sent", 0),
                        "skipped": summary.get("skipped", 0),
                        "failed": summary.get("failed", 0),
                    }
                )
            except Exception as exc:
                logger.warning(f"Could not read report {path}: {exc}")
        return reports

    def load_report(self, path: str | None = None) -> dict[str, Any] | None:
        target = Path(path) if path else next(iter(sorted(settings.REPORT_DIR.glob("*.json"), reverse=True)), None)
        if not target or not target.exists():
            return None
        try:
            return json.loads(target.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning(f"Could not load report {target}: {exc}")
            return None

    def _select_top_prospects(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        contacted = [row for row in results if row.get("send_result") == "SENT"]
        return contacted[:10]

    def _build_failure_reasons(self, results: list[dict[str, Any]]) -> dict[str, int]:
        reasons: dict[str, int] = {}
        for row in results:
            reason = row.get("error") or ""
            if reason:
                reasons[reason] = reasons.get(reason, 0) + 1
        return reasons

    def _build_quality_funnel(self, summary: dict[str, Any]) -> dict[str, int]:
        return {
            "raw_found": int(summary.get("raw_found", summary.get("leads_found", 0)) or 0),
            "validated_leads": int(summary.get("validated_leads", 0) or 0),
            "validation_skipped": int(summary.get("validation_skipped", 0) or 0),
            "contact_ready": int(summary.get("contact_ready", 0) or 0),
            "leads_saved": int(summary.get("leads_saved", 0) or 0),
            "selected": int(summary.get("selected", 0) or 0),
            "email_sent": int(summary.get("email_sent", 0) or 0),
            "sms_sent": int(summary.get("sms_sent", 0) or 0),
            "skipped": int(summary.get("skipped", 0) or 0),
            "failed": int(summary.get("failed", 0) or 0),
        }

    def _slugify(self, value: str) -> str:
        cleaned = "".join(char.lower() if char.isalnum() else "_" for char in value)
        return "_".join(part for part in cleaned.split("_") if part) or "auto_outreach"
