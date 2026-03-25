"""
Tests for centralized branding configuration.
"""
from app.core.branding import get_business_identity, get_mockup_quality_level, get_mockup_style_rule, get_text_signature
from app.core.sender_identity import DEFAULT_SENDER_IDENTITY


def test_business_identity_defaults():
    identity = get_business_identity()
    assert identity.business_name == DEFAULT_SENDER_IDENTITY.business_name
    assert identity.sender_display_name == DEFAULT_SENDER_IDENTITY.sender_display_name
    assert identity.professional_email == DEFAULT_SENDER_IDENTITY.professional_email
    assert identity.professional_phone == "0759558414"


def test_text_signature_contains_sender_info():
    signature = get_text_signature("fr")
    assert DEFAULT_SENDER_IDENTITY.sender_display_name in signature
    assert DEFAULT_SENDER_IDENTITY.professional_email in signature
    assert "0759558414" in signature
    assert "https://kah-digital.ch/" in signature


def test_mockup_style_resolution():
    assert get_mockup_style_rule("plumber").key == "trade"
    assert get_mockup_style_rule("hair salon").key == "beauty"
    assert get_mockup_style_rule("spa").key == "wellness"
    assert get_mockup_quality_level() == "premium"
