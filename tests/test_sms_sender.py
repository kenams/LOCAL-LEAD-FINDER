"""
Tests for SMS sending and automatic outreach routing.
"""
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


def test_send_outreach_respects_auto_send_enabled(monkeypatch):
    service = LeadService()
    monkeypatch.setattr("app.services.lead_service.settings.AUTO_SEND_ENABLED", False)

    summary = service.send_outreach(simulate=False)

    assert summary["failed"] == 1
    assert summary["error"] == "auto_send_disabled"
