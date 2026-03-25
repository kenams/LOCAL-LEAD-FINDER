"""
Test email generation.
"""
from app.core.sender_identity import DEFAULT_SENDER_IDENTITY
from app.services.email_generator import EmailGenerator


class TestEmailGenerator:
    def test_generate_french_email(self):
        generator = EmailGenerator()
        prospect = {
            "business_name": "Coiffure Plus",
            "category": "coiffeur",
            "location": "Toulouse",
            "country": "FR",
            "email_language": "fr",
            "website": "https://coiffureplus.fr",
            "detected_issues": ["no_cta", "old_design"],
            "estimated_price_min": 500,
            "estimated_price_max": 800,
            "estimated_time": "1 a 2 jours",
        }

        email = generator.generate_email(prospect, "fr")

        assert "Coiffure Plus" in email["subject"]
        assert "premium" in email["body"]
        assert "500 EUR" in email["body"]
        assert "800 EUR" in email["body"]
        assert DEFAULT_SENDER_IDENTITY.sender_display_name in email["body"]
        assert DEFAULT_SENDER_IDENTITY.professional_email in email["body"]
        assert email["html_body"].startswith("<!DOCTYPE html>")
        assert email["short_subject"]
        assert "day_2" in email["follow_ups"]
        assert "day_5" in email["follow_ups"]
        assert "day_10" in email["follow_ups"]

    def test_generate_english_email(self):
        generator = EmailGenerator()
        prospect = {
            "business_name": "Beauty Salon",
            "category": "institut de beaute",
            "location": "New York",
            "country": "US",
            "email_language": "en",
            "detected_issues": ["no_booking"],
            "estimated_price_min": 1500,
            "estimated_price_max": 2200,
        }

        email = generator.generate_email(prospect, "en")

        assert "Beauty Salon" in email["subject"]
        assert "booking" in email["body"]
        assert "$1500" in email["body"]
        assert "$2200" in email["body"]
        assert DEFAULT_SENDER_IDENTITY.sender_display_name in email["body"]
        assert DEFAULT_SENDER_IDENTITY.professional_email in email["body"]
        assert email["short_body"]
        assert "YES" in email["follow_ups"]["day_2"]["body"]

    def test_generate_swiss_email_stays_french(self):
        generator = EmailGenerator()
        prospect = {
            "business_name": "Studio Geneve",
            "category": "spa",
            "location": "Geneva",
            "country": "CH",
            "email_language": "fr",
            "estimated_price_min": 1200,
            "estimated_price_max": 1800,
        }

        email = generator.generate_email(prospect, "fr")
        assert "1200 CHF" in email["body"]
        assert "1800 CHF" in email["body"]

    def test_mockup_link_is_injected_naturally(self):
        generator = EmailGenerator()
        prospect = {
            "business_name": "Studio Geneve",
            "category": "spa",
            "location": "Geneva",
            "country": "CH",
            "email_language": "fr",
            "mockup_url": "https://demo.netlify.app",
        }

        email = generator.generate_email(prospect, "fr")
        assert "https://demo.netlify.app" in email["body"]
        assert "https://demo.netlify.app" in email["html_body"]

    def test_no_website_uses_presence_hook(self):
        generator = EmailGenerator()
        prospect = {
            "business_name": "Salon Local",
            "category": "coiffeur",
            "location": "Geneva",
            "country": "CH",
            "email_language": "fr",
            "website": "",
            "phone": "+41 22 000 00 00",
        }

        email = generator.generate_email(prospect, "fr")
        assert "presence digitale" in email["body"]

    def test_email_without_mockup_does_not_force_preview_link(self):
        generator = EmailGenerator()
        prospect = {
            "business_name": "Cabinet Local",
            "category": "avocat",
            "location": "Paris",
            "country": "FR",
            "email_language": "fr",
            "website": "https://cabinet-local.fr",
        }

        email = generator.generate_email(prospect, "fr")
        assert "maquette en ligne" not in email["body"].lower()
        assert "netlify.app" not in email["body"].lower()
