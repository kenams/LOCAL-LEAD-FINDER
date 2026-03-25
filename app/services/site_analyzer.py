"""
Site analysis service
"""
from typing import Dict

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

    async def analyze_site(self, website: str, country: str = "FR", language: str = "fr") -> Dict:
        """Analyze website and return localized scores and pricing."""
        result = {
            "site_quality_score": 0,
            "opportunity_score": 0,
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

            quality_score = self._calculate_quality_score(checks)
            opportunity_score = self._calculate_opportunity_score(checks)
            feasibility = self._determine_feasibility(checks)

            result.update(
                {
                    "site_quality_score": quality_score,
                    "opportunity_score": opportunity_score,
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

        return min(100, max(0, base_score))

    def _determine_feasibility(self, checks: Dict[str, bool]) -> str:
        """Determine project feasibility."""
        failed_count = sum(1 for value in checks.values() if not value)

        if failed_count <= 2:
            return "EASY"
        if failed_count <= 5:
            return "MEDIUM"
        return "ADVANCED"

    def _estimate_price(self, feasibility: str, country: str) -> Dict[str, float | str]:
        """Estimate price range for the given market."""
        profile = get_country_profile(country)
        min_price, max_price = profile.price_ranges.get(feasibility, profile.price_ranges["EASY"])
        return {
            "estimated_price_min": float(min_price),
            "estimated_price_max": float(max_price),
            "currency": profile.currency,
        }
