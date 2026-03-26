"""
Contact strategy service.
"""
from __future__ import annotations

from typing import Dict


class ContactStrategy:
    """Determine the current email-only strategy and keep legacy fallback fields empty."""

    def determine_strategy(self, prospect: Dict) -> str:
        if prospect.get("email"):
            return "email"
        return "unavailable"

    def preferred_social_channel(self, prospect: Dict) -> str:
        if prospect.get("instagram_url"):
            return "instagram"
        if prospect.get("facebook_url"):
            return "facebook"
        if prospect.get("linkedin_url"):
            return "linkedin"
        return ""

    def generate_messages(self, prospect: Dict) -> Dict[str, object]:
        strategy = self.determine_strategy(prospect)
        social_channel = self.preferred_social_channel(prospect)
        return {
            "recommended_channel": strategy,
            "contact_strategy": strategy,
            "preferred_social_channel": social_channel,
            "recommended_cta": self._recommended_cta(strategy),
            "email_unavailable_reason": prospect.get("contact_extraction", {}).get("email_unavailable_reason", ""),
            "email": self._preferred_email(prospect),
            "short_email": self._preferred_short_email(prospect),
            "follow_up_day_2": self._preferred_follow_up(prospect, "day_2"),
            "follow_up_day_5": self._preferred_follow_up(prospect, "day_5"),
            "follow_up_day_10": self._preferred_follow_up(prospect, "day_10"),
            "follow_up_sequence_fr": prospect.get("follow_ups_fr", {}),
            "follow_up_sequence_en": prospect.get("follow_ups_en", {}),
            "sms": "",
            "sms_message": "",
            "call_script": "",
            "contact_form_message": "",
            "contact_form_message_medium": "",
            "social_dm_message": "",
            "instagram_message": "",
            "facebook_message": "",
            "contact_form_url": prospect.get("contact_form_url", ""),
            "contact_form_detected": bool(prospect.get("contact_form_url") or prospect.get("contact_form_detected")),
            "instagram_url": prospect.get("instagram_url", ""),
            "facebook_url": prospect.get("facebook_url", ""),
            "linkedin_url": prospect.get("linkedin_url", ""),
            "whatsapp_url": prospect.get("whatsapp_url", ""),
        }

    def _preferred_email(self, prospect: Dict) -> str:
        return prospect.get("email_body_en") if prospect.get("email_language") == "en" else prospect.get("email_body_fr")

    def _preferred_short_email(self, prospect: Dict) -> Dict[str, str]:
        if prospect.get("email_language") == "en":
            return {"subject": prospect.get("email_short_subject_en", ""), "body": prospect.get("email_short_en", "")}
        return {"subject": prospect.get("email_short_subject_fr", ""), "body": prospect.get("email_short_fr", "")}

    def _preferred_follow_up(self, prospect: Dict, step: str) -> Dict[str, str]:
        sequence = prospect.get("follow_ups_en", {}) if prospect.get("email_language") == "en" else prospect.get("follow_ups_fr", {})
        return sequence.get(step, {})

    def _recommended_cta(self, strategy: str) -> str:
        if strategy == "email":
            return "Repondez a l'email pour recevoir les 3 priorites."
        return "Lead ignore tant qu'aucun email exploitable n'est disponible."
