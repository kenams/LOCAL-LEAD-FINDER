"""
Search run model
"""
from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime
from app.db.base import Base

class SearchRun(Base):
    __tablename__ = "search_runs"

    id = Column(Integer, primary_key=True, index=True)
    locations = Column(String, nullable=False)  # Comma-separated
    categories = Column(String, nullable=False)  # Comma-separated
    limit_per_location = Column(Integer, nullable=False)
    language = Column(String, default="fr")
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    prospects_found = Column(Integer, default=0)
    status = Column(String, default="RUNNING")  # RUNNING, COMPLETED, FAILED
    error_message = Column(Text)
    diagnostics_json = Column(Text)

    def __repr__(self):
        return f"<SearchRun(id={self.id}, locations='{self.locations}', status='{self.status}')>"
