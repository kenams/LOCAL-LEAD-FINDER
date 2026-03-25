#!/usr/bin/env python3
"""
Test database initialization
"""
import sys
from app.db.session import init_db
from app.models.prospect import Prospect
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from sqlalchemy import create_engine

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

print("Testing database initialization...")

try:
    # Create engine
    engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
    print(f"Database URL: {settings.DATABASE_URL}")

    # Initialize DB
    init_db()
    print("Database initialized successfully")

    # Test creating a session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    # Test query
    prospects = db.query(Prospect).all()
    print(f"Found {len(prospects)} prospects in database")

    db.close()
    print("✅ Database test successful")

except Exception as e:
    print(f"❌ Database test failed: {e}")
    import traceback
    traceback.print_exc()
