"""
Deduplication service
"""
import re
import unicodedata
from typing import Dict, List
from urllib.parse import urlparse


class Deduplicator:
    """Handle lead deduplication."""

    def deduplicate_leads(self, leads: List[Dict]) -> List[Dict]:
        """Remove exact and near duplicates from a lead list."""
        seen = set()
        unique_leads = []

        for lead in leads:
            if self._is_duplicate(lead, seen):
                continue

            seen.add(self._create_key(lead))
            unique_leads.append(lead)

        return unique_leads

    def _is_duplicate(self, lead: Dict, seen: set[str]) -> bool:
        """Check exact and near-duplicate matches."""
        key = self._create_key(lead)
        if key in seen:
            return True

        normalized_name = self._normalize_text(lead.get("business_name", ""))
        location = self._normalize_text(lead.get("location", ""))
        website = self._normalize_domain(lead.get("website", ""))
        phone = self._normalize_phone(lead.get("phone", ""))

        for existing_key in seen:
            existing_name, existing_website, existing_phone, existing_location = existing_key.split("|", 3)

            if website and existing_website and website == existing_website:
                return True

            if phone and existing_phone and phone == existing_phone:
                return True

            if location and location == existing_location:
                if normalized_name == existing_name:
                    return True
                if normalized_name and existing_name:
                    if normalized_name in existing_name or existing_name in normalized_name:
                        return True

        return False

    def _create_key(self, lead: Dict) -> str:
        """Create a normalized deduplication key."""
        name = self._normalize_text(lead.get("business_name", ""))
        website = self._normalize_domain(lead.get("website", ""))
        phone = self._normalize_phone(lead.get("phone", ""))
        location = self._normalize_text(lead.get("location", ""))
        return "|".join([name, website, phone, location])

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        if not text:
            return ""

        text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()
        text = re.sub(r"\b(le|la|les|du|de|des|et|a|un|une)\b", "", text)
        text = re.sub(r"[^\w\s]", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _normalize_domain(self, url: str) -> str:
        """Extract and normalize domain."""
        if not url:
            return ""

        try:
            domain = urlparse(url).netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except Exception:
            return ""

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number."""
        if not phone:
            return ""

        digits = re.sub(r"\D", "", phone)

        if digits.startswith("33") and len(digits) > 10:
            digits = digits[2:]
        elif digits.startswith("0") and len(digits) == 10:
            digits = digits[1:]

        return digits
