"""
Tests for automation reporting.
"""
from pathlib import Path

from app.services.report_service import ReportService


def test_report_service_saves_and_lists_reports(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("app.services.report_service.settings.REPORT_DIR", tmp_path)
    service = ReportService()
    monkeypatch.setattr(
        service,
        "_build_business_snapshot",
        lambda: {
            "sent": 4,
            "responses": 2,
            "interested": 1,
            "won": 1,
            "reply_rate": 50.0,
            "potential_deal_value": 950.0,
            "by_offer": {
                "landing_page": {"sent": 2, "responses": 1, "interested": 1, "won": 1, "reply_rate": 50.0, "potential_deal_value": 300.0},
                "website": {"sent": 2, "responses": 1, "interested": 0, "won": 0, "reply_rate": 50.0, "potential_deal_value": 650.0},
            },
        },
    )

    paths = service.save_outreach_report(
        {
            "leads_found": 5,
            "validated_leads": 3,
            "validation_skipped": 2,
            "validation_reasons": {"no website": 1, "no contact method": 1},
            "early_stage_businesses": 2,
            "growth_opportunities": 1,
            "high_opportunity_leads": 3,
            "landing_page_offers": 2,
            "website_offers": 1,
            "email_sent": 2,
            "landing_page_sent": 1,
            "website_sent": 1,
            "sms_sent": 0,
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
    assert reports[0]["landing_page_offers"] == 2
    assert reports[0]["landing_page_sent"] == 1
    assert reports[0]["responses"] == 2
    assert reports[0]["won"] == 1
    payload = service.load_report(paths["json_path"])
    assert payload["summary"]["email_sent"] == 2
    assert payload["quality_funnel"]["raw_found"] == 5
    assert payload["quality_funnel"]["high_opportunity_leads"] == 3
    assert payload["quality_funnel"]["website_sent"] == 1
    assert payload["business_snapshot"]["by_offer"]["landing_page"]["sent"] == 2
    assert payload["business_snapshot"]["potential_deal_value"] == 950.0
    assert payload["validation_reasons"]["no website"] == 1
    assert payload["failure_reasons"]["smtp_not_configured"] == 1


def test_report_service_builds_business_snapshot_from_rows():
    service = ReportService()
    snapshot = service._build_business_snapshot_from_rows(
        [
            {"selected_offer_type": "landing_page", "send_status": "SENT", "response_status": "REPLIED", "potential_deal_value": 300},
            {"selected_offer_type": "landing_page", "send_status": "SENT", "response_status": "WON", "potential_deal_value": 350},
            {"selected_offer_type": "website", "send_status": "SENT", "response_status": "NO_RESPONSE", "potential_deal_value": 600},
            {"selected_offer_type": "website", "send_status": "FAILED", "response_status": "NO_RESPONSE", "potential_deal_value": 0},
        ]
    )

    assert snapshot["sent"] == 3
    assert snapshot["responses"] == 2
    assert snapshot["won"] == 1
    assert snapshot["potential_deal_value"] == 1250.0
    assert snapshot["by_offer"]["landing_page"]["reply_rate"] == 100.0
    assert snapshot["by_offer"]["website"]["sent"] == 1
