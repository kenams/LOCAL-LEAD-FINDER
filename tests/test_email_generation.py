"""
Test email generation.
"""
from app.core.sender_identity import DEFAULT_SENDER_IDENTITY
from app.services.email_generator import EmailGenerator


class TestEmailGenerator:
    def test_generate_french_landing_page_email(self):
        generator = EmailGenerator()
        prospect = {
            "business_name": "Studio Launch",
            "category": "consultant",
            "location": "Paris",
            "country": "FR",
            "email_language": "fr",
            "website": "https://studio-launch.fr",
            "website_page_count": 1,
            "new_business_score": 78,
            "target_type": "early_stage_business",
        }

        email = generator.generate_email(prospect, "fr")

        assert email["selected_offer_type"] == "landing_page"
        assert "attirer plus de clients" in email["subject"]
        assert "landing pages modernes" in email["body"]
        assert "autour de 300 EUR" in email["body"]
        assert "3 a 5 jours" in email["body"]
        assert DEFAULT_SENDER_IDENTITY.sender_display_name in email["body"]
        assert DEFAULT_SENDER_IDENTITY.professional_email in email["body"]
        assert email["html_body"].startswith("<!DOCTYPE html>")
        assert email["short_subject"]
        assert "day_2" in email["follow_ups"]
        assert "day_5" in email["follow_ups"]
        assert "day_10" in email["follow_ups"]

    def test_generate_english_website_email(self):
        generator = EmailGenerator()
        prospect = {
            "business_name": "Growth Advisory",
            "category": "financial advisor",
            "location": "New York",
            "country": "US",
            "email_language": "en",
            "website_page_count": 6,
            "new_business_score": 18,
            "target_type": "established_business",
        }

        email = generator.generate_email(prospect, "en")

        assert email["selected_offer_type"] == "website"
        assert "more professional" in email["subject"].lower()
        assert "showcase websites" in email["body"]
        assert "between 500 USD and 700 USD" in email["body"]
        assert "5 to 7 days" in email["body"]
        assert DEFAULT_SENDER_IDENTITY.sender_display_name in email["body"]
        assert DEFAULT_SENDER_IDENTITY.professional_email in email["body"]
        assert email["short_body"]
        assert "suggest a clearer version" in email["follow_ups"]["day_2"]["body"]

    def test_generate_swiss_email_stays_french(self):
        generator = EmailGenerator()
        prospect = {
            "business_name": "Studio Geneve",
            "category": "agency",
            "location": "Geneva",
            "country": "CH",
            "email_language": "fr",
            "website_page_count": 4,
            "target_type": "established_business",
        }

        email = generator.generate_email(prospect, "fr")
        assert email["selected_offer_type"] == "website"
        assert "500 CHF" in email["body"]
        assert "700 CHF" in email["body"]

    def test_early_stage_business_defaults_to_landing_page(self):
        generator = EmailGenerator()
        prospect = {
            "business_name": "Coach Start",
            "category": "coach",
            "location": "Geneva",
            "country": "CH",
            "email_language": "fr",
            "website_page_count": 2,
            "target_type": "early_stage_business",
        }

        email = generator.generate_email(prospect, "fr")
        assert email["selected_offer_type"] == "landing_page"
        assert "landing pages modernes" in email["body"]

    def test_email_body_stays_short_and_clear(self):
        generator = EmailGenerator()
        prospect = {
            "business_name": "Cabinet Local",
            "category": "lawyer",
            "location": "Geneva",
            "country": "CH",
            "email_language": "fr",
            "website_page_count": 5,
        }

        email = generator.generate_email(prospect, "fr")
        assert email["body"].count("\n\n") >= 4
        assert "Je propose des sites vitrines simples et modernes" in email["body"]

    def test_trade_landing_page_uses_quote_angle(self):
        generator = EmailGenerator()
        prospect = {
            "business_name": "Depannage Express",
            "category": "plombier",
            "location": "Lyon",
            "country": "FR",
            "email_language": "fr",
            "website_page_count": 1,
            "target_type": "early_stage_business",
        }

        email = generator.generate_email(prospect, "fr")

        assert email["selected_offer_type"] == "landing_page"
        assert "devis" in email["subject"].lower()
        assert "demande de devis plus rapide" in email["body"]

    def test_detected_issues_are_injected_as_short_personalization(self):
        generator = EmailGenerator()
        prospect = {
            "business_name": "Studio Fresh",
            "category": "consultant",
            "location": "Paris",
            "country": "FR",
            "email_language": "fr",
            "website_page_count": 2,
            "detected_issues": ["no_cta", "old_design"],
        }

        email = generator.generate_email(prospect, "fr")

        assert "Ce qui me fait penser cela" in email["body"]
        assert "peu d'appels a l'action visibles" in email["body"]
        assert "presentation visuelle datee" in email["body"]

    def test_strong_site_uses_optimization_angle_instead_of_generic_redesign(self):
        generator = EmailGenerator()
        prospect = {
            "business_name": "KAH-Digital",
            "category": "agency",
            "location": "Lausanne",
            "country": "CH",
            "email_language": "fr",
            "website_page_count": 6,
            "site_quality_score": 82,
            "has_modern_ui": True,
            "has_seo_foundation": True,
            "target_type": "growth_opportunity",
        }

        email = generator.generate_email(prospect, "fr")

        assert email["selected_offer_type"] == "website"
        assert "plus ciblée" in email["subject"]
        assert "Votre site donne deja une bonne image" in email["body"]
        assert "pages plus ciblees" in email["body"]
        assert "preuves et cas clients plus visibles" in email["body"]

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
