"""
Tests for centralized sender identity helpers.
"""
from app.core.sender_identity import (
    DEFAULT_SENDER_IDENTITY,
    build_smtp_identity_warnings,
    normalize_sender_content,
)


def test_default_sender_identity_uses_professional_email():
    assert DEFAULT_SENDER_IDENTITY.professional_email == "kahdigital42@gmail.com"
    assert DEFAULT_SENDER_IDENTITY.sender_display_name == "Kenams — KAH.DIGITAL"


def test_normalize_sender_content_replaces_legacy_email():
    normalized = normalize_sender_content({"body": "Contact: kahprod42@gmail.com"})
    assert normalized["body"] == f"Contact: {DEFAULT_SENDER_IDENTITY.professional_email}"


def test_build_smtp_identity_warnings_flags_mismatches():
    warnings = build_smtp_identity_warnings(
        professional_email=DEFAULT_SENDER_IDENTITY.professional_email,
        smtp_username="wrong@example.com",
        smtp_from_email="kahprod42@gmail.com",
    )

    assert len(warnings) == 2
    assert "SMTP_USERNAME" in warnings[0]
    assert "SMTP_FROM_EMAIL" in warnings[1]
