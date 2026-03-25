"""
Site analysis service
"""
from typing import Any, Dict
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from app.core.config import settings
from app.core.country_config import get_country_profile, get_estimated_time
from app.core.logging import logger


class SiteAnalyzer:
    """Analyze website quality and opportunity."""

    def __init__(self):
        self.service_keywords = (
            "service",
            "services",
            "prestation",
            "prestations",
            "offer",
            "offers",
            "menu",
            "booking",
            "appointment",
        )
        self.contact_keywords = (
            "contact",
            "telephone",
            "phone",
            "email",
            "adresse",
            "address",
            "call us",
            "get in touch",
        )
        self.cta_keywords = (
            "reservation",
            "reserver",
            "contactez",
            "appelez",
            "demande",
            "book now",
            "get quote",
            "request quote",
            "schedule",
        )
        self.booking_keywords = (
            "book now",
            "booking",
            "appointment",
            "reserve",
            "reservation",
            "reserver",
            "book online",
            "prendre rendez-vous",
            "rdv",
            "calendly",
        )
        self.modern_ui_selectors = ("header", "nav", "main", "section", "button", "picture")

    async def analyze_site(
        self,
        website: str,
        country: str = "FR",
        language: str = "fr",
        *,
        reviews_count: int | None = None,
        instagram_url: str | None = None,
    ) -> Dict[str, Any]:
        """Analyze website and return localized scores and pricing."""
        result = {
            "site_quality_score": 0,
            "opportunity_score": 0,
            "new_business_score": 0,
            "target_type": "growth_opportunity",
            "website_page_count": 0,
            "website_content_length": 0,
            "has_booking_system": False,
            "has_seo_foundation": False,
            "has_modern_ui": False,
            "social_first_business": False,
            "feasibility": "UNKNOWN",
            "estimated_time": "UNKNOWN",
            "estimated_price_min": 0,
            "estimated_price_max": 0,
            "currency": get_country_profile(country).currency,
            "detected_issues": [],
        }

        if not website:
            result.update(
                {
                    "site_quality_score": 0,
                    "opportunity_score": 95,
                    "new_business_score": 92,
                    "target_type": "early_stage_business",
                    "feasibility": "EASY",
                    "estimated_time": get_estimated_time("EASY", language),
                    "detected_issues": ["no_website", "missing_digital_presence"],
                }
            )
            result.update(self._estimate_price("EASY", country))
            return result

        try:
            response = requests.get(
                website,
                headers={"User-Agent": settings.USER_AGENT},
                timeout=settings.REQUEST_TIMEOUT,
            )
            response.raise_for_status()

            if response.status_code >= 400:
                result["detected_issues"].append("site_unreachable")
                return result

            soup = BeautifulSoup(response.text, "html.parser")
            checks = await self._perform_checks(soup, response, website)
            page_count = self._estimate_page_count(soup, response.url)
            content_length = len(soup.get_text(" ", strip=True))

            quality_score = self._calculate_quality_score(checks)
            opportunity_score = self._calculate_opportunity_score(checks)
            new_business_profile = self._derive_new_business_profile(
                checks=checks,
                page_count=page_count,
                content_length=content_length,
                reviews_count=reviews_count,
                instagram_url=instagram_url,
                quality_score=quality_score,
                opportunity_score=opportunity_score,
            )
            feasibility = self._determine_feasibility(checks)

            result.update(
                {
                    "site_quality_score": quality_score,
                    "opportunity_score": opportunity_score,
                    "new_business_score": new_business_profile["new_business_score"],
                    "target_type": new_business_profile["target_type"],
                    "website_page_count": page_count,
                    "website_content_length": content_length,
                    "has_booking_system": checks.get("has_booking_system", False),
                    "has_seo_foundation": checks.get("has_seo_foundation", False),
                    "has_modern_ui": checks.get("has_modern_ui", False),
                    "social_first_business": new_business_profile["social_first_business"],
                    "feasibility": feasibility,
                    "estimated_time": get_estimated_time(feasibility, language),
                    "detected_issues": [key for key, passed in checks.items() if not passed],
                }
            )
            result.update(self._estimate_price(feasibility, country))
        except Exception as e:
            logger.warning(f"Site analysis failed for {website}: {e}")
            result["detected_issues"].append("analysis_failed")

        return result

    async def _perform_checks(self, soup: BeautifulSoup, response, website: str) -> Dict[str, bool]:
        """Perform various checks on the site."""
        text_content = soup.get_text(" ", strip=True).lower()
        seo_foundation = (
            bool(soup.title and soup.title.string and soup.title.string.strip())
            and bool(soup.find("meta", {"name": "description"}))
            and bool(soup.find("h1"))
        )
        has_stylesheet = bool(soup.find("link", rel=lambda value: value and "stylesheet" in str(value).lower()))
        modern_sections = sum(1 for selector in self.modern_ui_selectors if soup.find(selector))
        has_modern_ui = bool(soup.find("meta", {"name": "viewport"})) and has_stylesheet and modern_sections >= 4
        has_booking_system = any(word in text_content for word in self.booking_keywords)

        return {
            "has_https": website.startswith("https://"),
            "has_title": bool(soup.title and soup.title.string and soup.title.string.strip()),
            "has_meta_description": bool(soup.find("meta", {"name": "description"})),
            "has_h1": bool(soup.find("h1")),
            "has_services": any(word in text_content for word in self.service_keywords),
            "has_contact_info": any(word in text_content for word in self.contact_keywords),
            "has_cta": any(word in text_content for word in self.cta_keywords),
            "has_responsive_meta": bool(soup.find("meta", {"name": "viewport"})),
            "reasonable_size": len(response.text) > 1000,
            "has_images": bool(soup.find("img")),
            "has_booking_system": has_booking_system,
            "has_seo_foundation": seo_foundation,
            "has_modern_ui": has_modern_ui,
        }

    def _calculate_quality_score(self, checks: Dict[str, bool]) -> float:
        """Calculate site quality score 0-100."""
        weights = {
            "has_https": 10,
            "has_title": 15,
            "has_meta_description": 10,
            "has_h1": 10,
            "has_services": 15,
            "has_contact_info": 15,
            "has_cta": 10,
            "has_responsive_meta": 10,
            "reasonable_size": 5,
            "has_images": 10,
            "has_booking_system": 5,
            "has_seo_foundation": 10,
            "has_modern_ui": 10,
        }
        score = sum(weights.get(key, 0) for key, passed in checks.items() if passed)
        return min(100, score)

    def _calculate_opportunity_score(self, checks: Dict[str, bool]) -> float:
        """Calculate opportunity score based on improvement potential."""
        failed_checks = [key for key, value in checks.items() if not value]
        base_score = len(failed_checks) * 12

        if checks.get("has_contact_info"):
            base_score += 15
        if not checks.get("has_cta"):
            base_score += 10
        if not checks.get("has_responsive_meta"):
            base_score += 10
        if not checks.get("has_booking_system"):
            base_score += 8
        if not checks.get("has_seo_foundation"):
            base_score += 10
        if not checks.get("has_modern_ui"):
            base_score += 8

        return min(100, max(0, base_score))

    def _determine_feasibility(self, checks: Dict[str, bool]) -> str:
        """Determine project feasibility."""
        failed_count = sum(1 for value in checks.values() if not value)

        if failed_count <= 2:
            return "EASY"
        if failed_count <= 5:
            return "MEDIUM"
        return "ADVANCED"

    def _estimate_page_count(self, soup: BeautifulSoup, page_url: str) -> int:
        """Estimate website complexity from unique internal links on the homepage."""
        parsed = urlparse(page_url)
        hostname = parsed.netloc.lower()
        paths = {"/"}

        for anchor in soup.find_all("a", href=True):
            href = (anchor.get("href") or "").strip()
            if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue
            absolute = urljoin(page_url, href)
            absolute_parsed = urlparse(absolute)
            if absolute_parsed.netloc.lower() != hostname:
                continue
            normalized_path = absolute_parsed.path.rstrip("/") or "/"
            paths.add(normalized_path)
            if len(paths) >= 12:
                break

        return len(paths)

    def _derive_new_business_profile(
        self,
        *,
        checks: Dict[str, bool],
        page_count: int,
        content_length: int,
        reviews_count: int | None,
        instagram_url: str | None,
        quality_score: float,
        opportunity_score: float,
    ) -> Dict[str, Any]:
        """Estimate whether the lead looks early-stage or growth-oriented."""
        score = 0

        if page_count <= 3:
            score += 24
        elif page_count <= 6:
            score += 12

        if content_length < 1800:
            score += 20
        elif content_length < 3500:
            score += 10

        if quality_score < 45:
            score += 16
        elif quality_score < 65:
            score += 8

        if not checks.get("has_booking_system"):
            score += 10
        if not checks.get("has_seo_foundation"):
            score += 14
        if not checks.get("has_modern_ui"):
            score += 10

        if reviews_count is not None:
            if reviews_count <= 5:
                score += 18
            elif reviews_count <= 20:
                score += 8

        social_first_business = bool(instagram_url) and quality_score < 65
        if social_first_business:
            score += 10

        score = min(100, score)
        if score >= 65:
            target_type = "early_stage_business"
        elif score >= 40 or opportunity_score >= 75:
            target_type = "growth_opportunity"
        else:
            target_type = "established_business"

        return {
            "new_business_score": score,
            "target_type": target_type,
            "social_first_business": social_first_business,
        }

    def _estimate_price(self, feasibility: str, country: str) -> Dict[str, float | str]:
        """Estimate price range for the given market."""
        profile = get_country_profile(country)
        min_price, max_price = profile.price_ranges.get(feasibility, profile.price_ranges["EASY"])
        return {
            "estimated_price_min": float(min_price),
            "estimated_price_max": float(max_price),
            "currency": profile.currency,
        }
