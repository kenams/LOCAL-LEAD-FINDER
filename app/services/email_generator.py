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
                "subject": "Proposition de refonte de site web" if language == "fr" else "Premium website redesign idea",
                "short_subject": "Refonte premium" if language == "fr" else "Premium redesign",
                "body": signature,
                "short_body": signature,
                "long_body": signature,
                "html_body": f"<pre>{escape(signature)}</pre>",
                "follow_ups": {},
            }

    def _build_pack(self, prospect: Dict, language: str) -> Dict[str, object]:
        identity = get_business_identity()
        country = prospect.get("country")
        profile = get_country_profile(country)
        business_name = prospect.get("business_name", "")
        location = prospect.get("location", "")
        category_data = self._get_category_data(prospect.get("category", ""), language)
        price_min = format_price(prospect.get("estimated_price_min", 500 if language == "fr" else 900), country)
        price_max = format_price(prospect.get("estimated_price_max", 800 if language == "fr" else 1400), country)
        delivery_time = prospect.get("estimated_time", "1 a 2 jours" if language == "fr" else "1-2 days")
        issues_lines = self._get_issue_lines(prospect, language)
        mockup_text = self._get_mockup_text(prospect.get("mockup_url"), language)
        mockup_html = self._get_mockup_html(prospect.get("mockup_url"), language)
        market_sentence = self._get_market_sentence(profile.messaging_style, language)
        signature_text = get_text_signature(language)
        signature_html = get_html_signature(language)
        reply_cta = self._get_reply_cta(language)
        hook = self._get_hook(prospect, category_data, language)

        if language == "fr":
            subject = category_data["subject"].format(business_name=business_name)
            short_subject = category_data["short_subject"].format(business_name=business_name)
            greeting = "Bonjour,"
            intro = f"Je vous contacte sous l'identite {identity.sender_display_name}."
            long_body = "\n\n".join(
                part
                for part in [
                    greeting,
                    intro,
                    hook,
                    f"{category_data['pitch']} {market_sentence}",
                    self._render_issue_block(issues_lines, language),
                    "L'idee serait de proposer :\n"
                    f"- {category_data['offer_1']}\n"
                    f"- {category_data['offer_2']}\n"
                    f"- {category_data['offer_3']}",
                    mockup_text,
                    f"Pour ce type de projet, on se situe generalement entre {price_min} et {price_max}, avec une livraison en {delivery_time}.",
                    reply_cta,
                    signature_text,
                ]
                if part
            )
            short_body = "\n\n".join(
                part
                for part in [
                    greeting,
                    hook,
                    mockup_text,
                    f"Je pense qu'une version plus premium pourrait mieux convertir, pour une enveloppe de {price_min} a {price_max}.",
                    "Si vous voulez, repondez simplement OUI et je vous envoie les 3 priorites a traiter en premier.",
                    signature_text,
                ]
                if part
            )
            html_body = self._render_html_email(
                language=language,
                subject=subject,
                greeting=greeting,
                intro=f"Je vous contacte sous l'identite <strong>{escape(identity.sender_display_name)}</strong>.",
                paragraphs=[
                    hook,
                    f"{category_data['pitch']} {market_sentence}",
                    self._render_issue_html(issues_lines, "J'ai notamment releve :"),
                    "L'idee serait de proposer "
                    f"<strong>{escape(category_data['offer_1'])}</strong>, "
                    f"<strong>{escape(category_data['offer_2'])}</strong> et "
                    f"<strong>{escape(category_data['offer_3'])}</strong>.",
                    mockup_html,
                    f"Pour ce type de projet, on se situe generalement entre <strong>{escape(price_min)}</strong> et <strong>{escape(price_max)}</strong>, avec une livraison en <strong>{escape(delivery_time)}</strong>.",
                    "Si le sujet est pertinent, repondez simplement <strong>OUI</strong> et je vous envoie les 3 priorites que je traiterais en premier.",
                ],
                signature_html=signature_html,
            )
        else:
            subject = category_data["subject"].format(business_name=business_name)
            short_subject = category_data["short_subject"].format(business_name=business_name)
            greeting = "Hello,"
            intro = f"I am reaching out as {identity.sender_display_name}."
            long_body = "\n\n".join(
                part
                for part in [
                    greeting,
                    intro,
                    hook,
                    f"{category_data['pitch']} {market_sentence}",
                    self._render_issue_block(issues_lines, language),
                    "The goal would be to deliver:\n"
                    f"- {category_data['offer_1']}\n"
                    f"- {category_data['offer_2']}\n"
                    f"- {category_data['offer_3']}",
                    mockup_text,
                    f"For this kind of project, pricing would usually sit between {price_min} and {price_max}, with delivery in {delivery_time}.",
                    reply_cta,
                    signature_text,
                ]
                if part
            )
            short_body = "\n\n".join(
                part
                for part in [
                    greeting,
                    hook,
                    mockup_text,
                    f"I believe a more premium version could convert better, typically in the {price_min} to {price_max} range.",
                    "If useful, reply with YES and I will send the 3 priority improvements I would make first.",
                    signature_text,
                ]
                if part
            )
            html_body = self._render_html_email(
                language=language,
                subject=subject,
                greeting=greeting,
                intro=f"I am reaching out as <strong>{escape(identity.sender_display_name)}</strong>.",
                paragraphs=[
                    hook,
                    f"{category_data['pitch']} {market_sentence}",
                    self._render_issue_html(issues_lines, "The main points I noticed were:"),
                    "The goal would be to deliver "
                    f"<strong>{escape(category_data['offer_1'])}</strong>, "
                    f"<strong>{escape(category_data['offer_2'])}</strong> and "
                    f"<strong>{escape(category_data['offer_3'])}</strong>.",
                    mockup_html,
                    f"For this kind of project, pricing would usually sit between <strong>{escape(price_min)}</strong> and <strong>{escape(price_max)}</strong>, with delivery in <strong>{escape(delivery_time)}</strong>.",
                    "If useful, reply with <strong>YES</strong> and I will send the 3 priority improvements I would make first.",
                ],
                signature_html=signature_html,
            )

        return {
            "subject": subject,
            "short_subject": short_subject,
            "body": long_body,
            "short_body": short_body,
            "long_body": long_body,
            "html_body": html_body,
            "follow_ups": self._build_follow_ups(prospect, language, category_data),
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
