"""
Prospect schemas
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class ProspectBase(BaseModel):
    business_name: str
    category: str
    location: str
    country: Optional[str] = "FR"
    currency: Optional[str] = "EUR"
    address: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    website: Optional[str]
    contact_page: Optional[str]
    reviews_count: Optional[int]
    source: Optional[str]

class ProspectCreate(ProspectBase):
    pass

class ProspectUpdate(BaseModel):
    status: Optional[str]
    opportunity_score: Optional[float]
    site_quality_score: Optional[float]
    new_business_score: Optional[float]
    target_type: Optional[str]
    selected_offer_type: Optional[str]
    website_page_count: Optional[int]
    website_content_length: Optional[int]
    has_booking_system: Optional[bool]
    has_seo_foundation: Optional[bool]
    has_modern_ui: Optional[bool]
    social_first_business: Optional[bool]
    feasibility: Optional[str]
    estimated_time: Optional[str]
    estimated_price_min: Optional[float]
    estimated_price_max: Optional[float]
    priority_score: Optional[float]
    detected_issues: Optional[str]
    email_language: Optional[str]
    email_subject_fr: Optional[str]
    email_body_fr: Optional[str]
    email_html_fr: Optional[str]
    email_subject_en: Optional[str]
    email_body_en: Optional[str]
    email_html_en: Optional[str]
    selected_outreach_channel: Optional[str]
    outreach_status: Optional[str]
    send_status: Optional[str]
    first_sent_at: Optional[datetime]
    last_attempt_at: Optional[datetime]
    send_attempts: Optional[int]
    last_send_error: Optional[str]
    mockup_url: Optional[str]
    mockup_status: Optional[str]
    netlify_site_id: Optional[str]
    netlify_deploy_id: Optional[str]
    notes: Optional[str]

class Prospect(ProspectBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    collected_at: datetime
    status: str
    opportunity_score: Optional[float]
    site_quality_score: Optional[float]
    new_business_score: Optional[float]
    target_type: Optional[str]
    selected_offer_type: Optional[str]
    website_page_count: Optional[int]
    website_content_length: Optional[int]
    has_booking_system: Optional[bool]
    has_seo_foundation: Optional[bool]
    has_modern_ui: Optional[bool]
    social_first_business: Optional[bool]
    feasibility: Optional[str]
    estimated_time: Optional[str]
    estimated_price_min: Optional[float]
    estimated_price_max: Optional[float]
    priority_score: Optional[float]
    detected_issues: Optional[str]
    email_language: str
    email_subject_fr: Optional[str]
    email_body_fr: Optional[str]
    email_html_fr: Optional[str]
    email_subject_en: Optional[str]
    email_body_en: Optional[str]
    email_html_en: Optional[str]
    selected_outreach_channel: Optional[str]
    outreach_status: Optional[str]
    send_status: Optional[str]
    first_sent_at: Optional[datetime]
    last_attempt_at: Optional[datetime]
    send_attempts: Optional[int]
    last_send_error: Optional[str]
    mockup_url: Optional[str]
    mockup_status: Optional[str]
    netlify_site_id: Optional[str]
    netlify_deploy_id: Optional[str]
    notes: Optional[str]
