"""
Schedule model
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from datetime import datetime
from app.db.base import Base

class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    cron_expression = Column(String, nullable=False)  # e.g., "0 9 */2 * *" for every 2 days at 9am
    locations = Column(String, nullable=False)
    categories = Column(String, nullable=False)
    limit_per_location = Column(Integer, default=10)
    language = Column(String, default="fr")
    enabled = Column(Boolean, default=True)
    last_run = Column(DateTime)
    next_run = Column(DateTime)
    last_status = Column(String, default="IDLE")
    last_error = Column(Text)
    last_report_path = Column(String)
    configs_json = Column(Text)
    last_used_config_index = Column(Integer)
    last_run_config = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Schedule(id={self.id}, name='{self.name}', enabled={self.enabled})>"
