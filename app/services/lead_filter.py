"""
Lead filtering service
Filters prospects based on business potential criteria
"""
from urllib.parse import urlparse

from typing import List, Dict, Tuple

from app.core.config import settings
from app.core.logging import logger
from app.core.search_config import should_skip_domain

class LeadFilter:
    """Filters leads to keep only high-potential prospects"""

    def __init__(self):
        self.min_opportunity_score = settings.AUTO_MODE_MIN_OPPORTUNITY_SCORE
        self.min_site_quality_score = 10
        self.placeholder_domains = {"example.com", "example.org", "example.net", "domain.com", "invalid", "localhost"}

    def filter_leads(self, leads: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Filter leads based on business criteria

        Args:
            leads: List of prospect dictionaries

        Returns:
            Tuple of (filtered_leads, rejected_leads_with_reasons)
        """
        filtered = []
        rejected = []

        for lead in leads:
            reason = self._check_lead(lead)
            if reason:
                rejected.append({
                    **lead,
                    "rejection_reason": reason
                })
            else:
                filtered.append(lead)

        logger.info(f"Filtered {len(filtered)} leads, rejected {len(rejected)}")
        return filtered, rejected

    def _check_lead(self, lead: Dict) -> str:
        """
        Check if lead meets criteria

        Returns:
            Empty string if passes, rejection reason if fails
        """
        validation_error = (lead.get("_validation_error") or "").strip()
        if validation_error:
            return validation_error

        # Check opportunity score
        score = lead.get("opportunity_score")
        if score is None or score < self.min_opportunity_score:
            return f"Opportunity score too low: {score}"

        quality = lead.get("site_quality_score")
        if quality is not None and quality < self.min_site_quality_score:
            return f"Weak site quality: {quality}"

        return ""  # Passes all checks

    def validate_before_analysis(self, lead: Dict) -> str:
        """Apply strict validation before site analysis runs."""
        website = (lead.get("website") or "").strip()
        if settings.REQUIRE_WEBSITE and not website:
            return "no website"
        if website and not self._is_usable_website(website):
            return "low_quality_website"
        return ""

    def validate_after_contact_extraction(self, lead: Dict) -> str:
        """Apply strict validation after contact extraction but before deeper analysis."""
        website = (lead.get("website") or "").strip()
        extraction = lead.get("contact_extraction") or {}
        fallback_reason = (extraction.get("fallback_reason") or "").strip()

        if website and fallback_reason in {"page_fetch_failed", "empty_page", "unexpected_extraction_error"}:
            return "low_quality_website"
        if settings.REQUIRE_CONTACT and not lead.get("email") and not lead.get("phone"):
            return "no contact method"
        return ""

    def _is_usable_website(self, website: str) -> bool:
        """Reject malformed, directory-like and placeholder domains."""
        normalized = website if website.startswith(("http://", "https://")) else f"https://{website}"
        parsed = urlparse(normalized)
        hostname = parsed.netloc.lower().lstrip("www.")
        if not parsed.scheme or not parsed.netloc:
            return False
        if hostname in self.placeholder_domains:
            return False
        if any(token in hostname for token in ["example", "placeholder", "invalid"]):
            return False
        if should_skip_domain(hostname):
            return False
        return True
