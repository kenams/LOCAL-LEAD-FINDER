"""
Tests for SMS sending and automatic outreach routing.
"""
import asyncio
import json

from app.models.prospect import Prospect
from app.services.lead_service import LeadService
from app.services.sms_sender import SMSSender


def test_sms_sender_simulate_succeeds(monkeypatch):
    monkeypatch.setattr("app.services.sms_sender.settings.SMS_PROVIDER", "twilio")
    monkeypatch.setattr("app.services.sms_sender.settings.SMS_API_KEY", "acct")
    monkeypatch.setattr("app.services.sms_sender.settings.SMS_API_SECRET", "secret")
    monkeypatch.setattr("app.services.sms_sender.settings.SMS_FROM_NUMBER", "+41000000000")

    sender = SMSSender()
    prepared = sender.prepare_sms({"phone": "+41795551212", "sms_message": "Bonjour"})

    result = sender.send_prepared_sms(prepared, simulate=True)

    assert result.success is True
    assert result.simulated is True
    assert result.actual_recipient == "+41795551212"


def test_sms_sender_fails_cleanly_when_not_configured(monkeypatch):
    monkeypatch.setattr("app.services.sms_sender.settings.SMS_PROVIDER", "")
    monkeypatch.setattr("app.services.sms_sender.settings.SMS_API_KEY", "")
    monkeypatch.setattr("app.services.sms_sender.settings.SMS_API_SECRET", "")
    monkeypatch.setattr("app.services.sms_sender.settings.SMS_FROM_NUMBER", "")

    sender = SMSSender()
    prepared = sender.prepare_sms({"phone": "+41795551212", "sms_message": "Bonjour"})
    result = sender.send_prepared_sms(prepared, simulate=False)

    assert result.success is False
    assert result.error == "sms_provider_not_configured"


def test_auto_outreach_channel_prioritizes_email_then_sms_then_skip():
    service = LeadService()

    assert service._select_outreach_channel(Prospect(email="lead@example.com", phone="+41795551212"), {}) == "email"
    assert service._select_outreach_channel(Prospect(phone="+41795551212"), {}) == "sms"
    assert service._select_outreach_channel(Prospect(), {}) == "skipped"


def test_auto_outreach_channel_skips_phone_when_sms_disabled(monkeypatch):
    service = LeadService()
    monkeypatch.setattr("app.services.lead_service.settings.AUTO_MODE_SMS_ENABLED", False)

    assert service._select_outreach_channel(Prospect(phone="+41795551212"), {}) == "skipped"


def test_send_outreach_respects_auto_send_enabled(monkeypatch):
    service = LeadService()
    monkeypatch.setattr("app.services.lead_service.settings.AUTO_SEND_ENABLED", False)

    summary = service.send_outreach(simulate=False)

    assert summary["failed"] == 1
    assert summary["error"] == "auto_send_disabled"


def test_auto_outreach_preflight_reports_missing_delivery_config(monkeypatch):
    service = LeadService()
    monkeypatch.setattr("app.services.lead_service.settings.AUTO_SEND_ENABLED", False)
    monkeypatch.setattr("app.services.lead_service.settings.SMTP_HOST", "")
    monkeypatch.setattr("app.services.lead_service.settings.SMTP_FROM_EMAIL", "")
    monkeypatch.setattr("app.services.lead_service.settings.SMS_PROVIDER", "")
    monkeypatch.setattr("app.services.lead_service.settings.SMS_API_KEY", "")
    monkeypatch.setattr("app.services.lead_service.settings.SMS_API_SECRET", "")
    monkeypatch.setattr("app.services.lead_service.settings.SMS_FROM_NUMBER", "")

    preflight = service.get_auto_outreach_preflight(simulate=False)

    assert preflight["auto_send_enabled"] is False
    assert preflight["smtp_ready"] is False
    assert preflight["sms_ready"] is False
    assert any("AUTO_SEND_ENABLED is false" in warning for warning in preflight["warnings"])
    assert any("smtp_not_configured" in warning for warning in preflight["warnings"])
    assert any("sms_provider_not_configured" in warning for warning in preflight["warnings"])


