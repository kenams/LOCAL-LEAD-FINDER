"""
KAH.DIGITAL Streamlit theme helpers.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd
import streamlit as st

from app.core.config import settings

PALETTE = {
    "bg": "#070708",
    "bg_soft": "#0E1014",
    "surface": "#111317",
    "surface_alt": "#171A20",
    "surface_glow": "#1C2027",
    "accent": "#C9A86A",
    "accent_bright": "#E0BF83",
    "text": "#F5EFE3",
    "muted": "#9C968A",
    "border": "rgba(201, 168, 106, 0.22)",
    "success": "#B9A16A",
    "warning": "#C48F4A",
    "danger": "#8E4A4A",
}


def inject_global_styles():
    """Inject global CSS for the branded experience."""
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Cormorant+Garamond:wght@600;700&display=swap');

        :root {{
            --kah-bg: {PALETTE["bg"]};
            --kah-bg-soft: {PALETTE["bg_soft"]};
            --kah-surface: {PALETTE["surface"]};
            --kah-surface-alt: {PALETTE["surface_alt"]};
            --kah-surface-glow: {PALETTE["surface_glow"]};
            --kah-accent: {PALETTE["accent"]};
            --kah-accent-bright: {PALETTE["accent_bright"]};
            --kah-text: {PALETTE["text"]};
            --kah-muted: {PALETTE["muted"]};
            --kah-border: {PALETTE["border"]};
            --kah-success: {PALETTE["success"]};
            --kah-warning: {PALETTE["warning"]};
            --kah-danger: {PALETTE["danger"]};
        }}

        html, body, [class*="css"] {{
            font-family: "Plus Jakarta Sans", "Segoe UI", sans-serif;
            background:
                radial-gradient(circle at top left, rgba(201, 168, 106, 0.08), transparent 28%),
                radial-gradient(circle at top right, rgba(201, 168, 106, 0.04), transparent 24%),
                linear-gradient(180deg, #050506 0%, var(--kah-bg) 100%);
            color: var(--kah-text);
        }}

        .stApp {{
            background:
                radial-gradient(circle at 0% 0%, rgba(201, 168, 106, 0.07), transparent 24%),
                linear-gradient(180deg, #050506 0%, var(--kah-bg) 100%);
        }}

        [data-testid="stAppViewContainer"] > .main {{
            padding-top: 1.6rem;
        }}

        [data-testid="stSidebar"] {{
            background:
                linear-gradient(180deg, rgba(19, 21, 25, 0.98), rgba(10, 11, 14, 0.98));
            border-right: 1px solid var(--kah-border);
        }}

        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] span {{
            color: var(--kah-text);
        }}

        [data-testid="stSidebarNav"] {{
            display: none;
        }}

        h1, h2, h3 {{
            color: var(--kah-text);
            letter-spacing: 0.01em;
        }}

        h1, .kah-brand-title {{
            font-family: "Cormorant Garamond", Georgia, serif;
        }}

        .kah-hero {{
            position: relative;
            overflow: hidden;
            padding: 2rem 2.1rem;
            border-radius: 24px;
            border: 1px solid var(--kah-border);
            background:
                linear-gradient(135deg, rgba(201, 168, 106, 0.10), transparent 42%),
                linear-gradient(180deg, rgba(18, 20, 24, 0.96), rgba(10, 11, 14, 0.98));
            box-shadow: 0 20px 80px rgba(0, 0, 0, 0.32);
            margin-bottom: 1.2rem;
        }}

        .kah-hero::after {{
            content: "";
            position: absolute;
            inset: 0;
            background:
                radial-gradient(circle at 100% 0%, rgba(201, 168, 106, 0.18), transparent 28%);
            pointer-events: none;
        }}

        .kah-overline {{
            color: var(--kah-accent);
            text-transform: uppercase;
            letter-spacing: 0.24em;
            font-size: 0.72rem;
            font-weight: 700;
            margin-bottom: 0.8rem;
        }}

        .kah-brand-title {{
            font-size: clamp(2.3rem, 5vw, 3.8rem);
            line-height: 0.96;
            margin: 0;
        }}

        .kah-subtitle {{
            color: var(--kah-muted);
            font-size: 1rem;
            margin-top: 0.8rem;
            max-width: 58rem;
        }}

        .kah-section {{
            margin-top: 0.6rem;
            margin-bottom: 0.55rem;
        }}

        .kah-section-label {{
            text-transform: uppercase;
            letter-spacing: 0.16em;
            font-size: 0.72rem;
            color: var(--kah-accent);
            font-weight: 700;
            margin-bottom: 0.35rem;
        }}

        .kah-section-title {{
            font-size: 1.45rem;
            font-weight: 700;
            margin: 0;
        }}

        .kah-section-subtitle {{
            color: var(--kah-muted);
            margin-top: 0.35rem;
            font-size: 0.95rem;
        }}

        .kah-card {{
            background: linear-gradient(180deg, rgba(23, 25, 30, 0.98), rgba(14, 16, 20, 0.98));
            border: 1px solid var(--kah-border);
            border-radius: 20px;
            padding: 1rem 1rem 0.95rem;
            box-shadow: 0 12px 32px rgba(0, 0, 0, 0.18);
        }}

        .kah-metric {{
            min-height: 126px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}

        .kah-metric-label {{
            color: var(--kah-muted);
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            font-weight: 700;
        }}

        .kah-metric-value {{
            color: var(--kah-text);
            font-size: 2rem;
            font-weight: 800;
            line-height: 1;
        }}

        .kah-metric-note {{
            color: var(--kah-accent);
            font-size: 0.84rem;
        }}

        .kah-summary-grid {{
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.7rem;
        }}

        .kah-meta {{
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            border-bottom: 1px solid rgba(255,255,255,0.04);
            padding: 0.42rem 0;
        }}

        .kah-meta:last-child {{
            border-bottom: none;
        }}

        .kah-meta-label {{
            color: var(--kah-muted);
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-size: 0.72rem;
            font-weight: 700;
        }}

        .kah-meta-value {{
            color: var(--kah-text);
            text-align: right;
            font-weight: 600;
        }}

        .kah-badge {{
            display: inline-flex;
            align-items: center;
            gap: 0.38rem;
            padding: 0.34rem 0.68rem;
            border-radius: 999px;
            border: 1px solid var(--kah-border);
            background: rgba(255,255,255,0.02);
            font-size: 0.73rem;
            text-transform: uppercase;
            letter-spacing: 0.10em;
            font-weight: 700;
        }}

        .kah-badge::before {{
            content: "";
            width: 0.48rem;
            height: 0.48rem;
            border-radius: 999px;
            background: currentColor;
            opacity: 0.9;
        }}

        .kah-badge-neutral {{ color: var(--kah-accent); }}
        .kah-badge-success {{ color: var(--kah-success); }}
        .kah-badge-warning {{ color: var(--kah-warning); }}
        .kah-badge-danger {{ color: var(--kah-danger); }}

        .kah-inline-badges {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.55rem;
            margin-top: 0.2rem;
        }}

        .stButton > button,
        .stDownloadButton > button,
        [data-testid="stLinkButton"] a {{
            border-radius: 14px !important;
            border: 1px solid rgba(201, 168, 106, 0.36) !important;
            background: linear-gradient(180deg, rgba(205, 172, 112, 0.94), rgba(183, 147, 88, 0.94)) !important;
            color: #090909 !important;
            font-weight: 700 !important;
            letter-spacing: 0.04em !important;
            padding: 0.7rem 1rem !important;
            transition: all 0.18s ease !important;
            box-shadow: 0 10px 24px rgba(0, 0, 0, 0.18);
        }}

        .stButton > button:hover,
        .stDownloadButton > button:hover,
        [data-testid="stLinkButton"] a:hover {{
            transform: translateY(-1px);
            background: linear-gradient(180deg, rgba(224, 191, 131, 0.98), rgba(201, 168, 106, 0.98)) !important;
            border-color: rgba(224, 191, 131, 0.62) !important;
        }}

        .stButton > button:disabled {{
            opacity: 0.45;
            cursor: not-allowed;
        }}

        [data-baseweb="input"] > div,
        [data-baseweb="select"] > div,
        .stMultiSelect [data-baseweb="select"] > div,
        .stNumberInput [data-baseweb="input"] > div {{
            background: rgba(17, 19, 23, 0.96) !important;
            border: 1px solid var(--kah-border) !important;
            border-radius: 16px !important;
            color: var(--kah-text) !important;
        }}

        [data-baseweb="tag"] {{
            background: rgba(201, 168, 106, 0.12) !important;
            color: var(--kah-accent-bright) !important;
            border-radius: 999px !important;
            border: 1px solid rgba(201, 168, 106, 0.22) !important;
        }}

        [data-testid="stExpander"] {{
            border: 1px solid var(--kah-border);
            border-radius: 18px;
            background: linear-gradient(180deg, rgba(19, 22, 27, 0.98), rgba(14, 16, 20, 0.98));
            overflow: hidden;
        }}

        [data-testid="stExpander"] summary {{
            background: transparent !important;
            color: var(--kah-text) !important;
            font-weight: 700 !important;
        }}

        [data-testid="stDataFrame"] {{
            border: 1px solid var(--kah-border);
            border-radius: 20px;
            overflow: hidden;
            background: rgba(17, 19, 23, 0.98);
        }}

        .stTextArea textarea,
        .stTextInput input {{
            background: rgba(10, 11, 14, 0.98) !important;
            color: var(--kah-text) !important;
            border: 1px solid var(--kah-border) !important;
            border-radius: 16px !important;
        }}

        [data-testid="stMarkdownContainer"] code {{
            color: var(--kah-accent-bright);
            background: rgba(255,255,255,0.04);
        }}

        .kah-table-note {{
            color: var(--kah-muted);
            font-size: 0.82rem;
            margin-top: 0.35rem;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_brand_header():
    """Render the premium hero area."""
    logo_source = _resolve_logo_source()
    if logo_source:
        col1, col2 = st.columns([1, 5])
        with col1:
            st.image(logo_source, use_container_width=True)
        with col2:
            st.markdown(_hero_html(), unsafe_allow_html=True)
    else:
        st.markdown(_hero_html(), unsafe_allow_html=True)


def render_sidebar_brand():
    """Render the premium sidebar heading."""
    st.sidebar.markdown(
        f"""
        <div class="kah-card" style="margin-top:0.6rem;">
            <div class="kah-overline">KAH-Digital</div>
            <div style="font-family:'Cormorant Garamond', Georgia, serif; font-size:1.65rem; color:{PALETTE["text"]}; line-height:1;">
                Control Center
            </div>
            <div style="color:{PALETTE["muted"]}; margin-top:0.55rem; font-size:0.92rem;">
                Premium internal studio dashboard for lead generation, mockups and outreach.
            </div>
            <div style="color:{PALETTE["accent"]}; margin-top:0.7rem; font-size:0.78rem; letter-spacing:0.08em; text-transform:uppercase; font-weight:700;">
                Built by Kah-Digital
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section(title: str, eyebrow: str, subtitle: str | None = None):
    """Render a styled section heading."""
    subtitle_html = f'<div class="kah-section-subtitle">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f"""
        <div class="kah-section">
            <div class="kah-section-label">{eyebrow}</div>
            <div class="kah-section-title">{title}</div>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(label: str, value: str, note: str = ""):
    """Render a premium metric card."""
    note_html = f'<div class="kah-metric-note">{note}</div>' if note else ""
    st.markdown(
        f"""
        <div class="kah-card kah-metric">
            <div class="kah-metric-label">{label}</div>
            <div class="kah-metric-value">{value}</div>
            {note_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_key_value_card(title: str, rows: Iterable[tuple[str, str]]):
    """Render a card with label/value rows."""
    body = "".join(
        f"""
        <div class="kah-meta">
            <div class="kah-meta-label">{label}</div>
            <div class="kah-meta-value">{value}</div>
        </div>
        """
        for label, value in rows
    )
    st.markdown(
        f"""
        <div class="kah-card">
            <div class="kah-section-label" style="margin-bottom:0.8rem;">{title}</div>
            {body}
        </div>
        """,
        unsafe_allow_html=True,
    )


def badge_html(text: str, tone: str = "neutral") -> str:
    """Return HTML for a status badge."""
    safe_tone = tone if tone in {"neutral", "success", "warning", "danger"} else "neutral"
    return f'<span class="kah-badge kah-badge-{safe_tone}">{text}</span>'


def priority_badge_html(priority_score: float | int | None) -> str:
    """Return a styled badge for priority score."""
    score = float(priority_score or 0)
    if score >= 110:
        return badge_html("High Priority", "success")
    if score >= 80:
        return badge_html("Medium Priority", "warning")
    return badge_html("Low Priority", "neutral")


def status_badge_html(status: str | None) -> str:
    """Return a badge for deployment/contact status."""
    normalized = (status or "pending").lower()
    tone = {
        "deployed": "success",
        "pending": "warning",
        "failed": "danger",
        "sent": "success",
        "not_sent": "neutral",
        "skipped": "warning",
        "contacted": "success",
        "high priority": "success",
        "medium priority": "warning",
        "low priority": "neutral",
    }.get(normalized, "neutral")
    return badge_html(normalized, tone)


def style_prospect_dataframe(dataframe: pd.DataFrame) -> pd.io.formats.style.Styler:
    """Apply premium styling to the main lead table."""
    styled = (
        dataframe.style.hide(axis="index")
        .set_properties(
            **{
                "background-color": PALETTE["surface"],
                "color": PALETTE["text"],
                "border-color": PALETTE["border"],
                "font-size": "0.92rem",
            }
        )
        .set_table_styles(
            [
                {
                    "selector": "thead th",
                    "props": [
                        ("background-color", PALETTE["surface_alt"]),
                        ("color", PALETTE["accent_bright"]),
                        ("font-weight", "700"),
                        ("text-transform", "uppercase"),
                        ("letter-spacing", "0.08em"),
                        ("border-bottom", f"1px solid {PALETTE['border']}"),
                    ],
                },
                {
                    "selector": "tbody tr:hover",
                    "props": [("background-color", PALETTE["surface_glow"])],
                },
            ]
        )
        .map(_priority_style, subset=["Priority"])
        .map(_status_style, subset=["Mockup"])
        .map(_country_style, subset=["Country"])
    )
    if "Send Status" in dataframe.columns:
        styled = styled.map(_send_style, subset=["Send Status"])
    return styled


def _priority_style(value):
    score = float(value or 0)
    if score >= 110:
        return f"color: {PALETTE['accent_bright']}; font-weight: 800;"
    if score >= 80:
        return f"color: {PALETTE['accent']}; font-weight: 700;"
    return f"color: {PALETTE['muted']};"


def _status_style(value):
    normalized = str(value or "").lower()
    if normalized == "deployed":
        return f"color: {PALETTE['success']}; font-weight: 700;"
    if normalized == "failed":
        return f"color: {PALETTE['danger']}; font-weight: 700;"
    return f"color: {PALETTE['warning']}; font-weight: 700;"


def _country_style(value):
    return f"color: {PALETTE['accent_bright']}; font-weight: 700;"


def _send_style(value):
    normalized = str(value or "").lower()
    if normalized == "sent":
        return f"color: {PALETTE['success']}; font-weight: 700;"
    if normalized == "failed":
        return f"color: {PALETTE['danger']}; font-weight: 700;"
    if normalized == "skipped":
        return f"color: {PALETTE['warning']}; font-weight: 700;"
    return f"color: {PALETTE['muted']}; font-weight: 700;"


def _hero_html() -> str:
    return f"""
    <div class="kah-hero">
        <div class="kah-overline">Built by Kah-Digital</div>
        <h1 class="kah-brand-title">{settings.BRAND_NAME}</h1>
        <div class="kah-subtitle">{settings.BRAND_SUBTITLE}</div>
    </div>
    """


def _resolve_logo_source() -> str | None:
    if settings.BRAND_LOGO_URL:
        return settings.BRAND_LOGO_URL
    if settings.BRAND_LOGO_PATH:
        logo_path = Path(settings.BRAND_LOGO_PATH)
        if logo_path.exists():
            return str(logo_path)
    return None
