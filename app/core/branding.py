"""
Central business identity and mockup branding configuration.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from app.core.config import settings
from app.core.country_config import normalize_location


@dataclass(frozen=True)
class BusinessIdentity:
    business_name: str
    sender_name: str
    sender_display_name: str
    professional_email: str
    professional_phone: str
    website: str
    portfolio_url: str
    logo_url: str
    signature_label: str


@dataclass(frozen=True)
class MockupStyleRule:
    key: str
    label: str
    heading_font: str
    body_font: str
    background: str
    surface: str
    surface_alt: str
    accent: str
    accent_soft: str
    text: str
    muted: str
    border: str
    hero_eyebrow_fr: str
    hero_eyebrow_en: str
    hero_title_fr: str
    hero_title_en: str
    hero_subtitle_fr: str
    hero_subtitle_en: str


MOCKUP_STYLE_RULES: Dict[str, MockupStyleRule] = {
    "beauty": MockupStyleRule(
        key="beauty",
        label="Editorial Beauty",
        heading_font="'Cormorant Garamond', Georgia, serif",
        body_font="'Manrope', 'Segoe UI', sans-serif",
        background="#121011",
        surface="#1b1718",
        surface_alt="#241f21",
        accent="#d3ab78",
        accent_soft="#f1e1cc",
        text="#f8f1e7",
        muted="#b9a897",
        border="rgba(211, 171, 120, 0.24)",
        hero_eyebrow_fr="Studio signature",
        hero_eyebrow_en="Signature studio",
        hero_title_fr="Une presence plus desiree, plus claire, plus premium.",
        hero_title_en="A more desirable, clearer and more premium presence.",
        hero_subtitle_fr="Un site editorial qui valorise les prestations, la reservation et l'image du salon.",
        hero_subtitle_en="An editorial website that elevates services, booking and brand perception.",
    ),
    "trade": MockupStyleRule(
        key="trade",
        label="Trust-First Trades",
        heading_font="'Space Grotesk', 'Segoe UI', sans-serif",
        body_font="'Manrope', 'Segoe UI', sans-serif",
        background="#0d1320",
        surface="#121a2b",
        surface_alt="#182339",
        accent="#dca35c",
        accent_soft="#f2dfc8",
        text="#eef4ff",
        muted="#aeb9ca",
        border="rgba(220, 163, 92, 0.24)",
        hero_eyebrow_fr="Intervention premium",
        hero_eyebrow_en="Premium response",
        hero_title_fr="Inspirer confiance des la premiere seconde.",
        hero_title_en="Build trust from the very first second.",
        hero_subtitle_fr="Une page orientee conversion pour les demandes urgentes, les devis et la preuve sociale.",
        hero_subtitle_en="A conversion-focused page built for urgent requests, quotes and trust signals.",
    ),
    "wellness": MockupStyleRule(
        key="wellness",
        label="Calm Luxury Wellness",
        heading_font="'Cormorant Garamond', Georgia, serif",
        body_font="'Manrope', 'Segoe UI', sans-serif",
        background="#0f1716",
        surface="#16211f",
        surface_alt="#1d2b28",
        accent="#b7a27a",
        accent_soft="#e7dfcf",
        text="#edf4f0",
        muted="#a8b8b2",
        border="rgba(183, 162, 122, 0.24)",
        hero_eyebrow_fr="Rituel premium",
        hero_eyebrow_en="Premium ritual",
        hero_title_fr="Faire ressentir le calme avant meme le premier rendez-vous.",
        hero_title_en="Make visitors feel calm before the first appointment.",
        hero_subtitle_fr="Une ambiance plus haut de gamme, une navigation plus fluide et une reservation plus rassurante.",
        hero_subtitle_en="A more elevated atmosphere, smoother navigation and a more reassuring booking flow.",
    ),
    "restaurant": MockupStyleRule(
        key="restaurant",
        label="Refined Hospitality",
        heading_font="'Cormorant Garamond', Georgia, serif",
        body_font="'Manrope', 'Segoe UI', sans-serif",
        background="#140f0d",
        surface="#1d1512",
        surface_alt="#271d1a",
        accent="#c49358",
        accent_soft="#f0dcc6",
        text="#f7efe8",
        muted="#b5a393",
        border="rgba(196, 147, 88, 0.24)",
        hero_eyebrow_fr="Table signature",
        hero_eyebrow_en="Signature table",
        hero_title_fr="Donner envie de reserver avant meme de lire la carte.",
        hero_title_en="Make guests want to book before they even read the menu.",
        hero_subtitle_fr="Une vitrine plus appetissante, plus claire et mieux pensee pour la reservation.",
        hero_subtitle_en="A more appetising, clearer and reservation-ready showcase.",
    ),
    "professional": MockupStyleRule(
        key="professional",
        label="Executive Professional",
        heading_font="'Cormorant Garamond', Georgia, serif",
        body_font="'Manrope', 'Segoe UI', sans-serif",
        background="#0f1115",
        surface="#171a20",
        surface_alt="#1f242c",
        accent="#c6a36e",
        accent_soft="#efe3d0",
        text="#f4f0ea",
        muted="#b0aa9e",
        border="rgba(198, 163, 110, 0.24)",
        hero_eyebrow_fr="Presence executive",
        hero_eyebrow_en="Executive presence",
        hero_title_fr="Une image plus credible, plus rassurante, plus haut de gamme.",
        hero_title_en="A more credible, more reassuring and higher-end presence.",
        hero_subtitle_fr="Un site sobre et precis pour renforcer la confiance, la clarte et la prise de contact.",
        hero_subtitle_en="A clean, precise website built to strengthen trust, clarity and enquiries.",
    ),
}


def get_business_identity() -> BusinessIdentity:
    """Return the centralized professional outreach identity."""
    return BusinessIdentity(
        business_name=settings.BUSINESS_NAME,
        sender_name=settings.SENDER_NAME,
        sender_display_name=settings.SENDER_DISPLAY_NAME,
        professional_email=settings.PROFESSIONAL_EMAIL,
        professional_phone=settings.PROFESSIONAL_PHONE,
        website=settings.BUSINESS_WEBSITE,
        portfolio_url=settings.PORTFOLIO_URL,
        logo_url=settings.PROFESSIONAL_LOGO_URL or settings.BRAND_LOGO_URL,
        signature_label=settings.SIGNATURE_LABEL,
    )


def get_mockup_quality_level() -> str:
    """Return the active mockup quality level."""
    return settings.MOCKUP_QUALITY_LEVEL if settings.MOCKUP_QUALITY_LEVEL in {"standard", "premium"} else "premium"


def get_mockup_style_rule(category: str) -> MockupStyleRule:
    """Resolve a mockup style family from a category."""
    normalized = normalize_location(category)
    if any(term in normalized for term in ["coiff", "hair", "salon", "barber", "beauty"]):
        return MOCKUP_STYLE_RULES["beauty"]
    if any(term in normalized for term in ["spa", "wellness", "institut", "massage"]):
        return MOCKUP_STYLE_RULES["wellness"]
    if any(term in normalized for term in ["plomb", "plumb", "electric", "elect", "craft", "chauffag"]):
        return MOCKUP_STYLE_RULES["trade"]
    if any(term in normalized for term in ["restaurant", "resto", "bistro", "cafe", "brasserie"]):
        return MOCKUP_STYLE_RULES["restaurant"]
    return MOCKUP_STYLE_RULES["professional"]


def get_text_signature(language: str = "fr") -> str:
    """Return the plain-text email signature."""
    identity = get_business_identity()
    label_line = identity.signature_label if language == "en" else f"{identity.signature_label}"
    lines = [
        identity.sender_display_name,
        label_line,
        identity.professional_email,
        identity.professional_phone,
        identity.website,
    ]
    return "\n".join(lines)


def get_html_signature(language: str = "fr") -> str:
    """Return the HTML email signature."""
    identity = get_business_identity()
    logo_html = (
        f'<img src="{identity.logo_url}" alt="{identity.business_name}" style="height:34px; width:auto; display:block; margin-bottom:10px;" />'
        if identity.logo_url
        else ""
    )
    label = identity.signature_label
    return f"""
    <div style="margin-top:28px; padding-top:18px; border-top:1px solid rgba(198,163,110,0.32); font-family:Arial, sans-serif; color:#EDE7DB;">
        {logo_html}
        <div style="font-size:15px; font-weight:700; color:#F5EFE3;">{identity.sender_display_name}</div>
        <div style="font-size:13px; color:#C7B79B; margin-top:2px;">{label}</div>
        <div style="margin-top:10px; font-size:13px; line-height:1.75;">
            <div><a href="mailto:{identity.professional_email}" style="color:#D4AE72; text-decoration:none;">{identity.professional_email}</a></div>
            <div>{identity.professional_phone}</div>
            <div><a href="{identity.website}" style="color:#D4AE72; text-decoration:none;">{identity.website}</a></div>
        </div>
    </div>
    """.strip()


def get_sender_preview_rows() -> List[tuple[str, str]]:
    """Return UI-friendly identity rows."""
    identity = get_business_identity()
    return [
        ("Business", identity.business_name),
        ("Sender", identity.sender_display_name),
        ("Email", identity.professional_email),
        ("Phone", identity.professional_phone),
        ("Website", identity.website),
        ("Portfolio", identity.portfolio_url),
        ("Mockup quality", get_mockup_quality_level()),
    ]
