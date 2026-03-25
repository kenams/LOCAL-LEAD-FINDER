"""
Tests for lead filtering.
"""
from app.services.lead_filter import LeadFilter


def test_validate_before_analysis_rejects_missing_website():
    lead_filter = LeadFilter()
    lead = {
        "business_name": "Salon Test",
        "website": "",
        "phone": "+41 22 000 00 00",
        "email": None,
    }

    assert lead_filter.validate_before_analysis(lead) == "no website"


def test_validate_after_contact_extraction_rejects_missing_contact():
    lead_filter = LeadFilter()
    lead = {
        "business_name": "Studio Test",
        "website": "https://studio.test",
        "email": "",
        "phone": "",
        "contact_extraction": {"fallback_reason": "no_email_found"},
    }

    assert lead_filter.validate_after_contact_extraction(lead) == "no contact method"


def test_validate_after_contact_extraction_rejects_broken_website():
    lead_filter = LeadFilter()
    lead = {
        "business_name": "Broken Site",
        "website": "https://broken.test",
        "email": "",
        "phone": "",
        "contact_extraction": {"fallback_reason": "page_fetch_failed"},
    }

    assert lead_filter.validate_after_contact_extraction(lead) == "low_quality_website"
