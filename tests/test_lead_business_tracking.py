"""
Tests for lightweight business tracking on prospects.
"""
from app.db.session import SessionLocal, init_db
from app.models.prospect import Prospect
from app.services.lead_service import LeadService


def test_update_prospect_status_tracks_response_and_value():
    init_db()
    db = SessionLocal()
    try:
        prospect = Prospect(
            business_name="Studio Reply",
            category="consultant",
            location="Geneva",
            country="CH",
            currency="CHF",
            email="hello@example.com",
            send_status="SENT",
            selected_offer_type="landing_page",
        )
        db.add(prospect)
        db.commit()
        db.refresh(prospect)
        prospect_id = prospect.id
    finally:
        db.close()

    service = LeadService()
    updated = service.update_prospect_status(
        prospect_id,
        response_status="INTERESTED",
        potential_deal_value=450.0,
        reply_notes="Positive reply",
    )

    assert updated is True

    db = SessionLocal()
    refreshed = None
    try:
        refreshed = db.query(Prospect).filter(Prospect.id == prospect_id).first()
        assert refreshed is not None
        assert refreshed.response_status == "INTERESTED"
        assert refreshed.potential_deal_value == 450.0
        assert refreshed.reply_notes == "Positive reply"
        assert refreshed.replied_at is not None
    finally:
        if refreshed is not None:
            db.delete(refreshed)
            db.commit()
        db.close()
