"""
Configuration settings.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

from app.core.sender_identity import (
    DEFAULT_SENDER_IDENTITY,
    build_default_user_agent,
    build_smtp_identity_warnings,
)

# Load environment variables
load_dotenv()


class Settings:
    # App settings
    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_PORT: int = int(os.getenv("APP_PORT", 8000))
    STREAMLIT_PORT: int = int(os.getenv("STREAMLIT_PORT", 8501))

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/local_lead_finder.db")

    # Defaults
    DEFAULT_LANGUAGE: str = os.getenv("DEFAULT_LANGUAGE", "fr")
    DEFAULT_PROSPECTS_PER_LOCATION: int = int(os.getenv("DEFAULT_PROSPECTS_PER_LOCATION", 10))
    REQUIRE_WEBSITE: bool = os.getenv("REQUIRE_WEBSITE", "true").lower() == "true"
    REQUIRE_CONTACT: bool = os.getenv("REQUIRE_CONTACT", "true").lower() == "true"
    PRIORITY_NICHES_ENABLED: bool = os.getenv("PRIORITY_NICHES_ENABLED", "true").lower() == "true"

    # API Keys
    SERPAPI_KEY: str = os.getenv("SERPAPI_KEY", "")
    APIFY_TOKEN: str = os.getenv("APIFY_TOKEN", "")
    NETLIFY_TOKEN: str = os.getenv("NETLIFY_TOKEN", "")
    NETLIFY_API_BASE: str = os.getenv("NETLIFY_API_BASE", "https://api.netlify.com/api/v1")

    # Request settings
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", 30))
    USER_AGENT: str = os.getenv("USER_AGENT", build_default_user_agent())
    NETLIFY_DEPLOY_POLL_ATTEMPTS: int = int(os.getenv("NETLIFY_DEPLOY_POLL_ATTEMPTS", 12))
    NETLIFY_DEPLOY_POLL_INTERVAL: int = int(os.getenv("NETLIFY_DEPLOY_POLL_INTERVAL", 3))
    SEARCH_QUERIES_PER_COMBO: int = int(os.getenv("SEARCH_QUERIES_PER_COMBO", 8))
    SEARCH_MAX_RAW_CANDIDATES: int = int(os.getenv("SEARCH_MAX_RAW_CANDIDATES", 24))
    SEARCH_FALLBACK_ENABLED: bool = os.getenv("SEARCH_FALLBACK_ENABLED", "true").lower() == "true"
    SEARCH_BROADEN_IF_EMPTY: bool = os.getenv("SEARCH_BROADEN_IF_EMPTY", "true").lower() == "true"
    SEARCH_RESET_BEFORE_COLLECT: bool = os.getenv("SEARCH_RESET_BEFORE_COLLECT", "true").lower() == "true"
    OSM_NOMINATIM_URL: str = os.getenv("OSM_NOMINATIM_URL", "https://nominatim.openstreetmap.org/search")
    OSM_OVERPASS_URLS: list[str] = [
        url.strip()
        for url in os.getenv(
            "OSM_OVERPASS_URLS",
            "https://lz4.overpass-api.de/api/interpreter,https://overpass-api.de/api/interpreter,https://overpass.kumi.systems/api/interpreter",
        ).split(",")
        if url.strip()
    ]

    # Scheduler
    ENABLE_SCHEDULER: bool = os.getenv("ENABLE_SCHEDULER", "true").lower() == "true"
    AUTO_MODE_ENABLED: bool = os.getenv("AUTO_MODE_ENABLED", "true").lower() == "true"
    AUTO_MODE_NAME: str = os.getenv("AUTO_MODE_NAME", "Auto Outreach")
    AUTO_MODE_CRON: str = os.getenv("AUTO_MODE_CRON", "0 9 */2 * *")
    AUTO_MODE_LOCATIONS: str = os.getenv("AUTO_MODE_LOCATIONS", "Geneva,Sydney")
    AUTO_MODE_CATEGORIES: str = os.getenv(
        "AUTO_MODE_CATEGORIES",
        "marketing,consultant,agency,web design,seo,coach,accountant,lawyer,financial advisor,real estate",
    )
    AUTO_MODE_LIMIT: int = int(os.getenv("AUTO_MODE_LIMIT", 10))
    AUTO_MODE_LANGUAGE: str = os.getenv("AUTO_MODE_LANGUAGE", "fr")
    AUTO_MODE_SMS_ENABLED: bool = os.getenv("AUTO_MODE_SMS_ENABLED", "true").lower() == "true"
    AUTO_MODE_REQUIRE_EMAIL_AND_PHONE: bool = os.getenv("AUTO_MODE_REQUIRE_EMAIL_AND_PHONE", "false").lower() == "true"
    AUTO_MODE_CONTACT_CANDIDATE_MULTIPLIER: int = int(os.getenv("AUTO_MODE_CONTACT_CANDIDATE_MULTIPLIER", 8))
    AUTO_MODE_GENERATE_MOCKUPS: bool = os.getenv("AUTO_MODE_GENERATE_MOCKUPS", "false").lower() == "true"
    AUTO_MODE_DEPLOY_MOCKUPS: bool = os.getenv("AUTO_MODE_DEPLOY_MOCKUPS", "false").lower() == "true"

    # Paths
    BASE_DIR: Path = Path(__file__).parent.parent.parent
    EXPORT_DIR: Path = BASE_DIR / os.getenv("EXPORT_DIR", "exports")
    REPORT_DIR: Path = BASE_DIR / os.getenv("REPORT_DIR", "reports")
    LOG_DIR: Path = BASE_DIR / "logs"
    DATA_DIR: Path = BASE_DIR / "data"

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: Path = LOG_DIR / "app.log"

    # Branding
    BRAND_NAME: str = os.getenv("BRAND_NAME", "KAH-Digital")
    BRAND_SUBTITLE: str = os.getenv("BRAND_SUBTITLE", "Premium prospecting command center")
    BRAND_LOGO_URL: str = os.getenv("BRAND_LOGO_URL", "")
    BRAND_LOGO_PATH: str = os.getenv("BRAND_LOGO_PATH", "")
    BUSINESS_NAME: str = os.getenv("BUSINESS_NAME", DEFAULT_SENDER_IDENTITY.business_name)
    SENDER_NAME: str = os.getenv("SENDER_NAME", DEFAULT_SENDER_IDENTITY.sender_name)
    SENDER_DISPLAY_NAME: str = os.getenv("SENDER_DISPLAY_NAME", DEFAULT_SENDER_IDENTITY.sender_display_name)
    PROFESSIONAL_EMAIL: str = os.getenv("PROFESSIONAL_EMAIL", DEFAULT_SENDER_IDENTITY.professional_email)
    PROFESSIONAL_PHONE: str = os.getenv("PROFESSIONAL_PHONE", DEFAULT_SENDER_IDENTITY.professional_phone)
    BUSINESS_WEBSITE: str = os.getenv("BUSINESS_WEBSITE", DEFAULT_SENDER_IDENTITY.website)
    PORTFOLIO_URL: str = os.getenv("PORTFOLIO_URL", DEFAULT_SENDER_IDENTITY.portfolio_url)
    PROFESSIONAL_LOGO_URL: str = os.getenv("PROFESSIONAL_LOGO_URL", "")
    SIGNATURE_LABEL: str = os.getenv("SIGNATURE_LABEL", DEFAULT_SENDER_IDENTITY.signature_label)
    MOCKUP_QUALITY_LEVEL: str = os.getenv("MOCKUP_QUALITY_LEVEL", "premium").lower()
    MOCKUP_INCLUDE_STUDIO_CREDIT: bool = os.getenv("MOCKUP_INCLUDE_STUDIO_CREDIT", "false").lower() == "true"

    # Email sending
    AUTO_SEND_ENABLED: bool = os.getenv("AUTO_SEND_ENABLED", "false").lower() == "true"
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", DEFAULT_SENDER_IDENTITY.professional_email)
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    SMTP_FROM_EMAIL: str = os.getenv(
        "SMTP_FROM_EMAIL",
        os.getenv("PROFESSIONAL_EMAIL", DEFAULT_SENDER_IDENTITY.professional_email),
    )
    SMTP_FROM_NAME: str = os.getenv(
        "SMTP_FROM_NAME",
        os.getenv("SENDER_DISPLAY_NAME", DEFAULT_SENDER_IDENTITY.sender_display_name),
    )
    SEND_MAX_PER_RUN: int = int(os.getenv("SEND_MAX_PER_RUN", 10))
    SEND_DELAY_SECONDS: float = float(os.getenv("SEND_DELAY_SECONDS", 1.5))
    SEND_BATCH_SIZE: int = int(os.getenv("SEND_BATCH_SIZE", 10))
    SEND_ALLOW_RESEND: bool = os.getenv("SEND_ALLOW_RESEND", "false").lower() == "true"

    # SMS sending
    SMS_PROVIDER: str = os.getenv("SMS_PROVIDER", "").strip().lower()
    SMS_API_KEY: str = os.getenv("SMS_API_KEY", "")
    SMS_API_SECRET: str = os.getenv("SMS_API_SECRET", "")
    SMS_FROM_NUMBER: str = os.getenv("SMS_FROM_NUMBER", "")

    def get_smtp_identity_warnings(self) -> list[str]:
        """Return warnings when SMTP sender settings drift from the configured professional email."""
        return build_smtp_identity_warnings(
            professional_email=self.PROFESSIONAL_EMAIL,
            smtp_username=self.SMTP_USERNAME,
            smtp_from_email=self.SMTP_FROM_EMAIL,
        )

    def get_smtp_diagnostics(self) -> dict[str, object]:
        """Return a safe SMTP diagnostic snapshot without exposing the real password."""
        return {
            "host": self.SMTP_HOST,
            "port": self.SMTP_PORT,
            "username": self.SMTP_USERNAME,
            "from_email": self.SMTP_FROM_EMAIL,
            "password_present": bool(self.SMTP_PASSWORD),
            "password_length": len(self.SMTP_PASSWORD or ""),
            "warnings": self.get_smtp_identity_warnings(),
        }

    # Ensure directories exist
    EXPORT_DIR.mkdir(exist_ok=True)
    REPORT_DIR.mkdir(exist_ok=True)
    LOG_DIR.mkdir(exist_ok=True)
    DATA_DIR.mkdir(exist_ok=True)


settings = Settings()
