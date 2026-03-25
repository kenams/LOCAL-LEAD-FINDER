"""
Tests for closing-ready contact strategy assets.
"""
from app.services.contact_strategy import ContactStrategy


def test_contact_strategy_generates_sequence_assets():
    strategy = ContactStrategy()
    prospect = {
        "business_name": "Maison Studio",
        "category": "hair salon",
        "email_language": "fr",
        "email_body_fr": "Primary email FR",
        "email_short_subject_fr": "Sujet court",
        "email_short_fr": "Short FR",
        "follow_ups_fr": {
            "day_2": {"subject": "J+2", "body": "Body J+2"},
            "day_5": {"subject": "J+5", "body": "Body J+5"},
            "day_10": {"subject": "J+10", "body": "Body J+10"},
        },
        "mockup_url": "https://demo.netlify.app",
    }

    messages = strategy.generate_messages(prospect)

    assert messages["short_email"]["subject"] == "Sujet court"
    assert messages["follow_up_day_2"]["subject"] == "J+2"
    assert "https://demo.netlify.app" in messages["sms_message"]
    assert "KAH.DIGITAL" in messages["call_script"]


def test_contact_strategy_prioritizes_phone_then_form_then_social():
    strategy = ContactStrategy()

    assert strategy.determine_strategy({"email": "lead@example.com", "phone": "+33123456789"}) == "email"
    assert strategy.determine_strategy({"phone": "+33123456789"}) == "phone"
    assert strategy.determine_strategy({"contact_form_url": "https://studio.fr/contact"}) == "contact_form"
    assert strategy.determine_strategy({"instagram_url": "https://instagram.com/studio"}) == "instagram"
    assert strategy.determine_strategy({"facebook_url": "https://facebook.com/studio"}) == "facebook"
    assert strategy.determine_strategy({}) == "unavailable"
