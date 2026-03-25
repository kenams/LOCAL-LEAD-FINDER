"""
Tests for lead filtering.
"""
from app.services.lead_filter import LeadFilter


def test_lead_without_website_but_with_phone_can_pass():
    lead_filter = LeadFilter()
    lead = {
        "business_name": "Salon Test",
        "opportunity_score": 95,
        "website": "",
        "phone": "+41 22 000 00 00",
        "email": None,
        "site_quality_score": 0,
    }

    filtered, rejected = lead_filter.filter_leads([lead])
    assert len(filtered) == 1
    assert not rejected
