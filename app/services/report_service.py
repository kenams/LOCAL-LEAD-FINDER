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
from app.db.session import SessionLocal
from app.models.prospect import Prospect


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
            "business_snapshot": self._build_business_snapshot(),
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
                        "early_stage_businesses": summary.get("early_stage_businesses", 0),
                        "growth_opportunities": summary.get("growth_opportunities", 0),
                        "high_opportunity_leads": summary.get("high_opportunity_leads", 0),
                        "landing_page_offers": summary.get("landing_page_offers", 0),
                        "website_offers": summary.get("website_offers", 0),
                        "email_sent": summary.get("email_sent", 0),
                        "landing_page_sent": summary.get("landing_page_sent", 0),
                        "website_sent": summary.get("website_sent", 0),
                        "sms_sent": summary.get("sms_sent", 0),
                        "skipped": summary.get("skipped", 0),
                        "failed": summary.get("failed", 0),
                        "responses": payload.get("business_snapshot", {}).get("responses", 0),
                        "interested": payload.get("business_snapshot", {}).get("interested", 0),
                        "won": payload.get("business_snapshot", {}).get("won", 0),
                        "potential_deal_value": payload.get("business_snapshot", {}).get("potential_deal_value", 0.0),
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
            "early_stage_businesses": int(summary.get("early_stage_businesses", 0) or 0),
            "growth_opportunities": int(summary.get("growth_opportunities", 0) or 0),
            "high_opportunity_leads": int(summary.get("high_opportunity_leads", 0) or 0),
            "landing_page_offers": int(summary.get("landing_page_offers", 0) or 0),
            "website_offers": int(summary.get("website_offers", 0) or 0),
            "selected": int(summary.get("selected", 0) or 0),
            "email_sent": int(summary.get("email_sent", 0) or 0),
            "landing_page_sent": int(summary.get("landing_page_sent", 0) or 0),
            "website_sent": int(summary.get("website_sent", 0) or 0),
            "sms_sent": int(summary.get("sms_sent", 0) or 0),
            "skipped": int(summary.get("skipped", 0) or 0),
            "failed": int(summary.get("failed", 0) or 0),
        }

    def _build_business_snapshot(self) -> dict[str, Any]:
        """Build lightweight business-facing performance metrics from stored prospects."""
        db = SessionLocal()
        try:
            prospects = db.query(Prospect).all()
            rows = [
                {
                    "selected_offer_type": prospect.selected_offer_type or "",
                    "send_status": prospect.send_status or "",
                    "response_status": prospect.response_status or "NO_RESPONSE",
                    "potential_deal_value": float(prospect.potential_deal_value or 0.0),
                }
                for prospect in prospects
            ]
            return self._build_business_snapshot_from_rows(rows)
        except Exception as exc:
            logger.warning(f"Could not build business snapshot: {exc}")
            return self._build_business_snapshot_from_rows([])
        finally:
            db.close()

    def _build_business_snapshot_from_rows(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        """Aggregate business metrics that show which offer angles convert better."""
        def is_sent(row: dict[str, Any]) -> bool:
            return str(row.get("send_status") or "").upper() == "SENT"

        def response_bucket(row: dict[str, Any]) -> str:
            return str(row.get("response_status") or "NO_RESPONSE").upper()

        sent_rows = [row for row in rows if is_sent(row)]
        responses = [row for row in sent_rows if response_bucket(row) in {"REPLIED", "INTERESTED", "WON", "LOST"}]
        interested = [row for row in sent_rows if response_bucket(row) in {"INTERESTED", "WON"}]
        won = [row for row in sent_rows if response_bucket(row) == "WON"]
        potential_deal_value = round(sum(float(row.get("potential_deal_value") or 0.0) for row in sent_rows), 2)

        by_offer: dict[str, dict[str, Any]] = {}
        for offer_type in ("landing_page", "website"):
            offer_rows = [row for row in sent_rows if str(row.get("selected_offer_type") or "") == offer_type]
            offer_responses = [row for row in offer_rows if response_bucket(row) in {"REPLIED", "INTERESTED", "WON", "LOST"}]
            offer_interested = [row for row in offer_rows if response_bucket(row) in {"INTERESTED", "WON"}]
            offer_won = [row for row in offer_rows if response_bucket(row) == "WON"]
            sent_count = len(offer_rows)
            by_offer[offer_type] = {
                "sent": sent_count,
                "responses": len(offer_responses),
                "interested": len(offer_interested),
                "won": len(offer_won),
                "reply_rate": round((len(offer_responses) / sent_count) * 100, 2) if sent_count else 0.0,
                "potential_deal_value": round(sum(float(row.get("potential_deal_value") or 0.0) for row in offer_rows), 2),
            }

        sent_count = len(sent_rows)
        return {
            "sent": sent_count,
            "responses": len(responses),
            "interested": len(interested),
            "won": len(won),
            "reply_rate": round((len(responses) / sent_count) * 100, 2) if sent_count else 0.0,
            "potential_deal_value": potential_deal_value,
            "by_offer": by_offer,
        }

    def _slugify(self, value: str) -> str:
        cleaned = "".join(char.lower() if char.isalnum() else "_" for char in value)
        return "_".join(part for part in cleaned.split("_") if part) or "auto_outreach"
