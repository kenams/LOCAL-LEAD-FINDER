"""
Country and market configuration.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class CountryProfile:
    code: str
    name: str
    default_language: str
    currency: str
    currency_symbol: str
    messaging_style: str
    price_ranges: Dict[str, Tuple[int, int]]
    country_value_weight: float


COUNTRY_PROFILES: Dict[str, CountryProfile] = {
    "FR": CountryProfile(
        code="FR",
        name="France",
        default_language="fr",
        currency="EUR",
        currency_symbol="EUR",
        messaging_style="local_consultative",
        price_ranges={"EASY": (500, 800), "MEDIUM": (900, 1500), "ADVANCED": (1600, 2800)},
        country_value_weight=1.0,
    ),
    "CH": CountryProfile(
        code="CH",
        name="Switzerland",
        default_language="fr",
        currency="CHF",
        currency_symbol="CHF",
        messaging_style="premium_polite",
        price_ranges={"EASY": (1200, 1800), "MEDIUM": (2200, 3400), "ADVANCED": (3800, 5800)},
        country_value_weight=1.35,
    ),
    "US": CountryProfile(
        code="US",
        name="United States",
        default_language="en",
        currency="USD",
        currency_symbol="$",
        messaging_style="direct_business",
        price_ranges={"EASY": (1500, 2200), "MEDIUM": (2600, 4200), "ADVANCED": (4500, 7200)},
        country_value_weight=1.45,
    ),
    "AU": CountryProfile(
        code="AU",
        name="Australia",
        default_language="en",
        currency="AUD",
        currency_symbol="AUD",
        messaging_style="friendly_professional",
        price_ranges={"EASY": (1200, 1900), "MEDIUM": (2200, 3400), "ADVANCED": (3600, 5600)},
        country_value_weight=1.2,
    ),
    "GB": CountryProfile(
        code="GB",
        name="United Kingdom",
        default_language="en",
        currency="GBP",
        currency_symbol="GBP",
        messaging_style="direct_business",
        price_ranges={"EASY": (900, 1400), "MEDIUM": (1700, 2600), "ADVANCED": (3000, 4600)},
        country_value_weight=1.15,
    ),
    "AE": CountryProfile(
        code="AE",
        name="United Arab Emirates",
        default_language="en",
        currency="AED",
        currency_symbol="AED",
        messaging_style="direct_business",
        price_ranges={"EASY": (3500, 5500), "MEDIUM": (6000, 9500), "ADVANCED": (10000, 18000)},
        country_value_weight=1.8,
    ),
    "SG": CountryProfile(
        code="SG",
        name="Singapore",
        default_language="en",
        currency="SGD",
        currency_symbol="SGD",
        messaging_style="direct_business",
        price_ranges={"EASY": (1300, 2000), "MEDIUM": (2400, 3800), "ADVANCED": (4200, 7000)},
        country_value_weight=1.5,
    ),
    "CA": CountryProfile(
        code="CA",
        name="Canada",
        default_language="en",
        currency="CAD",
        currency_symbol="CAD",
        messaging_style="friendly_professional",
        price_ranges={"EASY": (1200, 1900), "MEDIUM": (2200, 3500), "ADVANCED": (4000, 6500)},
        country_value_weight=1.3,
    ),
}


LOCATION_COUNTRY_MAP = {
    "FR": {"toulouse", "montpellier", "marseille", "paris", "lyon", "nice", "bordeaux", "lille", "nantes"},
    "CH": {"geneva", "geneve", "genf", "zurich", "zuerich", "lausanne", "basel", "bern", "lucerne", "lugano"},
    "US": {"new york", "nyc", "miami", "dallas", "los angeles", "la", "chicago", "houston", "phoenix", "san francisco", "boston", "seattle"},
    "AU": {"sydney", "melbourne", "brisbane", "perth", "adelaide", "gold coast", "canberra"},
    "GB": {"london", "manchester", "birmingham", "liverpool", "leeds", "glasgow"},
    "AE": {"dubai", "abu dhabi", "sharjah", "ajman", "uae"},
    "SG": {"singapore"},
    "CA": {"toronto", "montreal", "vancouver", "calgary", "ottawa"},
}

SWISS_ENGLISH_FALLBACK_CITIES = {"zurich", "zuerich", "basel", "bern", "lucerne"}


def normalize_location(location: str) -> str:
    """Normalize a location string for matching."""
    normalized = unicodedata.normalize("NFKD", (location or "").strip().lower())
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"[^a-z0-9\s-]", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def detect_country(location: str) -> str:
    """Detect country code from a location string."""
    normalized = normalize_location(location)
    for country_code, aliases in LOCATION_COUNTRY_MAP.items():
        if any(alias in normalized for alias in aliases):
            return country_code
    return "FR"


def get_country_profile(country_code: str | None) -> CountryProfile:
    """Return the configured profile for a country code."""
    return COUNTRY_PROFILES.get((country_code or "").upper(), COUNTRY_PROFILES["FR"])


def resolve_email_language(location: str, country_code: str | None, fallback_language: str = "fr") -> str:
    """Resolve the language to use for outbound messaging."""
    code = (country_code or "").upper() or detect_country(location)
    normalized = normalize_location(location)

    if code == "CH":
        return "en" if any(city in normalized for city in SWISS_ENGLISH_FALLBACK_CITIES) else "fr"
    if code in {"US", "AU", "GB", "AE", "SG", "CA"}:
        return "en"
    if code == "FR":
        return "fr"
    return fallback_language


def format_price(amount: float | int, country_code: str | None) -> str:
    """Format a numeric amount using the country currency convention."""
    profile = get_country_profile(country_code)
    value = int(round(float(amount)))
    if profile.code == "US":
        return f"${value}"
    if profile.code == "FR":
        return f"{value} EUR"
    return f"{value} {profile.currency_symbol}"


def format_price_range(price_min: float | int | None, price_max: float | int | None, country_code: str | None) -> str:
    """Format a min/max range for UI and export."""
    if price_min is None and price_max is None:
        return ""
    if price_min is None:
        return format_price(price_max or 0, country_code)
    if price_max is None:
        return format_price(price_min, country_code)
    return f"{format_price(price_min, country_code)} - {format_price(price_max, country_code)}"


def get_estimated_time(feasibility: str, language: str) -> str:
    """Return localized delivery timing."""
    normalized = (feasibility or "EASY").upper()
    if language == "fr":
        mapping = {"EASY": "1 a 2 jours", "MEDIUM": "3 a 5 jours", "ADVANCED": "5 a 10 jours"}
    else:
        mapping = {"EASY": "1-2 days", "MEDIUM": "3-5 days", "ADVANCED": "5-10 days"}
    return mapping.get(normalized, mapping["EASY"])


def get_country_display_name(country_code: str | None) -> str:
    """Return a human readable country name."""
    return get_country_profile(country_code).name
