"""
Contact strategy service.
"""
from __future__ import annotations

from typing import Dict

from app.core.branding import get_business_identity, get_text_signature
from app.core.country_config import format_price_range


class ContactStrategy:
    """Determine optimal contact methods and generate localized fallback messages."""

    def determine_strategy(self, prospect: Dict) -> str:
        if prospect.get("email"):
            return "email"
        if prospect.get("phone"):
            return "phone"
        if prospect.get("contact_form_url") or prospect.get("contact_form_detected"):
            return "contact_form"
        if prospect.get("instagram_url"):
            return "instagram"
        if prospect.get("facebook_url"):
            return "facebook"
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
        language = prospect.get("email_language", "fr")
        strategy = self.determine_strategy(prospect)
        social_channel = self.preferred_social_channel(prospect)
        sms_message = self._generate_sms(prospect, language)
        call_script = self._generate_call_script(prospect, language)
        contact_form_message = self._generate_contact_form_message(prospect, language)
        social_dm_message = self._generate_social_dm_message(prospect, language, social_channel)
        return {
            "recommended_channel": strategy,
            "contact_strategy": "phone" if strategy == "phone" else strategy,
            "preferred_social_channel": social_channel,
            "recommended_cta": self._recommended_cta(strategy, language),
            "email_unavailable_reason": prospect.get("contact_extraction", {}).get("email_unavailable_reason", ""),
            "email": self._preferred_email(prospect),
            "short_email": self._preferred_short_email(prospect),
            "follow_up_day_2": self._preferred_follow_up(prospect, "day_2"),
            "follow_up_day_5": self._preferred_follow_up(prospect, "day_5"),
            "follow_up_day_10": self._preferred_follow_up(prospect, "day_10"),
            "follow_up_sequence_fr": prospect.get("follow_ups_fr", {}),
            "follow_up_sequence_en": prospect.get("follow_ups_en", {}),
            "sms": sms_message,
            "sms_message": sms_message,
            "call_script": call_script,
            "contact_form_message": contact_form_message,
            "contact_form_message_medium": self._generate_contact_form_message(prospect, language, medium=True),
            "social_dm_message": social_dm_message,
            "instagram_message": social_dm_message if social_channel == "instagram" else "",
            "facebook_message": social_dm_message if social_channel == "facebook" else "",
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

    def _generate_sms(self, prospect: Dict, language: str) -> str:
        identity = get_business_identity()
        business_name = prospect.get("business_name", "")
        mockup_url = prospect.get("mockup_url")
        hook = self._category_hook(prospect.get("category", ""), language)
        if language == "en":
            message = f"Hi {business_name}, {identity.sender_name} from {identity.business_name}. I reviewed your site and think {hook}. "
            if mockup_url:
                message += f"Preview: {mockup_url} "
            return message + "If useful, reply YES and I will send the 3 priority improvements."
        message = f"Bonjour {business_name}, ici {identity.sender_name} de {identity.business_name}. J'ai regarde votre site et je pense que {hook}. "
        if mockup_url:
            message += f"Apercu: {mockup_url} "
        return message + "Si cela vous interesse, repondez OUI et je vous envoie les 3 priorites."

    def _generate_call_script(self, prospect: Dict, language: str) -> str:
        identity = get_business_identity()
        business_name = prospect.get("business_name", "")
        price_range = format_price_range(prospect.get("estimated_price_min"), prospect.get("estimated_price_max"), prospect.get("country"))
        pitch = self._category_pitch(prospect.get("category", ""), language)
        mockup_url = prospect.get("mockup_url")
        if language == "en":
            mockup_line = f"I also prepared a live mockup I can send after the call: {mockup_url}" if mockup_url else "I can also send a live mockup after the call."
            return f"Hello, this is {identity.sender_name} from {identity.business_name}, calling for {business_name}.\n\nI reviewed your current website and my impression is that {pitch}.\n\nWould you have 2 minutes now, or should I send the short version by email?\n\n{mockup_line}\nProjects like this usually sit around {price_range}."
        mockup_line = f"J'ai aussi prepare une maquette en ligne que je peux vous envoyer apres l'appel : {mockup_url}" if mockup_url else "Je peux aussi vous envoyer une maquette en ligne juste apres l'appel."
        return f"Bonjour, ici {identity.sender_name} de {identity.business_name}, je contacte {business_name}.\n\nJ'ai regarde votre site actuel et mon impression est que {pitch}.\n\nVous avez 2 minutes maintenant, ou je vous envoie directement la version courte ?\n\n{mockup_line}\nSur ce type de projet, on se situe generalement autour de {price_range}."

    def _generate_contact_form_message(self, prospect: Dict, language: str, medium: bool = False) -> str:
        identity = get_business_identity()
        business_name = prospect.get("business_name", "")
        mockup_url = prospect.get("mockup_url")
        if language == "en":
            lines = [f"Hello {business_name},", "", f"I am {identity.sender_display_name}. I reviewed your site and believe a more premium, more conversion-focused version could improve enquiries."]
            if mockup_url:
                lines.append(f"Live mockup: {mockup_url}")
            if medium:
                lines.append("If useful, I can send the 3 improvements I would prioritise first.")
            else:
                lines.append("If useful, reply YES and I will send the short version.")
            return "\n".join(lines)
        lines = [f"Bonjour {business_name},", "", f"Je suis {identity.sender_display_name}. J'ai regarde votre site et je pense qu'une version plus premium et plus orientee conversion pourrait ameliorer les demandes entrantes."]
        if mockup_url:
            lines.append(f"Maquette en ligne : {mockup_url}")
        if medium:
            lines.append("Si utile, je peux vous envoyer les 3 ameliorations que je prioriserais.")
        else:
            lines.append("Si cela vous interesse, repondez OUI et je vous envoie la version courte.")
        return "\n".join(lines)

    def _generate_social_dm_message(self, prospect: Dict, language: str, channel: str) -> str:
        identity = get_business_identity()
        business_name = prospect.get("business_name", "")
        mockup_url = prospect.get("mockup_url")
        channel_label = channel or "social"
        if language == "en":
            message = f"Hi {business_name}, {identity.sender_name} here from {identity.business_name}. I prepared a more premium and conversion-focused website direction for your business."
            if mockup_url:
                message += f" Preview: {mockup_url}"
            return message + f" If useful, reply here on {channel_label} and I will send the short version."
        message = f"Bonjour {business_name}, ici {identity.sender_name} de {identity.business_name}. J'ai prepare une direction de site plus premium et plus orientee conversion pour votre activite."
        if mockup_url:
            message += f" Apercu: {mockup_url}"
        return message + f" Si cela vous interesse, repondez ici sur {channel_label} et je vous envoie la version courte."

    def _recommended_cta(self, strategy: str, language: str) -> str:
        fr = {
            "email": "Repondez a l'email pour recevoir les 3 priorites.",
            "phone": "Envoyer le SMS puis appeler si reponse positive.",
            "contact_form": "Coller le message court dans le formulaire et demander la bonne personne.",
            "instagram": "Envoyer le DM puis proposer l'aperçu ou la version courte.",
            "facebook": "Envoyer le message privé puis proposer l'aperçu ou la version courte.",
            "unavailable": "Passage manuel requis.",
        }
        en = {
            "email": "Reply to the email to receive the 3 priority improvements.",
            "phone": "Send the SMS first, then call if the reply is positive.",
            "contact_form": "Paste the short message into the form and ask for the right contact.",
            "instagram": "Send the DM, then offer the preview or short version.",
            "facebook": "Send the private message, then offer the preview or short version.",
            "unavailable": "Manual research required.",
        }
        return (en if language == "en" else fr).get(strategy, (en if language == "en" else fr)["unavailable"])

    def _category_hook(self, category: str, language: str) -> str:
        normalized = (category or "").lower()
        if any(term in normalized for term in ["plomb", "plumb", "elect", "electric", "chauffag"]):
            return "the site could capture more quote requests quickly" if language == "en" else "le site pourrait capter plus de devis rapidement"
        if any(term in normalized for term in ["coiff", "hair", "salon", "barber", "beauty"]):
            return "the real quality of the salon is not yet fully reflected online" if language == "en" else "le niveau reel du salon n'est pas encore pleinement ressenti en ligne"
        if any(term in normalized for term in ["spa", "wellness", "institut", "massage"]):
            return "the calm and premium quality of the treatments could come through much better online" if language == "en" else "le calme et la qualite percue des soins pourraient mieux ressortir en ligne"
        return "the site could gain a lot in clarity and credibility" if language == "en" else "le site pourrait gagner en clarte et en credibilite"

    def _category_pitch(self, category: str, language: str) -> str:
        normalized = (category or "").lower()
        if any(term in normalized for term in ["plomb", "plumb", "elect", "electric", "chauffag"]):
            return "the site could do a better job reassuring visitors and converting urgent enquiries" if language == "en" else "le site pourrait mieux rassurer et convertir les demandes urgentes"
        if any(term in normalized for term in ["coiff", "hair", "salon", "barber", "beauty"]):
            return "the real quality of the salon is not yet being reflected strongly enough online" if language == "en" else "la qualite reelle du salon n'est pas encore assez bien valorisee en ligne"
        if any(term in normalized for term in ["spa", "wellness", "institut", "massage"]):
            return "the brand could feel more premium and more reassuring from the first scroll" if language == "en" else "la marque pourrait paraitre plus premium et plus rassurante des le premier scroll"
        return "the site could build more trust and generate more enquiries" if language == "en" else "le site pourrait inspirer davantage de confiance et generer plus de prises de contact"
