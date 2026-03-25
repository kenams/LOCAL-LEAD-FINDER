"""
Tests for contact extraction.
"""
from __future__ import annotations

from bs4 import BeautifulSoup
import pytest

from app.services.contact_extractor import ContactExtractor


class TestContactExtractor:
    def test_extract_emails_handles_standard_and_obfuscated_formats(self):
        extractor = ContactExtractor()
        text = "Contactez-nous a contact@coiffure.fr ou hello [at] coiffure [dot] fr"

        emails = extractor._extract_emails(text)

        assert "contact@coiffure.fr" in emails
        assert "hello@coiffure.fr" in emails

    def test_extract_phones(self):
        extractor = ContactExtractor()
        text = "Telephone: 05 61 23 45 67 ou +33 6 12 34 56 78"

        phones = extractor._extract_phones(text)

        assert "05 61 23 45 67" in phones or "0561234567" in phones

    def test_rejects_noreply_and_placeholder_domains(self):
        extractor = ContactExtractor()

        assert extractor._is_valid_business_email("contact@coiffure.fr") is True
        assert extractor._is_valid_business_email("noreply@coiffure.fr") is False
        assert extractor._is_valid_business_email("hello@example.com") is False

    def test_extract_email_candidates_from_page_uses_multiple_sources(self):
        extractor = ContactExtractor()
        html = """
        <html>
            <body>
                <footer>
                    Ecrivez-nous: footer@studio.fr
                    <a href="mailto:contact@studio.fr">Contact</a>
                </footer>
                <script type="application/ld+json">
                    {"email": "bonjour@studio.fr"}
                </script>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")

        candidates = extractor._extract_email_candidates_from_page(
            soup=soup,
            raw_html=html,
            page_url="https://studio.fr",
            page_type="homepage",
        )

        emails = {candidate["email"] for candidate in candidates}
        assert "contact@studio.fr" in emails
        assert "footer@studio.fr" in emails
        assert "bonjour@studio.fr" in emails

    def test_discover_pages_uses_links_and_common_paths(self):
        extractor = ContactExtractor()
        soup = BeautifulSoup(
            """
            <html>
                <body>
                    <a href="/contact">Contact</a>
                    <a href="/about-us">About us</a>
                    <a href="/mentions-legales">Mentions legales</a>
                </body>
            </html>
            """,
            "html.parser",
        )

        pages = extractor._discover_pages(soup, "https://studio.fr")
        urls = {page["url"] for page in pages}

        assert "https://studio.fr/contact" in urls
        assert "https://studio.fr/about-us" in urls
        assert "https://studio.fr/mentions-legales" in urls
        assert "https://studio.fr/impressum" in urls

    def test_extracts_contact_form_and_social_profiles(self):
        extractor = ContactExtractor()
        html = """
        <html>
            <body>
                <form action="/contact">
                    <input type="text" name="name" />
                    <input type="email" name="email" />
                    <textarea name="message"></textarea>
                    <button>Contact us</button>
                </form>
                <a href="https://instagram.com/studio42">Instagram</a>
                <a href="https://facebook.com/studio42">Facebook</a>
                <a href="https://wa.me/41795551212">WhatsApp</a>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")

        form_data = extractor._extract_contact_form_data(soup, "https://studio.fr/contact", "contact")
        social_profiles = extractor._extract_social_profiles(soup, "https://studio.fr")

        assert form_data["detected"] is True
        assert form_data["url"] == "https://studio.fr/contact"
        assert social_profiles["instagram_url"] == "https://instagram.com/studio42"
        assert social_profiles["facebook_url"] == "https://facebook.com/studio42"
        assert social_profiles["whatsapp_url"] == "https://wa.me/41795551212"

    def test_mailto_contact_email_is_ranked_first(self):
        extractor = ContactExtractor()
        candidates = {}

        extractor._store_candidate(candidates, "info@studio.fr", "visible_text", "https://studio.fr", "homepage")
        extractor._store_candidate(candidates, "contact@studio.fr", "mailto", "https://studio.fr/contact", "contact")

        assert extractor._select_best_email(candidates) == "contact@studio.fr"

    @pytest.mark.asyncio
    async def test_extract_contacts_returns_diagnostics_and_selected_email(self, monkeypatch):
        extractor = ContactExtractor()

        homepage_html = """
        <html>
            <body>
                <footer>info@studio.fr</footer>
                <a href="/contact">Contact</a>
            </body>
        </html>
        """
        contact_html = """
        <html>
            <body>
                <form action="/contact">
                    <input type="text" name="name" />
                    <input type="email" name="email" />
                    <textarea name="message"></textarea>
                    <button>Contact us</button>
                </form>
                <a href="mailto:contact@studio.fr">Email</a>
                <a href="https://instagram.com/studio42">Instagram</a>
                <a href="https://facebook.com/studio42">Facebook</a>
            </body>
        </html>
        """
        homepage_soup = BeautifulSoup(homepage_html, "html.parser")
        contact_soup = BeautifulSoup(contact_html, "html.parser")

        def fake_scan_page(_session, url, page_type, source):
            if page_type == "homepage":
                return {
                    "url": "https://studio.fr",
                    "page_type": "homepage",
                    "source": source,
                    "status": "ok",
                    "emails": ["info@studio.fr"],
                    "phones": [],
                    "contact_form_detected": False,
                    "contact_form_url": None,
                    "contact_form_signals": [],
                    "social_profiles": {},
                    "email_candidates": extractor._extract_email_candidates_from_page(
                        homepage_soup,
                        homepage_html,
                        "https://studio.fr",
                        "homepage",
                    ),
                    "soup": homepage_soup,
                }
            return {
                "url": "https://studio.fr/contact",
                "page_type": "contact",
                "source": source,
                "status": "ok",
                "emails": ["contact@studio.fr"],
                "phones": [],
                "contact_form_detected": True,
                "contact_form_url": "https://studio.fr/contact",
                "contact_form_signals": ["html_form"],
                "social_profiles": {
                    "instagram_url": "https://instagram.com/studio42",
                    "facebook_url": "https://facebook.com/studio42",
                },
                "email_candidates": extractor._extract_email_candidates_from_page(
                    contact_soup,
                    contact_html,
                    "https://studio.fr/contact",
                    "contact",
                ),
                "soup": contact_soup,
            }

        class FakeSession:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        monkeypatch.setattr("app.services.contact_extractor.requests.Session", lambda: FakeSession())
        monkeypatch.setattr(extractor, "_scan_page", fake_scan_page)

        result = await extractor.extract_contacts("https://studio.fr")

        assert result["email"] == "contact@studio.fr"
        assert result["contact_page"] == "https://studio.fr/contact"
        assert result["contact_extraction"]["selected_email"] == "contact@studio.fr"
        assert result["contact_extraction"]["selected_email_source"] == "mailto"
        assert result["contact_extraction"]["selected_channel"] == "email"
        assert result["contact_form_url"] == "https://studio.fr/contact"
        assert result["contact_form_detected"] is True
        assert result["instagram_url"] == "https://instagram.com/studio42"
        assert result["facebook_url"] == "https://facebook.com/studio42"
        assert len(result["contact_extraction"]["pages_scanned"]) >= 2
        assert result["contact_extraction"]["fallback_reason"] == ""

    @pytest.mark.asyncio
    async def test_extract_contacts_reports_fallback_reason_when_no_email_found(self, monkeypatch):
        extractor = ContactExtractor()

        def fake_scan_page(_session, url, page_type, source):
            return {
                "url": url,
                "page_type": page_type,
                "source": source,
                "status": "ok",
                "emails": [],
                "phones": [],
                "contact_form_detected": False,
                "contact_form_url": None,
                "contact_form_signals": [],
                "social_profiles": {},
                "email_candidates": [],
                "soup": BeautifulSoup("<html></html>", "html.parser"),
            }

        class FakeSession:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        monkeypatch.setattr("app.services.contact_extractor.requests.Session", lambda: FakeSession())
        monkeypatch.setattr(extractor, "_scan_page", fake_scan_page)
        monkeypatch.setattr(extractor, "_discover_pages", lambda soup, base_url: [])

        result = await extractor.extract_contacts("https://studio.fr")

        assert result["email"] is None
        assert result["contact_extraction"]["selected_channel"] == "unavailable"
        assert result["contact_extraction"]["fallback_reason"] == "empty_page"
