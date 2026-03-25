"""
Tests for automation reporting.
"""
from pathlib import Path

from app.services.report_service import ReportService


def test_report_service_saves_and_lists_reports(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("app.services.report_service.settings.REPORT_DIR", tmp_path)
    service = ReportService()

    paths = service.save_outreach_report(
        {
            "leads_found": 5,
            "validated_leads": 3,
            "validation_skipped": 2,
            "validation_reasons": {"no website": 1, "no contact method": 1},
            "early_stage_businesses": 2,
            "growth_opportunities": 1,
            "high_opportunity_leads": 3,
            "email_sent": 2,
            "sms_sent": 1,
            "skipped": 1,
            "failed": 1,
            "results": [
                {"business_name": "A", "send_result": "SENT", "error": ""},
                {"business_name": "B", "send_result": "FAILED", "error": "smtp_not_configured"},
            ],
        },
        trigger="manual",
        schedule_name="Auto Outreach",
    )

    assert Path(paths["json_path"]).exists()
    assert Path(paths["csv_path"]).exists()

    reports = service.list_reports(limit=5)
    assert len(reports) == 1
    assert reports[0]["raw_found"] == 5
    assert reports[0]["validated_leads"] == 3
    assert reports[0]["contact_ready"] == 0
    assert reports[0]["early_stage_businesses"] == 2
    payload = service.load_report(paths["json_path"])
    assert payload["summary"]["email_sent"] == 2
    assert payload["quality_funnel"]["raw_found"] == 5
    assert payload["quality_funnel"]["high_opportunity_leads"] == 3
    assert payload["validation_reasons"]["no website"] == 1
    assert payload["failure_reasons"]["smtp_not_configured"] == 1
