"""
Tests for country configuration.
"""
from app.core.country_config import detect_country, format_price_range, normalize_location, resolve_email_language


def test_detect_country():
    assert detect_country("Toulouse") == "FR"
    assert detect_country("Geneva") == "CH"
    assert detect_country("Genève") == "CH"
    assert detect_country("Zurich") == "CH"
    assert detect_country("New York") == "US"
    assert detect_country("Sydney") == "AU"


def test_resolve_email_language():
    assert resolve_email_language("Toulouse", "FR") == "fr"
    assert resolve_email_language("Geneva", "CH") == "fr"
    assert resolve_email_language("Zurich", "CH") == "en"
    assert resolve_email_language("Dallas", "US") == "en"
    assert resolve_email_language("Melbourne", "AU") == "en"


def test_format_price_range():
    assert format_price_range(500, 800, "FR") == "500 EUR - 800 EUR"
    assert format_price_range(1200, 1800, "CH") == "1200 CHF - 1800 CHF"
    assert format_price_range(1500, 2200, "US") == "$1500 - $2200"


def test_normalize_location_removes_accents():
    assert normalize_location("Genève") == "geneve"
    assert normalize_location("Zürich") == "zurich"
