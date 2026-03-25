"""
Prospect model
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from datetime import datetime
from app.db.base import Base

class Prospect(Base):
    __tablename__ = "prospects"

    id = Column(Integer, primary_key=True, index=True)
    business_name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    location = Column(String, nullable=False)
    country = Column(String, default="FR")
    currency = Column(String, default="EUR")
    address = Column(String)
    phone = Column(String)
    email = Column(String)
    website = Column(String)
    contact_page = Column(String)
    reviews_count = Column(Integer)
    source = Column(String)
    collected_at = Column(DateTime, default=datetime.utcnow)

    # Processing
    status = Column(String, default="NEW")  # NEW, REVIEWED, MAQUETTE_READY, CONTACTED, WON, LOST
    opportunity_score = Column(Float)
    site_quality_score = Column(Float)
    new_business_score = Column(Float)
    target_type = Column(String)
    selected_offer_type = Column(String)
    website_page_count = Column(Integer)
    website_content_length = Column(Integer)
    has_booking_system = Column(Boolean, default=False)
    has_seo_foundation = Column(Boolean, default=False)
    has_modern_ui = Column(Boolean, default=False)
    social_first_business = Column(Boolean, default=False)
    feasibility = Column(String)  # EASY, MEDIUM, ADVANCED
    estimated_time = Column(String)  # 1-2 days, 3-5 days, 5-10 days
    estimated_price_min = Column(Float)
    estimated_price_max = Column(Float)
    priority_score = Column(Float)
    detected_issues = Column(Text)  # JSON string

    # Email generation
    email_language = Column(String, default="fr")
    email_subject_fr = Column(String)
    email_body_fr = Column(Text)
    email_html_fr = Column(Text)
    email_subject_en = Column(String)
    email_body_en = Column(Text)
    email_html_en = Column(Text)
    selected_outreach_channel = Column(String, default="skipped")
    outreach_status = Column(String, default="NOT_SENT")
    send_status = Column(String, default="NOT_SENT")
    first_sent_at = Column(DateTime)
    last_attempt_at = Column(DateTime)
    send_attempts = Column(Integer, default=0)
    last_send_error = Column(Text)
    response_status = Column(String, default="NO_RESPONSE")
    replied_at = Column(DateTime)
    potential_deal_value = Column(Float)
    reply_notes = Column(Text)

    mockup_url = Column(String)
    mockup_status = Column(String, default="pending")
    netlify_site_id = Column(String)
    netlify_deploy_id = Column(String)
    notes = Column(Text)

    def __repr__(self):
        return f"<Prospect(id={self.id}, name='{self.business_name}', location='{self.location}')>"
