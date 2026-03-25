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
        identity = get_business_identity()
        country = prospect.get("country")
        selected_offer_type = prospect.get("selected_offer_type") or self._select_offer_type(prospect)
        offer_copy = self._get_offer_copy(selected_offer_type, language, country)
        greeting = "Bonjour," if language == "fr" else "Hello,"
        signature_text = get_text_signature(language)
        signature_html = get_html_signature(language)

        body_lines = [
            greeting,
            "",
            offer_copy["intro"],
            "",
            offer_copy["problem"],
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

    def _get_offer_copy(self, offer_type: str, language: str, country: str | None) -> Dict[str, str]:
        currency = get_country_profile(country).currency or "EUR"
        landing_price_fr = f"C'est generalement autour de 300 {currency}, selon le besoin."
        website_price_fr = f"C'est souvent entre 500 {currency} et 700 {currency}, selon les besoins."
        landing_price_en = f"This is usually around 300 {currency}, depending on what is needed."
        website_price_en = f"This is often between 500 {currency} and 700 {currency}, depending on the scope."

        if offer_type == "landing_page":
            if language == "fr":
                return {
                    "subject": "Une version plus claire pour attirer plus de clients",
                    "short_subject": "Landing page plus claire",
                    "intro": "Je suis tombe sur votre site en cherchant des services comme les votres.",
                    "problem": "Je pense qu'il y a une opportunite simple d'ameliorer la conversion avec une page plus claire et orientee clients.",
                    "headline": "Je propose des landing pages modernes :",
                    "feature_1": "design propre et mobile",
                    "feature_2": "message clair",
                    "feature_3": "formulaire de contact",
                    "delivery": "Livraison en general sous 3 a 5 jours.",
                    "price": landing_price_fr,
                    "cta": "Si vous voulez, je peux vous proposer une version adaptee a votre activite.",
                }
            return {
                "subject": "A clearer page to attract more clients",
                "short_subject": "Clearer landing page",
                "intro": "I came across your website while looking for businesses like yours.",
                "problem": "I believe there is a simple opportunity to improve conversion with a clearer, more client-focused page.",
                "headline": "I build modern landing pages:",
                "feature_1": "clean mobile design",
                "feature_2": "clear message",
                "feature_3": "contact form",
                "delivery": "Delivery is usually within 3 to 5 days.",
                "price": landing_price_en,
                "cta": "If useful, I can suggest a version adapted to your business.",
            }

        if language == "fr":
            return {
                "subject": "Une version plus pro et plus efficace de votre site",
                "short_subject": "Site vitrine plus pro",
                "intro": "Je suis tombe sur votre site en cherchant des services comme les votres.",
                "problem": "En regardant votre site, je pense qu'il serait possible de le rendre plus clair et plus efficace pour convertir vos visiteurs.",
                "headline": "Je propose des sites vitrines simples et modernes :",
                "feature_1": "structure claire",
                "feature_2": "design mobile",
                "feature_3": "base SEO propre",
                "delivery": "Livraison en general sous 5 a 7 jours.",
                "price": website_price_fr,
                "cta": "Si vous voulez, je peux vous proposer une version adaptee a votre activite.",
            }
        return {
            "subject": "A more professional and more effective version of your website",
            "short_subject": "More effective website",
            "intro": "I came across your website while looking for businesses like yours.",
            "problem": "Looking at your website, I believe it could be made clearer and more effective at converting visitors.",
            "headline": "I build simple modern showcase websites:",
            "feature_1": "clear structure",
            "feature_2": "mobile design",
            "feature_3": "clean SEO basics",
            "delivery": "Delivery is usually within 5 to 7 days.",
            "price": website_price_en,
            "cta": "If useful, I can suggest a version adapted to your business.",
        }

    def _build_offer_follow_ups(self, prospect: Dict, language: str, offer_type: str) -> Dict[str, Dict[str, str]]:
        business_name = prospect.get("business_name", "")
        signature = get_text_signature(language)
        if language == "fr":
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