def test_auto_outreach_preflight_reports_sms_disabled(monkeypatch):
    service = LeadService()
    monkeypatch.setattr("app.services.lead_service.settings.AUTO_MODE_SMS_ENABLED", False)

    preflight = service.get_auto_outreach_preflight(simulate=False)

    assert preflight["sms_enabled"] is False
    assert any("AUTO_MODE_SMS_ENABLED is false" in warning for warning in preflight["warnings"])


def test_auto_outreach_preflight_reports_full_contact_requirement(monkeypatch):
    service = LeadService()
    monkeypatch.setattr("app.services.lead_service.settings.AUTO_MODE_REQUIRE_EMAIL_AND_PHONE", True)

    preflight = service.get_auto_outreach_preflight(simulate=False)

    assert preflight["require_full_contact"] is True
    assert any("AUTO_MODE_REQUIRE_EMAIL_AND_PHONE is true" in warning for warning in preflight["warnings"])


def test_filter_auto_mode_contacts_requires_email_and_phone(monkeypatch):
    service = LeadService()
    monkeypatch.setattr("app.services.lead_service.settings.AUTO_MODE_REQUIRE_EMAIL_AND_PHONE", True)

    eligible, rejected = service._filter_auto_mode_contacts(
        [
            {"business_name": "Full Contact", "email": "lead@example.com", "phone": "+41795551212"},
            {"business_name": "Email Only", "email": "lead@example.com", "phone": ""},
            {"business_name": "Phone Only", "email": "", "phone": "+41795550000"},
        ]
    )

    assert [lead["business_name"] for lead in eligible] == ["Full Contact"]
    assert len(rejected) == 2
    assert all(lead["rejection_reason"] == "missing_email_or_phone_for_auto_mode" for lead in rejected)


def test_prepare_outreach_assets_skips_mockups_in_auto_mode(monkeypatch):
    service = LeadService()
    monkeypatch.setattr("app.services.lead_service.settings.AUTO_MODE_GENERATE_MOCKUPS", False)
    monkeypatch.setattr("app.services.lead_service.settings.AUTO_MODE_DEPLOY_MOCKUPS", False)

    calls = {"generate": 0, "prepare": 0, "deploy": 0}

    def fake_generate_mockup(*args, **kwargs):
        calls["generate"] += 1
        return "mockup.html"

    def fake_prepare_for_deployment(*args, **kwargs):
        calls["prepare"] += 1
        return "bundle.zip"

    def fake_deploy_mockup(*args, **kwargs):
        calls["deploy"] += 1
        return {"status": "deployed", "mockup_status": "deployed", "url": "https://example.com"}

    monkeypatch.setattr(service.mockup_generator, "generate_mockup", fake_generate_mockup)
    monkeypatch.setattr(service.netlify_preparer, "prepare_for_deployment", fake_prepare_for_deployment)
    monkeypatch.setattr(service.netlify_deployer, "deploy_mockup", fake_deploy_mockup)
    monkeypatch.setattr(
        service.email_generator,
        "generate_email",
        lambda lead, language: {
            "subject": f"Subject {language}",
            "long_body": f"Body {language}",
            "html_body": f"<p>{language}</p>",
            "short_subject": f"Short {language}",
            "short_body": f"Short body {language}",
            "follow_ups": {},
        },
    )
    monkeypatch.setattr(
        service.contact_strategy,
        "generate_messages",
        lambda lead: {
            "recommended_channel": "sms",
            "contact_strategy": "phone",
            "sms_message": "Bonjour",
            "email_unavailable_reason": "missing_email",
        },
    )

    prepared = asyncio.run(
        service._prepare_outreach_assets(
            [
                {
                    "business_name": "Test Lead",
                    "category": "coiffeur",
                    "location": "Geneva",
                    "email_language": "fr",
                    "phone": "+41795551212",
                }
            ],
            "fr",
            auto_mode=True,
        )
    )

    notes = json.loads(prepared[0]["notes"])

    assert calls == {"generate": 0, "prepare": 0, "deploy": 0}
    assert prepared[0]["mockup_url"] == ""
    assert notes["netlify_status"] == "disabled_auto_mode"
