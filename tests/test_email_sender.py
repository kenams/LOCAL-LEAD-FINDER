"""
Tests for SMTP sending helpers and send state transitions.
"""
from types import SimpleNamespace

from app.core.sender_identity import DEFAULT_SENDER_IDENTITY
from app.models.prospect import Prospect
from app.services.email_sender import EmailSendResult, EmailSender
from app.services.lead_service import LeadService


def test_prepare_email_uses_test_recipient():
    sender = EmailSender()
    prepared = sender.prepare_email(
        {
            "email": "lead@example.com",
            "email_language": "fr",
            "email_subject_fr": "Sujet test",
            "email_body_fr": "Bonjour",
            "email_html_fr": "<p>Bonjour</p>",
        },
        test_to=DEFAULT_SENDER_IDENTITY.professional_email,
    )

    assert prepared.recipient == "lead@example.com"
    assert prepared.actual_recipient == DEFAULT_SENDER_IDENTITY.professional_email
    assert prepared.is_test_mode is True


def test_send_skips_when_no_email_exists():
    sender = EmailSender()
    prepared = sender.prepare_email(
        {
            "email": "",
            "email_language": "fr",
            "email_subject_fr": "Sujet test",
            "email_body_fr": "Bonjour",
        }
    )

    result = sender.send_prepared_email(prepared, simulate=False)
    assert result.skipped is True
    assert result.error == "missing_email"


def test_test_override_sends_even_when_lead_email_is_missing():
    sender = EmailSender()
    prepared = sender.prepare_email(
        {
            "email": "",
            "email_language": "fr",
            "email_subject_fr": "Sujet test",
            "email_body_fr": "Bonjour",
        },
        test_to=DEFAULT_SENDER_IDENTITY.professional_email,
    )

    result = sender.send_prepared_email(prepared, simulate=True)
    assert result.success is True
    assert result.simulated is True
    assert result.actual_recipient == DEFAULT_SENDER_IDENTITY.professional_email


def test_simulate_send_succeeds_without_smtp():
    sender = EmailSender()
    prepared = sender.prepare_email(
        {
            "email": "lead@example.com",
            "email_language": "en",
            "email_subject_en": "Premium website idea",
            "email_body_en": "Hello",
        }
    )

    result = sender.send_prepared_email(prepared, simulate=True)
    assert result.success is True
    assert result.simulated is True


def test_apply_send_result_marks_success_as_sent():
    service = LeadService()
    prospect = Prospect(
        business_name="Studio Test",
        category="coiffeur",
        location="Paris",
        email="lead@example.com",
        status="MAQUETTE_READY",
        send_status="NOT_SENT",
        send_attempts=0,
    )
    prepared = SimpleNamespace(is_test_mode=False)
    result = EmailSendResult(success=True, actual_recipient="lead@example.com")

    service._apply_send_result(None, prospect, prepared, result)
    assert prospect.send_status == "SENT"
    assert prospect.status == "CONTACTED"
    assert prospect.first_sent_at is not None
    assert prospect.send_attempts == 1


def test_apply_send_result_keeps_not_sent_in_test_mode():
    service = LeadService()
    prospect = Prospect(
        business_name="Studio Test",
        category="coiffeur",
        location="Paris",
        email="lead@example.com",
        status="MAQUETTE_READY",
        send_status="NOT_SENT",
        send_attempts=0,
    )
    prepared = SimpleNamespace(is_test_mode=True)
    result = EmailSendResult(success=True, actual_recipient=DEFAULT_SENDER_IDENTITY.professional_email, test_mode=True)

    service._apply_send_result(None, prospect, prepared, result)
    assert prospect.send_status == "NOT_SENT"
    assert prospect.first_sent_at is None
    assert prospect.send_attempts == 1


def test_prepare_email_normalizes_legacy_sender_email_in_bodies():
    sender = EmailSender()
    prepared = sender.prepare_email(
        {
            "email": "lead@example.com",
            "email_language": "fr",
            "email_subject_fr": "Sujet test",
            "email_body_fr": "Contact: kahprod42@gmail.com",
            "email_html_fr": "<p>kahprod42@gmail.com</p>",
        }
    )

    assert DEFAULT_SENDER_IDENTITY.professional_email in prepared.text_body
    assert DEFAULT_SENDER_IDENTITY.professional_email in prepared.html_body


def test_deduplication_blocks_already_sent_prospects():
    service = LeadService()
    prospect = Prospect(
        business_name="Studio Test",
        category="coiffeur",
        location="Paris",
        send_status="SENT",
    )

    assert service._should_send_prospect(prospect, only_not_sent=False, allow_resend=False) is False
    assert service._should_send_prospect(prospect, only_not_sent=False, allow_resend=True) is True
