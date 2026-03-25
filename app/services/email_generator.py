"""
Email generation service.
"""
from __future__ import annotations

from html import escape
from typing import Dict, List

from app.core.branding import get_business_identity, get_html_signature, get_text_signature
from app.core.country_config import format_price, get_country_profile
from app.core.logging import logger


class EmailGenerator:
    """Generate premium localized outreach packs."""

    def generate_email(self, prospect: Dict, language: str = "fr") -> Dict[str, object]:
        """Generate a full outreach email pack for one language."""
        try:
            resolved_language = prospect.get("email_language") or language
            return self._build_pack(prospect, "fr" if resolved_language == "fr" else "en")
        except Exception as exc:
            logger.error(f"Email generation failed: {exc}")
            signature = get_text_signature(language)
            return {
                "subject": "Une version plus claire pour attirer plus de clients" if language == "fr" else "A clearer page to attract more clients",
                "short_subject": "Landing page claire" if language == "fr" else "Clear landing page",
                "body": signature,
                "short_body": signature,
                "long_body": signature,
                "html_body": f"<pre>{escape(signature)}</pre>",
                "follow_ups": {},
                "selected_offer_type": "landing_page",
            }

    def _build_pack(self, prospect: Dict, language: str) -> Dict[str, object]:
        country = prospect.get("country")
        selected_offer_type = prospect.get("selected_offer_type") or self._select_offer_type(prospect)
        offer_copy = self._get_offer_copy(prospect, selected_offer_type, language, country)
        offer_copy = self._tune_offer_copy_for_site_band(offer_copy, prospect, language, selected_offer_type)
        greeting = "Bonjour," if language == "fr" else "Hello,"
        signature_text = get_text_signature(language)
        signature_html = get_html_signature(language)
        issues_lines = self._get_issue_lines(prospect, language)
        issue_sentence = self._render_issue_sentence(issues_lines, language)

        body_lines = [
            greeting,
            "",
            offer_copy["intro"],
            "",
            offer_copy["problem"],
            issue_sentence,
            "",
            offer_copy["headline"],
            f"-> {offer_copy['feature_1']}",
            f"-> {offer_copy['feature_2']}",
            f"-> {offer_copy['feature_3']}",
            "",
            offer_copy["delivery"],
            offer_copy["price"],
            "",
            offer_copy["cta"],
            "",
            signature_text,
        ]
        text_body = "\n".join(line for line in body_lines if line is not None)
        html_body = self._render_html_email(
            language=language,
            subject=offer_copy["subject"],
            greeting=greeting,
            intro=escape(offer_copy["intro"]),
            paragraphs=[
                escape(offer_copy["problem"]),
                escape(issue_sentence) if issue_sentence else "",
                (
                    f"<div><div style=\"font-weight:700; margin-bottom:8px;\">{escape(offer_copy['headline'])}</div>"
                    f"<ul style=\"margin:0; padding-left:18px; color:#EDE7DB;\">"
                    f"<li style=\"margin:0 0 6px 0;\">{escape(offer_copy['feature_1'])}</li>"
                    f"<li style=\"margin:0 0 6px 0;\">{escape(offer_copy['feature_2'])}</li>"
                    f"<li style=\"margin:0 0 6px 0;\">{escape(offer_copy['feature_3'])}</li>"
                    f"</ul></div>"
                ),
                f"{escape(offer_copy['delivery'])} {escape(offer_copy['price'])}",
                escape(offer_copy["cta"]),
            ],
            signature_html=signature_html,
        )

        return {
            "subject": offer_copy["subject"],
            "short_subject": offer_copy["short_subject"],
            "body": text_body,
            "short_body": text_body,
            "long_body": text_body,
            "html_body": html_body,
            "follow_ups": self._build_offer_follow_ups(prospect, language, selected_offer_type),
            "selected_offer_type": selected_offer_type,
        }

    def _select_offer_type(self, prospect: Dict) -> str:
        page_count = int(prospect.get("website_page_count") or 0)
        new_business_score = float(prospect.get("new_business_score") or 0)
        target_type = prospect.get("target_type") or ""
        if target_type == "early_stage_business" or page_count <= 3 or new_business_score >= 65:
            return "landing_page"
        return "website"

    def _get_offer_copy(self, prospect: Dict, offer_type: str, language: str, country: str | None) -> Dict[str, str]:
        currency = get_country_profile(country).currency or "EUR"
        business_name = prospect.get("business_name", "")
        niche = self._get_niche_segment(prospect.get("category", ""))
        strong_site = self._is_already_strong_site(prospect)
        angle = self._get_offer_angle(niche, offer_type, language, strong_site=strong_site)
        landing_price_fr = f"C'est generalement autour de 300 {currency}, selon le besoin."
        website_price_fr = f"C'est souvent entre 500 {currency} et 700 {currency}, selon les besoins."
        landing_price_en = f"This is usually around 300 {currency}, depending on what is needed."
        website_price_en = f"This is often between 500 {currency} and 700 {currency}, depending on the scope."

        if offer_type == "landing_page":
            if language == "fr":
                return {
                    "subject": angle["subject"],
                    "short_subject": angle["short_subject"],
                    "intro": f"Je suis tombe sur {business_name} en cherchant des services comme les votres.",
                    "problem": angle["problem"],
                    "headline": angle.get("headline", "Je propose des landing pages modernes :"),
                    "feature_1": angle["feature_1"],
                    "feature_2": angle["feature_2"],
                    "feature_3": angle["feature_3"],
                    "delivery": "Livraison en general sous 3 a 5 jours.",
                    "price": landing_price_fr,
                    "cta": "Si vous voulez, je peux vous envoyer une proposition tres simple adaptee a votre activite.",
                }
            return {
                "subject": angle["subject"],
                "short_subject": angle["short_subject"],
                "intro": f"I came across {business_name} while looking for businesses like yours.",
                "problem": angle["problem"],
                "headline": angle.get("headline", "I build modern landing pages:"),
                "feature_1": angle["feature_1"],
                "feature_2": angle["feature_2"],
                "feature_3": angle["feature_3"],
                "delivery": "Delivery is usually within 3 to 5 days.",
                "price": landing_price_en,
                "cta": "If useful, I can send a very simple version adapted to your business.",
            }

        if language == "fr":
            return {
                "subject": angle["subject"],
                "short_subject": angle["short_subject"],
                "intro": f"Je suis tombe sur {business_name} en cherchant des services comme les votres.",
                "problem": angle["problem"],
                "headline": angle.get("headline", "Je propose des sites vitrines simples et modernes :"),
                "feature_1": angle["feature_1"],
                "feature_2": angle["feature_2"],
                "feature_3": angle["feature_3"],
                "delivery": "Livraison en general sous 5 a 7 jours.",
                "price": website_price_fr,
                "cta": "Si vous voulez, je peux vous envoyer une proposition courte adaptee a votre activite.",
            }
        return {
            "subject": angle["subject"],
            "short_subject": angle["short_subject"],
            "intro": f"I came across {business_name} while looking for businesses like yours.",
            "problem": angle["problem"],
            "headline": angle.get("headline", "I build simple modern showcase websites:"),
            "feature_1": angle["feature_1"],
            "feature_2": angle["feature_2"],
            "feature_3": angle["feature_3"],
            "delivery": "Delivery is usually within 5 to 7 days.",
            "price": website_price_en,
            "cta": "If useful, I can send a short proposal adapted to your business.",
        }

    def _is_already_strong_site(self, prospect: Dict) -> bool:
        site_quality_score = float(prospect.get("site_quality_score") or 0)
        page_count = int(prospect.get("website_page_count") or 0)
        has_modern_ui = bool(prospect.get("has_modern_ui"))
        has_seo_foundation = bool(prospect.get("has_seo_foundation"))
        return site_quality_score >= 75 or (page_count >= 4 and has_modern_ui and has_seo_foundation)

    def _get_niche_segment(self, category: str) -> str:
        normalized = (category or "").lower()
        if any(term in normalized for term in ["coiff", "hair", "salon", "barber", "beauty"]):
            return "beauty"
        if any(term in normalized for term in ["spa", "wellness", "institut", "massage"]):
            return "wellness"
        if any(term in normalized for term in ["plomb", "plumb", "elect", "electric", "chauffag", "trade"]):
            return "trade"
        return "professional"

    def _get_offer_angle(self, niche: str, offer_type: str, language: str, *, strong_site: bool = False) -> Dict[str, str]:
        if strong_site and offer_type == "website":
            if language == "fr":
                return {
                    "subject": "Une version plus ciblée pour mieux convertir",
                    "short_subject": "Optimisation conversion",
                    "problem": "Votre site donne deja une bonne image. Je vois surtout une opportunite d'aller plus loin sur la conversion avec des pages plus ciblees, plus de preuve et un contact plus direct.",
                    "headline": "Je proposerais plutot ce type d'optimisation :",
                    "feature_1": "pages par offre ou service plus ciblees",
                    "feature_2": "preuves et cas clients plus visibles",
                    "feature_3": "parcours de contact plus direct",
                }
            return {
                "subject": "A more targeted version to convert better",
                "short_subject": "Conversion optimization",
                "problem": "Your website already gives a solid impression. The main opportunity I see is to push conversion further with more targeted pages, stronger proof and a more direct contact path.",
                "headline": "I would focus on this kind of optimization:",
                "feature_1": "more targeted pages by offer or service",
                "feature_2": "more visible proof and case studies",
                "feature_3": "more direct enquiry path",
            }
        if language == "fr":
            angles = {
                "landing_page": {
                    "professional": {
                        "subject": "Une page plus claire pour attirer plus de clients",
                        "short_subject": "Landing page plus claire",
                        "problem": "Je pense qu'il y a une opportunite simple d'ameliorer la conversion avec une page plus claire et orientee clients.",
                        "feature_1": "message clair des le premier ecran",
                        "feature_2": "preuve et credibilite mieux mises en avant",
                        "feature_3": "formulaire de contact plus direct",
                    },
                    "trade": {
                        "subject": "Une page plus directe pour generer plus de devis",
                        "short_subject": "Landing page devis",
                        "problem": "Sur ce type d'activite, beaucoup de demandes se jouent sur une page simple, claire et mobile.",
                        "feature_1": "offre et zones d'intervention visibles tout de suite",
                        "feature_2": "elements de confiance plus rassurants",
                        "feature_3": "demande de devis plus rapide",
                    },
                    "beauty": {
                        "subject": "Une page plus claire pour generer plus de rendez-vous",
                        "short_subject": "Landing page rendez-vous",
                        "problem": "Je pense qu'une page plus simple et plus desirables pourrait mieux convertir vos visiteurs en prises de rendez-vous.",
                        "feature_1": "presentation plus nette des prestations",
                        "feature_2": "design mobile plus desirables",
                        "feature_3": "prise de contact ou rendez-vous plus directe",
                    },
                    "wellness": {
                        "subject": "Une page plus rassurante pour attirer plus de demandes",
                        "short_subject": "Landing page plus rassurante",
                        "problem": "Je pense qu'une page plus calme, plus claire et plus rassurante pourrait mieux transformer vos visiteurs en demandes reelles.",
                        "feature_1": "presentation plus apaisante des soins",
                        "feature_2": "message plus clair sur les benefices",
                        "feature_3": "prise de contact plus fluide",
                    },
                },
                "website": {
                    "professional": {
                        "subject": "Une version plus pro et plus efficace de votre site",
                        "short_subject": "Site vitrine plus pro",
                        "problem": "En regardant votre site, je pense qu'il serait possible de le rendre plus clair et plus efficace pour convertir vos visiteurs.",
                        "feature_1": "structure claire",
                        "feature_2": "design mobile",
                        "feature_3": "base SEO propre",
                    },
                    "trade": {
                        "subject": "Un site plus clair pour generer plus de devis",
                        "short_subject": "Site vitrine devis",
                        "problem": "Je pense qu'un site vitrine plus simple et plus rassurant pourrait mieux capter les demandes de devis.",
                        "feature_1": "services plus lisibles",
                        "feature_2": "preuves de confiance mieux visibles",
                        "feature_3": "contact plus direct sur mobile",
                    },
                    "beauty": {
                        "subject": "Une version plus premium et plus efficace de votre site",
                        "short_subject": "Site vitrine plus premium",
                        "problem": "Je pense qu'un site vitrine plus propre et plus desirables pourrait mieux valoriser votre image et vos prestations.",
                        "feature_1": "univers visuel plus premium",
                        "feature_2": "prestations mieux presentees",
                        "feature_3": "parcours mobile plus fluide",
                    },
                    "wellness": {
                        "subject": "Une version plus rassurante et plus fluide de votre site",
                        "short_subject": "Site vitrine plus fluide",
                        "problem": "Je pense qu'un site vitrine plus calme et plus clair pourrait mieux inspirer confiance et faciliter la prise de contact.",
                        "feature_1": "structure plus apaisante",
                        "feature_2": "contenu plus clair sur les soins",
                        "feature_3": "base SEO simple et propre",
                    },
                },
            }
        else:
            angles = {
                "landing_page": {
                    "professional": {
                        "subject": "A clearer page to attract more clients",
                        "short_subject": "Clearer landing page",
                        "problem": "I believe there is a simple opportunity to improve conversion with a clearer, more client-focused page.",
                        "feature_1": "clear message from the first screen",
                        "feature_2": "stronger proof and credibility",
                        "feature_3": "more direct contact form",
                    },
                    "trade": {
                        "subject": "A more direct page to generate more quote requests",
                        "short_subject": "Quote-focused landing page",
                        "problem": "In this kind of business, many enquiries are won or lost on a simple, clear mobile page.",
                        "feature_1": "clear offer and service area from the start",
                        "feature_2": "stronger trust elements",
                        "feature_3": "faster quote request flow",
                    },
                    "beauty": {
                        "subject": "A clearer page to bring in more bookings",
                        "short_subject": "Booking landing page",
                        "problem": "I believe a simpler and more desirable page could convert more visitors into bookings.",
                        "feature_1": "clearer service presentation",
                        "feature_2": "more attractive mobile design",
                        "feature_3": "more direct booking or contact flow",
                    },
                    "wellness": {
                        "subject": "A more reassuring page to attract more enquiries",
                        "short_subject": "More reassuring landing page",
                        "problem": "I believe a calmer, clearer page could turn more visitors into real enquiries.",
                        "feature_1": "more reassuring treatment presentation",
                        "feature_2": "clearer value message",
                        "feature_3": "smoother contact flow",
                    },
                },
                "website": {
                    "professional": {
                        "subject": "A more professional and more effective version of your website",
                        "short_subject": "More effective website",
                        "problem": "Looking at your website, I believe it could be made clearer and more effective at converting visitors.",
                        "feature_1": "clear structure",
                        "feature_2": "mobile design",
                        "feature_3": "clean SEO basics",
                    },
                    "trade": {
                        "subject": "A clearer website to generate more quote requests",
                        "short_subject": "Quote-focused website",
                        "problem": "I believe a simpler, more reassuring showcase website could convert more quote enquiries.",
                        "feature_1": "clearer service structure",
                        "feature_2": "stronger trust signals",
                        "feature_3": "more direct mobile contact path",
                    },
                    "beauty": {
                        "subject": "A more premium and more effective version of your website",
                        "short_subject": "More premium website",
                        "problem": "I believe a cleaner and more desirable showcase website could better reflect your image and services.",
                        "feature_1": "more premium visual direction",
                        "feature_2": "stronger service presentation",
                        "feature_3": "smoother mobile experience",
                    },
                    "wellness": {
                        "subject": "A more reassuring and smoother version of your website",
                        "short_subject": "Smoother website",
                        "problem": "I believe a calmer, clearer website could build more trust and make contact easier.",
                        "feature_1": "more calming structure",
                        "feature_2": "clearer treatment content",
                        "feature_3": "simple clean SEO base",
                    },
                },
            }
        return angles[offer_type].get(niche, angles[offer_type]["professional"])

    def _render_issue_sentence(self, issues_lines: List[str], language: str) -> str:
        if not issues_lines:
            return ""
        joined = ", ".join(issues_lines[:2])
        if language == "fr":
            return f"Ce qui me fait penser cela: {joined}."
        return f"What made me think that: {joined}."

    def _get_site_band(self, prospect: Dict) -> str:
        """Group sites into simple quality bands for softer or stronger outreach angles."""
        if self._is_already_strong_site(prospect):
            return "strong"
        site_quality_score = float(prospect.get("site_quality_score") or 0)
        page_count = int(prospect.get("website_page_count") or 0)
        if site_quality_score >= 45 or page_count >= 4:
            return "medium"
        return "low"

    def _tune_offer_copy_for_site_band(
        self,
        offer_copy: Dict[str, str],
        prospect: Dict,
        language: str,
        offer_type: str,
    ) -> Dict[str, str]:
        """Adjust the message tone depending on whether the site is weak, average or already strong."""
        tuned = dict(offer_copy)
        site_band = self._get_site_band(prospect)

        if language == "fr":
            if site_band == "low" and offer_type == "website":
                tuned["subject"] = "Une version plus claire pour rassurer et convertir"
                tuned["problem"] = "Je pense qu'il y a une vraie opportunite de clarifier le site et de rendre la prise de contact plus evidente."
            elif site_band == "medium" and offer_type == "website":
                tuned["subject"] = "Une version plus claire pour mieux convertir"
                tuned["problem"] = "Le site a deja une bonne base. Je pense qu'il serait possible de le rendre plus lisible et plus oriente conversion."
            elif site_band == "medium" and offer_type == "landing_page":
                tuned["subject"] = "Une page plus directe pour convertir davantage"
                tuned["problem"] = "Je pense qu'une page plus directe et plus orientee action pourrait mieux transformer vos visiteurs en demandes."
            elif site_band == "strong" and offer_type == "website":
                tuned["subject"] = "Une version plus ciblee pour mieux convertir"
        else:
            if site_band == "low" and offer_type == "website":
                tuned["subject"] = "A clearer website to build trust and convert better"
                tuned["problem"] = "I believe there is a real opportunity to clarify the website and make the enquiry path much more obvious."
            elif site_band == "medium" and offer_type == "website":
                tuned["subject"] = "A clearer version to convert better"
                tuned["problem"] = "The website already has a decent base. I believe it could be made clearer and more conversion-focused."
            elif site_band == "medium" and offer_type == "landing_page":
                tuned["subject"] = "A more direct page to convert more visitors"
                tuned["problem"] = "I believe a more direct, action-focused page could turn more visitors into enquiries."
            elif site_band == "strong" and offer_type == "website":
                tuned["subject"] = "A more targeted version to convert better"

        return tuned

    def _build_offer_follow_ups(self, prospect: Dict, language: str, offer_type: str) -> Dict[str, Dict[str, str]]:
        business_name = prospect.get("business_name", "")
        signature = get_text_signature(language)
        strong_site = self._is_already_strong_site(prospect)
        if language == "fr":
            if strong_site and offer_type == "website":
                return {
                    "day_2": {"subject": f"Relance rapide pour {business_name}", "body": f"Bonjour,\n\nJe reviens vers vous concernant l'idee d'optimisation conversion pour {business_name}.\n\nJe pense surtout a des pages plus ciblees, plus de preuve visible et un parcours de contact plus direct.\n\nSi vous voulez, je peux vous envoyer une proposition courte.\n\n{signature}"},
                    "day_5": {"subject": f"Piste conversion pour {business_name}", "body": f"Bonjour,\n\nJe me permets une derniere relance concernant une version plus ciblee pour mieux convertir sur {business_name}.\n\nSi utile, je peux vous envoyer les 3 optimisations que je prioriserais en premier.\n\n{signature}"},
                    "day_10": {"subject": f"Dernier message pour {business_name}", "body": f"Bonjour,\n\nDernier message de ma part concernant l'optimisation conversion de votre site.\n\nSi vous voulez, je peux vous envoyer une proposition breve et concrete.\n\n{signature}"},
                }
            if offer_type == "landing_page":
                return {
                    "day_2": {"subject": f"Relance rapide pour {business_name}", "body": f"Bonjour,\n\nJe reviens vers vous concernant l'idee de landing page plus claire pour {business_name}.\n\nSi vous voulez, je peux vous proposer une version simple adaptee a votre activite.\n\n{signature}"},
                    "day_5": {"subject": f"Version simple pour {business_name}", "body": f"Bonjour,\n\nJe me permets une derniere relance concernant une landing page plus claire pour {business_name}.\n\nSi le sujet est utile, je peux vous envoyer une proposition courte.\n\n{signature}"},
                    "day_10": {"subject": f"Dernier message pour {business_name}", "body": f"Bonjour,\n\nDernier message de ma part concernant une landing page plus claire pour {business_name}.\n\nSi vous voulez, je peux vous proposer une version adaptee.\n\n{signature}"},
                }
            return {
                "day_2": {"subject": f"Relance rapide pour {business_name}", "body": f"Bonjour,\n\nJe reviens vers vous concernant l'idee de site vitrine plus clair pour {business_name}.\n\nSi vous voulez, je peux vous proposer une version adaptee a votre activite.\n\n{signature}"},
                "day_5": {"subject": f"Version plus claire pour {business_name}", "body": f"Bonjour,\n\nJe me permets une derniere relance concernant un site vitrine plus simple et plus efficace pour {business_name}.\n\nSi utile, je peux vous envoyer une proposition courte.\n\n{signature}"},
                "day_10": {"subject": f"Dernier message pour {business_name}", "body": f"Bonjour,\n\nDernier message de ma part concernant votre site vitrine.\n\nSi vous voulez, je peux vous proposer une version adaptee.\n\n{signature}"},
            }

        if strong_site and offer_type == "website":
            return {
                "day_2": {"subject": f"Quick follow-up for {business_name}", "body": f"Hello,\n\nFollowing up on the conversion optimization idea for {business_name}.\n\nI mainly mean more targeted pages, more visible proof and a more direct enquiry path.\n\nIf useful, I can send a short proposal.\n\n{signature}"},
                "day_5": {"subject": f"Conversion angle for {business_name}", "body": f"Hello,\n\nOne last follow-up about a more targeted version of the site for {business_name}.\n\nIf useful, I can send the 3 optimizations I would prioritize first.\n\n{signature}"},
                "day_10": {"subject": f"Final message for {business_name}", "body": f"Hello,\n\nFinal message from me about conversion optimization for your website.\n\nIf useful, I can send a brief and concrete proposal.\n\n{signature}"},
            }
        if offer_type == "landing_page":
            return {
                "day_2": {"subject": f"Quick follow-up for {business_name}", "body": f"Hello,\n\nFollowing up on the landing page idea for {business_name}.\n\nIf useful, I can suggest a simple version adapted to your business.\n\n{signature}"},
                "day_5": {"subject": f"Simple version for {business_name}", "body": f"Hello,\n\nOne last follow-up about a clearer landing page for {business_name}.\n\nIf useful, I can send a short proposal.\n\n{signature}"},
                "day_10": {"subject": f"Final message for {business_name}", "body": f"Hello,\n\nFinal message from me about a clearer landing page for {business_name}.\n\nIf useful, I can suggest a version adapted to your business.\n\n{signature}"},
            }
        return {
            "day_2": {"subject": f"Quick follow-up for {business_name}", "body": f"Hello,\n\nFollowing up on the website idea for {business_name}.\n\nIf useful, I can suggest a clearer version adapted to your business.\n\n{signature}"},
            "day_5": {"subject": f"Clearer website for {business_name}", "body": f"Hello,\n\nOne last follow-up about a simpler, more effective showcase website for {business_name}.\n\nIf useful, I can send a short proposal.\n\n{signature}"},
            "day_10": {"subject": f"Final message for {business_name}", "body": f"Hello,\n\nFinal message from me about your website.\n\nIf useful, I can suggest a version adapted to your business.\n\n{signature}"},
        }

    def _get_hook(self, prospect: Dict, category_data: Dict[str, str], language: str) -> str:
        """Return the best opening hook based on whether a website exists."""
        business_name = prospect.get("business_name", "")
        location = prospect.get("location", "")
        if prospect.get("website"):
            return category_data["hook"].format(business_name=business_name, location=location)
        if language == "fr":
            return f"En regardant {business_name} a {location}, je n'ai pas trouve de presence digitale suffisamment claire ou convaincante pour soutenir les prises de contact."
        return f"Looking at {business_name} in {location}, I could not find a digital presence that feels clear or strong enough to support enquiries properly."

    def _build_follow_ups(self, prospect: Dict, language: str, category_data: Dict[str, str]) -> Dict[str, Dict[str, str]]:
        business_name = prospect.get("business_name", "")
        mockup_url = prospect.get("mockup_url")
        signature = get_text_signature(language)

        if language == "fr":
            return {
                "day_2": {
                    "subject": f"Rebond rapide concernant {business_name}",
                    "body": "\n\n".join(
                        part for part in [
                            f"Bonjour, je reviens vers vous concernant l'idee de redesign preparee pour {business_name}.",
                            "Je pense sincerement qu'une version plus claire et plus premium pourrait faire une difference rapide sur la perception et les demandes entrantes.",
                            f"Maquette en ligne : {mockup_url}" if mockup_url else "",
                            "Si vous voulez, repondez simplement OUI et je vous envoie les 3 changements prioritaires.",
                            signature,
                        ] if part
                    ),
                },
                "day_5": {
                    "subject": f"3 points a corriger en priorite sur {business_name}",
                    "body": "\n\n".join(
                        part for part in [
                            f"Bonjour, mon dernier message concernant {business_name}.",
                            f"En regardant votre site, les 3 sujets qui me paraissent les plus impactants sont : {category_data['offer_1']}, {category_data['offer_2']} et {category_data['offer_3']}.",
                            "Si vous voulez, je peux vous envoyer une recommandation tres courte et concrete.",
                            signature,
                        ] if part
                    ),
                },
                "day_10": {
                    "subject": f"Dernier suivi pour {business_name}",
                    "body": "\n\n".join(
                        part for part in [
                            f"Bonjour, dernier message de ma part au sujet de {business_name}.",
                            "Je ferme le dossier ensuite, mais si vous souhaitez une version plus premium et plus efficace de votre site, je peux vous envoyer un plan simple a valider.",
                            "Si le sujet est d'actualite, un simple OUI suffit.",
                            signature,
                        ] if part
                    ),
                },
            }

        return {
            "day_2": {
                "subject": f"Quick follow-up for {business_name}",
                "body": "\n\n".join(
                    part for part in [
                        f"Hello, just following up on the redesign idea I prepared for {business_name}.",
                        "I genuinely believe a cleaner, more premium version could improve both credibility and enquiry conversion quite quickly.",
                        f"Live mockup: {mockup_url}" if mockup_url else "",
                        "If useful, reply with YES and I will send the 3 changes I would prioritise first.",
                        signature,
                    ] if part
                ),
            },
            "day_5": {
                "subject": f"3 priority improvements for {business_name}",
                "body": "\n\n".join(
                    part for part in [
                        f"Hello, one more follow-up regarding {business_name}.",
                        f"The 3 most important changes from my perspective would be {category_data['offer_1']}, {category_data['offer_2']} and {category_data['offer_3']}.",
                        "If useful, I can send a very concise recommendation.",
                        signature,
                    ] if part
                ),
            },
            "day_10": {
                "subject": f"Final follow-up for {business_name}",
                "body": "\n\n".join(
                    part for part in [
                        f"Hello, this is my final follow-up regarding {business_name}.",
                        "I will close the loop after this, but if a more premium and conversion-focused website is relevant, I can send a simple plan for review.",
                        "If it is worth exploring, just reply YES.",
                        signature,
                    ] if part
                ),
            },
        }

    def _get_category_data(self, category: str, language: str) -> Dict[str, str]:
        normalized = (category or "").lower()
        key = "professional"
        if any(term in normalized for term in ["plomb", "plumb", "elect", "electric", "chauffag", "trade"]):
            key = "trade"
        elif any(term in normalized for term in ["coiff", "hair", "salon", "barber", "beauty"]):
            key = "beauty"
        elif any(term in normalized for term in ["spa", "wellness", "institut", "massage"]):
            key = "wellness"

        if language == "fr":
            data = {
                "trade": {
                    "subject": "Une version plus rassurante pour {business_name}",
                    "short_subject": "Piste plus efficace pour {business_name}",
                    "hook": "En regardant {business_name} a {location}, j'ai eu l'impression que le site actuel ne convertissait pas encore aussi bien qu'il le pourrait, surtout pour les demandes urgentes.",
                    "pitch": "Pour un artisan ou une entreprise technique, les premieres secondes doivent inspirer confiance, clarifier les interventions et pousser au devis.",
                    "offer_1": "une CTA devis beaucoup plus visible",
                    "offer_2": "une presentation plus rassurante des services et garanties",
                    "offer_3": "une structure mobile plus directe pour les demandes urgentes",
                },
                "beauty": {
                    "subject": "Une piste plus premium pour {business_name}",
                    "short_subject": "Idee premium pour {business_name}",
                    "hook": "En regardant {business_name} a {location}, j'ai trouve que le niveau reel du salon n'etait pas encore pleinement ressenti en ligne.",
                    "pitch": "Pour ce type d'activite, l'image, la desirabilite et la fluidite de reservation comptent enormement dans la reponse client.",
                    "offer_1": "une image plus editoriale et plus premium",
                    "offer_2": "une mise en avant plus desirables des prestations",
                    "offer_3": "un parcours rendez-vous plus direct",
                },
                "wellness": {
                    "subject": "Une presence plus haut de gamme pour {business_name}",
                    "short_subject": "Piste bien-etre premium pour {business_name}",
                    "hook": "En regardant {business_name} a {location}, j'ai trouve que le calme, la confiance et la qualite percue des soins pouvaient etre mieux transmis en ligne.",
                    "pitch": "Pour un spa ou un institut, le site doit rassurer, apaiser et donner envie de reserver sans friction.",
                    "offer_1": "une atmosphere digitale plus premium",
                    "offer_2": "une mise en scene plus claire des soins",
                    "offer_3": "une reservation plus naturelle sur mobile",
                },
                "professional": {
                    "subject": "Une piste plus credible pour {business_name}",
                    "short_subject": "Idee de redesign pour {business_name}",
                    "hook": "En regardant {business_name} a {location}, j'ai eu l'impression que le site actuel pouvait gagner en clarte, en autorite et en credibilite.",
                    "pitch": "Pour les services professionnels, le site doit donner une impression nette, serieuse et executive des la premiere lecture.",
                    "offer_1": "une hierarchie plus claire des expertises",
                    "offer_2": "une image plus premium et plus credible",
                    "offer_3": "une prise de contact plus directe",
                },
            }
        else:
            data = {
                "trade": {
                    "subject": "A stronger quote-focused site for {business_name}",
                    "short_subject": "A quicker website win for {business_name}",
                    "hook": "Looking at {business_name} in {location}, my impression was that the current site is not converting as well as it could, especially for urgent enquiries.",
                    "pitch": "For a trade business, the first seconds should build trust, clarify services and move people to request a quote quickly.",
                    "offer_1": "a much clearer quote CTA",
                    "offer_2": "stronger trust and guarantee blocks",
                    "offer_3": "a more direct mobile path for urgent leads",
                },
                "beauty": {
                    "subject": "A more premium direction for {business_name}",
                    "short_subject": "Premium idea for {business_name}",
                    "hook": "Looking at {business_name} in {location}, my impression was that the real quality of the salon is not yet fully reflected online.",
                    "pitch": "For this category, image, desirability and booking flow have a major impact on response and conversion.",
                    "offer_1": "a more editorial and more premium look",
                    "offer_2": "a stronger service presentation",
                    "offer_3": "a more direct booking path",
                },
                "wellness": {
                    "subject": "A more premium online presence for {business_name}",
                    "short_subject": "Wellness redesign idea for {business_name}",
                    "hook": "Looking at {business_name} in {location}, I felt the calm, trust and perceived quality of the treatments could come through much better online.",
                    "pitch": "For a spa or wellness business, the website should reassure, slow the pace down and make booking feel natural.",
                    "offer_1": "a calmer premium atmosphere",
                    "offer_2": "clearer treatment storytelling",
                    "offer_3": "a smoother mobile booking flow",
                },
                "professional": {
                    "subject": "A more credible digital presence for {business_name}",
                    "short_subject": "Redesign idea for {business_name}",
                    "hook": "Looking at {business_name} in {location}, my impression was that the current site could gain a lot in clarity, authority and trust.",
                    "pitch": "For professional services, the website needs to feel clear, serious and executive from the first read.",
                    "offer_1": "clearer expertise hierarchy",
                    "offer_2": "more premium visual authority",
                    "offer_3": "a more direct enquiry path",
                },
            }

        return data[key]

    def _get_issue_lines(self, prospect: Dict, language: str) -> List[str]:
        raw_issues = prospect.get("detected_issues", [])
        if not raw_issues:
            return []

        translations = {
            "fr": {
                "no_cta": "peu d'appels a l'action visibles",
                "old_design": "une presentation visuelle datee",
                "no_booking": "une prise de rendez-vous peu evidente",
                "slow_mobile": "une experience mobile perfectible",
                "weak_trust": "des signaux de confiance a renforcer",
            },
            "en": {
                "no_cta": "limited call-to-action visibility",
                "old_design": "an outdated visual presentation",
                "no_booking": "an unclear booking path",
                "slow_mobile": "a mobile experience that could be stronger",
                "weak_trust": "trust signals that could be improved",
            },
        }
        localized = translations["fr" if language == "fr" else "en"]
        return [localized.get(issue, issue.replace("_", " ")) for issue in raw_issues[:3]]

    def _get_mockup_text(self, mockup_url: str | None, language: str) -> str:
        if not mockup_url:
            return ""
        if language == "fr":
            return f"J'ai aussi prepare une maquette en ligne pour illustrer la direction proposee : {mockup_url}"
        return f"I also prepared a live mockup to illustrate the proposed direction: {mockup_url}"

    def _get_mockup_html(self, mockup_url: str | None, language: str) -> str:
        if not mockup_url:
            return ""
        label = (
            "J'ai aussi prepare une maquette en ligne pour illustrer la direction proposee"
            if language == "fr"
            else "I also prepared a live mockup to illustrate the proposed direction"
        )
        return f'{escape(label)}: <a href="{escape(mockup_url)}" style="color:#D4AE72; text-decoration:none;">{escape(mockup_url)}</a>'

    def _get_market_sentence(self, messaging_style: str, language: str) -> str:
        if language == "fr":
            if messaging_style == "premium_polite":
                return "Je privilege une approche sobre, premium et orientee confiance."
            return "L'objectif est d'ameliorer rapidement la perception de marque et les prises de contact."
        if messaging_style == "friendly_professional":
            return "The tone stays polished, practical and easy to act on."
        return "The goal is to improve brand perception and response quality quickly."

    def _get_reply_cta(self, language: str) -> str:
        if language == "fr":
            return "Si cela vaut la peine d'etre regarde de votre cote, repondez simplement OUI et je vous envoie les 3 priorites que je traiterais en premier."
        return "If this looks worth exploring on your side, just reply YES and I will send the 3 priorities I would tackle first."

    def _render_issue_block(self, issues_lines: List[str], language: str) -> str:
        if not issues_lines:
            return ""
        heading = "J'ai notamment releve :" if language == "fr" else "The main points I noticed were:"
        return "\n".join([heading] + [f"- {issue}" for issue in issues_lines])

    def _render_issue_html(self, issues_lines: List[str], heading: str) -> str:
        if not issues_lines:
            return ""
        items = "".join(f'<li style="margin:0 0 6px 0;">{escape(issue)}</li>' for issue in issues_lines)
        return (
            f'<div><div style="font-weight:700; margin-bottom:8px;">{escape(heading)}</div>'
            f'<ul style="margin:0; padding-left:18px; color:#EDE7DB;">{items}</ul></div>'
        )

    def _render_html_email(
        self,
        language: str,
        subject: str,
        greeting: str,
        intro: str,
        paragraphs: List[str],
        signature_html: str,
    ) -> str:
        blocks = []
        for paragraph in paragraphs:
            if not paragraph:
                continue
            if paragraph.startswith("<div"):
                blocks.append(paragraph)
            else:
                blocks.append(f'<p style="margin:0 0 16px 0; color:#EDE7DB; line-height:1.75; font-size:15px;">{paragraph}</p>')

        preview_text = "Premium outreach prepared by KAH.DIGITAL." if language == "en" else "Outreach premium prepare par KAH.DIGITAL."
        return f"""
        <!DOCTYPE html>
        <html lang="{language}">
        <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            <title>{escape(subject)}</title>
        </head>
        <body style="margin:0; padding:24px 12px; background:#0C0E11; color:#F5EFE3;">
            <div style="display:none; max-height:0; overflow:hidden; opacity:0;">{escape(preview_text)}</div>
            <div style="max-width:680px; margin:0 auto; background:linear-gradient(180deg,#14171C 0%, #101317 100%); border:1px solid rgba(212,174,114,0.24); border-radius:22px; overflow:hidden; box-shadow:0 24px 64px rgba(0,0,0,0.28);">
                <div style="padding:26px 28px; background:linear-gradient(135deg, rgba(212,174,114,0.14), rgba(212,174,114,0.02)); border-bottom:1px solid rgba(212,174,114,0.16);">
                    <div style="font-size:11px; letter-spacing:0.18em; text-transform:uppercase; color:#D4AE72; font-family:Arial, sans-serif;">KAH.DIGITAL</div>
                    <div style="margin-top:10px; font-size:26px; line-height:1.15; font-weight:700; color:#F5EFE3; font-family:Arial, sans-serif;">{escape(subject)}</div>
                </div>
                <div style="padding:28px;">
                    <p style="margin:0 0 14px 0; color:#F5EFE3; line-height:1.75; font-size:15px;">{escape(greeting)}</p>
                    <p style="margin:0 0 16px 0; color:#EDE7DB; line-height:1.75; font-size:15px;">{intro}</p>
                    {"".join(blocks)}
                    {signature_html}
                </div>
            </div>
        </body>
        </html>
        """.strip()
