"""
Centralized sender identity defaults and SMTP consistency helpers.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SenderIdentityDefaults:
    business_name: str
    sender_name: str
    sender_display_name: str
    professional_email: str
    professional_phone: str
    website: str
    portfolio_url: str
    signature_label: str


DEFAULT_SENDER_IDENTITY = SenderIdentityDefaults(
    business_name="KAH.DIGITAL",
    sender_name="Kenams",
    sender_display_name="Kenams \u2014 KAH.DIGITAL",
    professional_email="kahdigital42@gmail.com",
    professional_phone="0759558414",
    website="https://kah-digital.ch/",
    portfolio_url="https://kah-digital.ch/",
    signature_label="Digital Studio",
)

LEGACY_PROFESSIONAL_EMAILS = ("kahprod42@gmail.com",)


def build_default_user_agent(identity: SenderIdentityDefaults = DEFAULT_SENDER_IDENTITY) -> str:
    """Build the default project user-agent with the centralized contact email."""
    return f"LocalLeadFinder/1.0 ({identity.business_name}; +{identity.website}; contact: {identity.professional_email})"


def build_smtp_identity_warnings(
    professional_email: str,
    smtp_username: str | None,
    smtp_from_email: str | None,
) -> list[str]:
    """Return warnings when SMTP sender settings drift from the professional identity."""
    warnings: list[str] = []
    expected_email = (professional_email or "").strip().lower()
    normalized_username = (smtp_username or "").strip().lower()
    normalized_from_email = (smtp_from_email or "").strip().lower()

    if normalized_username and normalized_username != expected_email:
        warnings.append(
            f"SMTP_USERNAME ({smtp_username}) does not match the configured professional email ({professional_email})."
        )
    if normalized_from_email and normalized_from_email != expected_email:
        warnings.append(
            f"SMTP_FROM_EMAIL ({smtp_from_email}) does not match the configured professional email ({professional_email})."
        )

    return warnings


def contains_legacy_sender_identity(value: Any) -> bool:
    """Detect whether persisted content still references the old sender email."""
    if isinstance(value, str):
        return any(legacy_email in value for legacy_email in LEGACY_PROFESSIONAL_EMAILS)
    if isinstance(value, dict):
        return any(contains_legacy_sender_identity(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(contains_legacy_sender_identity(item) for item in value)
    return False


def normalize_sender_content(value: Any, professional_email: str | None = None) -> Any:
    """Replace legacy sender-email references inside strings, lists, tuples, and dicts."""
    target_email = professional_email or DEFAULT_SENDER_IDENTITY.professional_email

    if isinstance(value, str):
        normalized = value
        for legacy_email in LEGACY_PROFESSIONAL_EMAILS:
            normalized = normalized.replace(legacy_email, target_email)
        return normalized
    if isinstance(value, dict):
        return {key: normalize_sender_content(item, target_email) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize_sender_content(item, target_email) for item in value]
    if isinstance(value, tuple):
        return tuple(normalize_sender_content(item, target_email) for item in value)
    return value
