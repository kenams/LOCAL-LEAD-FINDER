"""
Lead filtering service
Filters prospects based on business potential criteria
"""
from typing import List, Dict, Tuple
from app.core.logging import logger

class LeadFilter:
    """Filters leads to keep only high-potential prospects"""

    def __init__(self):
        self.min_opportunity_score = 70
        self.max_site_quality_score = 70  # Exclude modern sites

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
        # Check opportunity score
        score = lead.get("opportunity_score")
        if score is None or score < self.min_opportunity_score:
            return f"Opportunity score too low: {score}"

        # Check contact info
        phone = lead.get("phone")
        email = lead.get("email")
        if not phone and not email:
            return "No phone or email contact"

        # Missing website can still be a strong lead if direct contact exists.
        website = lead.get("website")
        if not website or not website.strip():
            return ""

        # Check site quality (exclude modern sites)
        quality = lead.get("site_quality_score")
        if quality is not None and quality > self.max_site_quality_score:
            return f"Site too modern: quality score {quality}"

        return ""  # Passes all checks
