"""
Database session management
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings
from app.db.base import Base

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Session:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database"""
    from app.models import prospect, search_run, schedule
    from sqlalchemy import text

    # Create tables
    Base.metadata.create_all(bind=engine)
    _ensure_prospect_columns()
    _ensure_search_run_columns()
    _ensure_schedule_columns()

    # Create indexes
    with engine.connect() as conn:
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_prospects_location ON prospects(location)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_prospects_category ON prospects(category)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_prospects_status ON prospects(status)"))
        conn.commit()


def _ensure_prospect_columns():
    """Apply lightweight SQLite schema upgrades for new prospect fields."""
    from sqlalchemy import text

    required_columns = {
        "currency": "VARCHAR",
        "priority_score": "FLOAT",
        "new_business_score": "FLOAT",
        "target_type": "VARCHAR",
        "selected_offer_type": "VARCHAR",
        "website_page_count": "INTEGER",
        "website_content_length": "INTEGER",
        "has_booking_system": "BOOLEAN",
        "has_seo_foundation": "BOOLEAN",
        "has_modern_ui": "BOOLEAN",
        "social_first_business": "BOOLEAN",
        "mockup_url": "TEXT",
        "mockup_status": "VARCHAR",
        "netlify_site_id": "VARCHAR",
        "netlify_deploy_id": "VARCHAR",
        "email_html_fr": "TEXT",
        "email_html_en": "TEXT",
        "selected_outreach_channel": "VARCHAR",
        "outreach_status": "VARCHAR",
        "send_status": "VARCHAR",
        "first_sent_at": "DATETIME",
        "last_attempt_at": "DATETIME",
        "send_attempts": "INTEGER",
        "last_send_error": "TEXT",
    }

    with engine.connect() as conn:
        existing_columns = {
            row[1]
            for row in conn.execute(text("PRAGMA table_info(prospects)")).fetchall()
        }

        for column_name, column_type in required_columns.items():
            if column_name not in existing_columns:
                conn.execute(text(f"ALTER TABLE prospects ADD COLUMN {column_name} {column_type}"))

        conn.commit()


def _ensure_search_run_columns():
    """Apply lightweight SQLite schema upgrades for search runs."""
    from sqlalchemy import text

    required_columns = {
        "diagnostics_json": "TEXT",
    }

    with engine.connect() as conn:
        existing_columns = {
            row[1]
            for row in conn.execute(text("PRAGMA table_info(search_runs)")).fetchall()
        }

        for column_name, column_type in required_columns.items():
            if column_name not in existing_columns:
                conn.execute(text(f"ALTER TABLE search_runs ADD COLUMN {column_name} {column_type}"))

        conn.commit()


def _ensure_schedule_columns():
    """Apply lightweight SQLite schema upgrades for schedules."""
    from sqlalchemy import text

    required_columns = {
        "next_run": "DATETIME",
        "last_status": "VARCHAR",
        "last_error": "TEXT",
        "last_report_path": "VARCHAR",
    }

    with engine.connect() as conn:
        existing_columns = {
            row[1]
            for row in conn.execute(text("PRAGMA table_info(schedules)")).fetchall()
        }

        for column_name, column_type in required_columns.items():
            if column_name not in existing_columns:
                conn.execute(text(f"ALTER TABLE schedules ADD COLUMN {column_name} {column_type}"))

        conn.commit()
