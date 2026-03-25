"""
Mockup generator service.
"""
from __future__ import annotations

import os
import re
from typing import Dict

from jinja2 import Template

from app.core.branding import get_business_identity, get_mockup_quality_level, get_mockup_style_rule
from app.core.config import settings
from app.core.logging import logger


class MockupGenerator:
    """Generate premium HTML mockups for prospect-facing previews."""

    def __init__(self):
        self.output_dir = os.path.join(os.path.dirname(__file__), "..", "..", "exports", "mockups")
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_mockup(
        self,
        business_name: str,
        category: str,
        city: str,
        language: str = "fr",
        quality_level: str | None = None,
    ) -> str:
        """Generate an HTML mockup and return its file path."""
        try:
            style = get_mockup_style_rule(category)
            quality = quality_level or get_mockup_quality_level()
            content = self._build_content(business_name, category, city, language, style.key)
            html = Template(self._get_template()).render(
                business_name=business_name,
                category=category,
                city=city,
                language=language,
                style=style,
                content=content,
                quality=quality,
                is_trade=style.key == "trade",
                show_studio_credit=settings.MOCKUP_INCLUDE_STUDIO_CREDIT,
                studio_identity=get_business_identity(),
            )

            filename = self._build_filename(business_name)
            filepath = os.path.join(self.output_dir, filename)
            with open(filepath, "w", encoding="utf-8") as handle:
                handle.write(html)

            logger.info(f"Generated premium mockup: {filepath}")
            return filepath
        except Exception as exc:
            logger.error(f"Mockup generation failed: {exc}")
            return ""

    def _build_filename(self, business_name: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "_", business_name.strip().lower())
        slug = re.sub(r"_+", "_", slug).strip("_") or "prospect"
        return f"{slug}_mockup.html"

    def _build_content(self, business_name: str, category: str, city: str, language: str, style_key: str) -> Dict[str, object]:
        builders = {
            "beauty": self._beauty_content,
            "trade": self._trade_content,
            "wellness": self._wellness_content,
            "restaurant": self._restaurant_content,
            "professional": self._professional_content,
        }
        return builders.get(style_key, self._professional_content)(business_name, category, city, language)

    def _beauty_content(self, business_name: str, _category: str, city: str, language: str) -> Dict[str, object]:
        if language == "en":
            return {
                "kicker": "Signature beauty destination",
                "title": "Editorial elegance designed to convert more appointments.",
                "intro": f"{business_name} deserves a more desirable digital presence in {city}, with a stronger booking flow and a premium first impression.",
                "cta_primary": "Book your consultation",
                "cta_secondary": "View signature services",
                "highlight_title": "A more premium atmosphere from the first scroll.",
                "highlight_text": "Cleaner hierarchy, stronger gallery rhythm, sharper service storytelling and clearer pricing confidence.",
                "services": [
                    ("Signature cuts", "Sharper editorial service positioning for premium bookings."),
                    ("Color expertise", "A cleaner way to showcase transformations and pricing tiers."),
                    ("Event styling", "A more desirable presentation for high-value appointments."),
                ],
                "benefits": ["Booking-first structure", "Premium service blocks", "Clear pricing cues", "Transformation stories"],
                "testimonials": [
                    ("The studio feels elevated before the appointment even starts.", city),
                    ("This direction makes the brand look more premium and more in demand.", city),
                ],
            }
        return {
            "kicker": "Destination beaute signature",
            "title": "Une elegance editoriale pensee pour convertir plus de rendez-vous.",
            "intro": f"{business_name} merite une presence digitale plus desirables a {city}, avec une reservation plus fluide et une premiere impression plus premium.",
            "cta_primary": "Prendre rendez-vous",
            "cta_secondary": "Voir les prestations",
            "highlight_title": "Une atmosphere plus premium des le premier scroll.",
            "highlight_text": "Une hierarchie plus claire, une meilleure galerie, un storytelling prestations plus fort et des tarifs plus rassurants.",
            "services": [
                ("Coupes signature", "Une mise en scene plus desirables des prestations iconiques."),
                ("Coloration experte", "Une presentation plus nette des transformations et des tarifs."),
                ("Coiffage evenementiel", "Une structure plus premium pour les prestations a forte valeur."),
            ],
            "benefits": ["Structure orientee reservation", "Blocs prestations premium", "Tarifs plus lisibles", "Histoires de transformation"],
            "testimonials": [
                ("L'impression premium est plus forte avant meme le rendez-vous.", city),
                ("Cette direction rend la marque plus haut de gamme et plus desiree.", city),
            ],
        }

    def _trade_content(self, business_name: str, category: str, city: str, language: str) -> Dict[str, object]:
        trade_label = "electrician" if "elect" in category.lower() else "plumber" if "plomb" in category.lower() or "plumb" in category.lower() else "trade"
        if language == "en":
            return {
                "kicker": "Trusted local response",
                "title": "A stronger emergency-first website built to win calls faster.",
                "intro": f"{business_name} needs a site that feels reliable within seconds and turns local demand in {city} into immediate phone calls and quote requests.",
                "cta_primary": "Call for urgent assistance",
                "cta_secondary": "See covered services",
                "highlight_title": "Built for urgent leads, stronger trust and cleaner conversion.",
                "highlight_text": "This direction puts the phone CTA, emergency promise, guarantee blocks and local proof exactly where trades prospects expect them.",
                "hero_alert": "Emergency support available 7 days a week",
                "hero_badge": "Phone-first conversion",
                "hero_card_title": "Fast local response",
                "hero_card_text": "A much clearer emergency path, stronger trust cues and better service coverage on mobile.",
                "service_note": "Designed to reduce hesitation and push urgent visitors to call sooner.",
                "services": [
                    ("Emergency repairs", "The urgent service offer is moved to the front with a stronger response CTA and clearer reassurance."),
                    ("Installations & upgrades", "Larger, cleaner cards explain long-term jobs without losing the premium visual polish."),
                    ("Maintenance & diagnostics", "Trust-led copy, guarantee blocks and conversion cues help turn browsing visitors into leads."),
                ],
                "benefits": ["24/7 visibility", "Direct phone CTA", "Guarantee-first trust", "Coverage area clarity"],
                "trust_stats": [("7j/7", "Visible emergency availability"), ("<30 min", "Response-style promise"), ("Local", "Territory and service clarity")],
                "proof_items": ["Certified team", "Transparent quotes", "Workmanship guarantee", "Fast local dispatch"],
                "testimonials": [
                    ("This version feels much more serious and much easier to trust when the issue is urgent.", "Homeowner perspective"),
                    ("The path from leak or outage to phone call is far more direct.", "Conversion review"),
                ],
                "process_title": "A clearer process that removes friction before the first call.",
                "process_steps": [
                    ("1", "Call or request help", "The emergency path is visible above the fold and repeated on mobile."),
                    ("2", "Quick triage and quote", "The site explains what happens next, which reduces hesitation."),
                    ("3", "Fast local intervention", "Trust signals and guarantees reinforce the decision to contact."),
                ],
                "contact_title": f"A premium {trade_label} landing page that feels more trustworthy immediately.",
                "contact_text": "More urgency, stronger proof, better service hierarchy and a much clearer mobile call journey.",
                "contact_lines": [
                    ("Emergency line", "Priority response for urgent requests"),
                    ("Quote promise", "Clear diagnosis and rapid follow-up"),
                    ("Coverage area", f"{city} and nearby service zones"),
                ],
            }
        return {
            "kicker": "Intervention locale de confiance",
            "title": "Un site urgence-premium pense pour faire appeler plus vite.",
            "intro": f"{business_name} a besoin d'un site qui rassure en quelques secondes et transforme la demande locale a {city} en appels directs et demandes de devis.",
            "cta_primary": "Appel urgence prioritaire",
            "cta_secondary": "Voir les interventions",
            "highlight_title": "Pense pour l'urgence, la confiance et une conversion plus directe.",
            "highlight_text": "Cette direction place la CTA telephone, la promesse de reactivite, les garanties et les preuves locales exactement la ou un prospect artisan les attend.",
            "hero_alert": "Urgence 7j/7 avec reponse prioritaire",
            "hero_badge": "Parcours telephone-first",
            "hero_card_title": "Intervention locale rapide",
            "hero_card_text": "Une CTA appel beaucoup plus visible, des preuves de confiance plus fortes et une lecture mobile bien plus efficace.",
            "service_note": "Concu pour reduire l'hesitation et faire appeler plus vite un prospect local.",
            "services": [
                ("Depannage urgent", "Le besoin immediat passe au premier plan avec une CTA plus forte et une reassurance visible des le hero."),
                ("Installation et remplacement", "Des cartes plus propres mettent en valeur les travaux planifies sans perdre la sensation premium."),
                ("Entretien et diagnostic", "Une structure orientee confiance transforme mieux les visiteurs encore hesitants."),
            ],
            "benefits": ["Urgence 7j/7 visible", "CTA appel direct", "Garanties rassurantes", "Zone d'intervention claire"],
            "trust_stats": [("7j/7", "Urgence visible"), ("<30 min", "Promesse de reponse"), ("Local", "Ancrage terrain")],
            "proof_items": ["Equipe certifiee", "Devis transparents", "Travaux garantis", "Intervention locale rapide"],
            "testimonials": [
                ("Cette version parait beaucoup plus serieuse et plus fiable quand le besoin est urgent.", "Perspective client"),
                ("Le passage entre le probleme et l'appel devient beaucoup plus direct.", "Lecture conversion"),
            ],
            "process_title": "Un process plus clair qui retire les frictions avant le premier appel.",
            "process_steps": [
                ("1", "Appel ou demande rapide", "Le chemin urgence est visible des le hero et repete sur mobile."),
                ("2", "Qualification et devis", "Le site explique ce qui se passe ensuite, ce qui rassure immediatement."),
                ("3", "Intervention locale", "Les garanties et la preuve sociale renforcent la decision d'appeler."),
            ],
            "contact_title": "Une landing page artisan beaucoup plus rassurante des les premieres secondes.",
            "contact_text": "Plus d'urgence, plus de preuves, une meilleure hierarchie services et un parcours appel mobile bien plus clair.",
            "contact_lines": [
                ("Ligne urgence", "Prise en charge prioritaire des demandes urgentes"),
                ("Promesse devis", "Diagnostic clair et reponse rapide"),
                ("Zone couverte", f"{city} et zones d'intervention voisines"),
            ],
        }

    def _wellness_content(self, business_name: str, _category: str, city: str, language: str) -> Dict[str, object]:
        if language == "en":
            return {
                "kicker": "Premium wellness atmosphere",
                "title": "A calmer, softer and more premium booking experience.",
                "intro": f"{business_name} can feel more elevated online in {city} with a quieter visual rhythm and a more reassuring client journey.",
                "cta_primary": "Book a treatment",
                "cta_secondary": "Discover the rituals",
                "highlight_title": "Designed to communicate calm, trust and premium care.",
                "highlight_text": "More visual breathing room, better treatment storytelling and a smoother path to reservation.",
                "services": [
                    ("Signature treatments", "More premium storytelling for the most profitable services."),
                    ("Membership rituals", "Cleaner packaging for repeat clients and premium experiences."),
                    ("Client reassurance", "A more polished way to show expertise and atmosphere."),
                ],
                "benefits": ["Refined spacing", "Treatment storytelling", "Calm palette", "Reservation CTA"],
                "testimonials": [
                    ("The website feels like part of the treatment experience.", city),
                    ("Much calmer, more credible and more premium than a standard page.", city),
                ],
            }
        return {
            "kicker": "Atmosphere bien-etre premium",
            "title": "Une experience plus calme, plus douce et plus haut de gamme.",
            "intro": f"{business_name} peut gagner en valeur percue a {city} avec un rythme plus apaisant et un parcours plus rassurant.",
            "cta_primary": "Reserver un soin",
            "cta_secondary": "Decouvrir les rituels",
            "highlight_title": "Concu pour transmettre le calme, la confiance et le soin premium.",
            "highlight_text": "Plus de respiration visuelle, une meilleure mise en scene des soins et un parcours reservation plus fluide.",
            "services": [
                ("Soins signature", "Une mise en valeur plus premium des prestations phares."),
                ("Rituels et abonnements", "Une structure plus nette pour les offres a plus forte valeur."),
                ("Reassurance cliente", "Une presentation plus propre de l'expertise et de l'ambiance."),
            ],
            "benefits": ["Respiration visuelle", "Storytelling soin", "Palette apaisante", "CTA reservation"],
            "testimonials": [
                ("Le site prolonge l'experience du soin avant meme le rendez-vous.", city),
                ("C'est beaucoup plus calme, plus credible et plus premium.", city),
            ],
        }

    def _restaurant_content(self, business_name: str, _category: str, city: str, language: str) -> Dict[str, object]:
        if language == "en":
            return {
                "kicker": "Refined hospitality",
                "title": "A more desirable digital storefront for reservations and mood.",
                "intro": f"{business_name} can feel more memorable in {city} with a stronger menu structure and a more inviting reservation flow.",
                "cta_primary": "Reserve a table",
                "cta_secondary": "View the menu",
                "highlight_title": "A stronger first impression before the guest arrives.",
                "highlight_text": "Atmosphere, menu clarity and booking cues are elevated without losing elegance.",
                "services": [
                    ("Signature menu", "A clearer path into the most desirable dishes and offers."),
                    ("Reservation flow", "A more direct booking journey with less friction."),
                    ("Ambience and trust", "More premium proof and clearer hospitality cues."),
                ],
                "benefits": ["Menu clarity", "Reservation visibility", "Mood storytelling", "Refined social proof"],
                "testimonials": [
                    ("The atmosphere is communicated immediately, not buried in text.", city),
                    ("This style makes the place feel worth booking straight away.", city),
                ],
            }
        return {
            "kicker": "Hospitalite raffinee",
            "title": "Une vitrine digitale plus desirables pour la reservation et l'ambiance.",
            "intro": f"{business_name} peut devenir plus memorables a {city} avec une carte mieux structuree et une reservation plus fluide.",
            "cta_primary": "Reserver une table",
            "cta_secondary": "Voir la carte",
            "highlight_title": "Une meilleure premiere impression avant meme l'arrivee du client.",
            "highlight_text": "L'ambiance, la clarte de la carte et la reservation sont renforcees sans perdre en elegance.",
            "services": [
                ("Carte signature", "Une lecture plus desirables des plats et des offres."),
                ("Reservation fluide", "Un parcours plus direct jusqu'a la reservation."),
                ("Ambiance et confiance", "Une meilleure preuve sociale et plus de ressenti premium."),
            ],
            "benefits": ["Carte lisible", "Reservation visible", "Storytelling ambiance", "Preuve sociale premium"],
            "testimonials": [
                ("L'ambiance est ressentie immediatement sans se perdre dans le texte.", city),
                ("Cette direction donne envie de reserver beaucoup plus vite.", city),
            ],
        }

    def _professional_content(self, business_name: str, category: str, city: str, language: str) -> Dict[str, object]:
        if language == "en":
            return {
                "kicker": "Executive credibility",
                "title": "A more credible and premium website for serious enquiries.",
                "intro": f"{business_name} can present its {category} expertise in {city} with more clarity, authority and trust.",
                "cta_primary": "Request a consultation",
                "cta_secondary": "See core expertise",
                "highlight_title": "Premium minimalism designed for clarity and trust.",
                "highlight_text": "Less noise, more authority, cleaner enquiry flow and stronger mobile readability.",
                "services": [
                    ("Clear expertise blocks", "A sharper way to structure services and decision points."),
                    ("Trust-led layout", "A cleaner proof system for authority and reassurance."),
                    ("Consultation conversion", "A more direct enquiry path from mobile and desktop."),
                ],
                "benefits": ["Executive hierarchy", "Premium minimalism", "Sharper CTA", "Mobile clarity"],
                "testimonials": [
                    ("The business feels more established and more premium.", city),
                    ("This direction gives more confidence before the first conversation.", city),
                ],
            }
        return {
            "kicker": "Credibilite executive",
            "title": "Un site plus credible et plus premium pour des demandes serieuses.",
            "intro": f"{business_name} peut mieux presenter son expertise {category} a {city} avec plus de clarte, d'autorite et de confiance.",
            "cta_primary": "Demander une consultation",
            "cta_secondary": "Voir les expertises",
            "highlight_title": "Un minimalisme premium pense pour la clarte et la confiance.",
            "highlight_text": "Moins de bruit visuel, plus d'autorite, une prise de contact plus nette et une meilleure lisibilite mobile.",
            "services": [
                ("Expertises plus nettes", "Une structure plus claire des services et de la valeur apportee."),
                ("Structure orientee confiance", "Des preuves plus lisibles de serieux et d'experience."),
                ("Conversion consultation", "Un parcours plus direct vers la prise de contact."),
            ],
            "benefits": ["Hierarchie executive", "Minimalisme premium", "CTA plus net", "Lisibilite mobile"],
            "testimonials": [
                ("L'activite parait plus etablie et plus premium.", city),
                ("Cette direction inspire plus confiance avant le premier echange.", city),
            ],
        }

    def _get_template(self) -> str:
        return """
<!DOCTYPE html>
<html lang="{{ language }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ business_name }} - {{ city }}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Cormorant+Garamond:wght@600;700&family=Space+Grotesk:wght@500;700&display=swap');
        :root{--bg:{{ style.background }};--surface:{{ style.surface }};--surface-alt:{{ style.surface_alt }};--accent:{{ style.accent }};--soft:{{ style.accent_soft }};--text:{{ style.text }};--muted:{{ style.muted }};--border:{{ style.border }};}
        *{box-sizing:border-box}body{margin:0;font-family:{{ style.body_font }};color:var(--text);background:radial-gradient(circle at top left,rgba(255,255,255,.06),transparent 25%),linear-gradient(180deg,#090a0d,var(--bg))}
        .shell{width:min(1180px,calc(100% - 28px));margin:0 auto;padding:18px 0 42px}
        .hero,.panel,.trade-strip,.trade-process,.trade-urgency{border:1px solid var(--border);border-radius:30px;background:linear-gradient(180deg,rgba(255,255,255,.04),rgba(255,255,255,.015));box-shadow:0 24px 72px rgba(0,0,0,.24)}
        .hero{padding:28px;overflow:hidden;position:relative}.hero:after{content:"";position:absolute;inset:auto -10% -24% auto;width:380px;height:380px;background:radial-gradient(circle,var(--accent),transparent 70%);opacity:.12;filter:blur({{ "28px" if quality == "premium" else "14px" }})}
        .topbar,.hero-grid,.head,.cta-grid{display:grid;gap:18px}.topbar{grid-template-columns:1fr auto;align-items:center}.hero-grid{grid-template-columns:1.15fr .85fr;align-items:end;margin-top:26px}
        .brand{display:flex;gap:14px;align-items:center}.mark{width:46px;height:46px;border-radius:16px;display:grid;place-items:center;background:linear-gradient(135deg,var(--soft),var(--accent));color:#0e0e0e;font-weight:800;letter-spacing:.12em}
        .brand h1,.copy h2,.panel h3,.trade-process h3,.trade-urgency h3{font-family:{{ style.heading_font }};margin:0}.brand p,.copy p,.panel p,.quote p,.contact p,.trade-process p,.trade-urgency p{color:var(--muted);line-height:1.75}
        .pills{display:flex;gap:10px;flex-wrap:wrap;justify-content:flex-end}.pill,.benefit,.stat,.service,.quote,.contact-line,.proof-item,.trade-step{border:1px solid var(--border);background:rgba(255,255,255,.03);border-radius:18px}
        .pill{padding:10px 14px;color:var(--soft);font-size:.78rem;font-weight:800;text-transform:uppercase;letter-spacing:.1em}
        .eyebrow{color:var(--accent);font-size:.78rem;font-weight:800;letter-spacing:.16em;text-transform:uppercase;margin-bottom:14px}.copy h2{font-size:clamp(2.4rem,5vw,4.9rem);line-height:.95;max-width:12ch}
        .actions{display:flex;gap:12px;flex-wrap:wrap;margin-top:24px}.btn1,.btn2,.btn-phone{padding:14px 20px;border-radius:16px;font-weight:800;display:inline-flex;align-items:center;justify-content:center}.btn1{background:linear-gradient(135deg,var(--soft),var(--accent));color:#0d0d0d}.btn2{border:1px solid var(--border)}.btn-phone{background:#f5f0e4;color:#0e1014;min-width:230px;box-shadow:0 18px 38px rgba(0,0,0,.22)}
        .visual{min-height:520px;border-radius:28px;border:1px solid var(--border);position:relative;background:radial-gradient(circle at 20% 18%,rgba(255,255,255,.09),transparent 26%),linear-gradient(180deg,rgba(255,255,255,.06),rgba(255,255,255,.02))}
        .floating{position:absolute;padding:18px;border-radius:22px;border:1px solid rgba(255,255,255,.1);background:rgba(17,19,23,.82);backdrop-filter:blur(18px)}.floating.top{top:26px;right:26px;width:min(86%,310px)}.floating.bottom{left:26px;bottom:26px;width:min(88%,330px)}
        .mini{color:var(--accent);font-size:.72rem;font-weight:800;letter-spacing:.12em;text-transform:uppercase}.floating h3{font-size:1.3rem;margin:10px 0 8px}
        .stats,.services,.benefits,.quotes,.proof-grid,.trade-steps{display:grid;gap:16px}.stats{grid-template-columns:repeat(3,1fr);margin-top:22px}.stat{padding:16px}.stat strong{display:block;color:var(--soft);font-size:1.5rem}
        .stack{display:grid;gap:18px;margin-top:22px}.panel,.trade-process,.trade-strip{padding:28px}.head{grid-template-columns:1.1fr .9fr;align-items:end;margin-bottom:24px}.services{grid-template-columns:repeat(3,1fr)}.service{padding:22px}.service strong{display:block;color:var(--soft);margin-bottom:10px;font-size:1.02rem}
        .benefits{grid-template-columns:repeat(4,1fr)}.benefit{padding:14px 16px;font-weight:700}.quotes{grid-template-columns:repeat(2,1fr)}.quote{padding:22px}.quote footer{margin-top:14px;color:var(--accent);font-size:.76rem;font-weight:800;letter-spacing:.1em;text-transform:uppercase}
        .cta-grid{grid-template-columns:1.05fr .95fr}.contact-line{padding:14px 16px}.contact-line span{display:block;color:var(--accent);font-size:.72rem;font-weight:800;letter-spacing:.1em;text-transform:uppercase;margin-bottom:6px}.foot{margin-top:18px;text-align:center;color:var(--muted)}
        .credit{margin-top:8px;color:var(--accent);font-size:.72rem;font-weight:800;letter-spacing:.1em;text-transform:uppercase}
        .trade-urgency{padding:18px 20px;display:grid;grid-template-columns:1.3fr auto;gap:16px;align-items:center;background:linear-gradient(135deg,rgba(255,255,255,.08),rgba(255,255,255,.02))}
        .trade-urgency strong{display:block;color:var(--soft);font-size:1.05rem;letter-spacing:.06em;text-transform:uppercase}
        .proof-grid{grid-template-columns:repeat(4,1fr)}.proof-item{padding:14px 15px;font-weight:700}
        .trade-steps{grid-template-columns:repeat(3,1fr);margin-top:18px}.trade-step{padding:20px}.trade-step .num{display:inline-flex;width:34px;height:34px;border-radius:999px;align-items:center;justify-content:center;background:linear-gradient(135deg,var(--soft),var(--accent));color:#0d0d0d;font-weight:800;margin-bottom:14px}.trade-step strong{display:block;color:var(--soft);margin-bottom:8px}
        @media(max-width:980px){.hero-grid,.head,.cta-grid,.services,.benefits,.quotes,.stats,.proof-grid,.trade-steps,.trade-urgency{grid-template-columns:1fr}.visual{min-height:430px}}
        @media(max-width:640px){.shell{width:min(100% - 16px,100%)}.hero,.panel,.trade-strip,.trade-process,.trade-urgency{padding:20px;border-radius:24px}.topbar{grid-template-columns:1fr}.pills{justify-content:flex-start}.copy h2{font-size:2.2rem}.btn1,.btn2,.btn-phone{width:100%;text-align:center}.floating.top,.floating.bottom{left:16px;right:16px;width:auto}}
    </style>
</head>
<body>
<div class="shell">
    {% if is_trade %}
    <section class="trade-urgency">
        <div><strong>{{ content.hero_alert }}</strong><p>{{ content.highlight_text }}</p></div>
        <a class="btn-phone" href="#contact">{{ content.cta_primary }}</a>
    </section>
    {% endif %}
    <section class="hero">
        <div class="topbar">
            <div class="brand"><div class="mark">{{ business_name[:2]|upper }}</div><div><h1>{{ business_name }}</h1><p>{{ city }} · {{ category }}</p></div></div>
            <div class="pills"><div class="pill">{{ quality }}</div><div class="pill">{{ content.kicker }}</div>{% if is_trade %}<div class="pill">{{ content.hero_badge }}</div>{% endif %}</div>
        </div>
        <div class="hero-grid">
            <div class="copy">
                <div class="eyebrow">{{ content.kicker }}</div>
                <h2>{{ content.title }}</h2>
                <p>{{ content.intro }}</p>
                <div class="actions">{% if is_trade %}<a class="btn-phone" href="#contact">{{ content.cta_primary }}</a>{% else %}<a class="btn1" href="#contact">{{ content.cta_primary }}</a>{% endif %}<a class="btn2" href="#services">{{ content.cta_secondary }}</a></div>
                <div class="stats">{% if is_trade %}{% for stat in content.trust_stats %}<div class="stat"><strong>{{ stat[0] }}</strong><span>{{ stat[1] }}</span></div>{% endfor %}{% else %}<div class="stat"><strong>{{ "Premium" if quality == "premium" else "Clean" }}</strong><span>{{ "Visual level" if language == "en" else "Niveau visuel" }}</span></div><div class="stat"><strong>Mobile</strong><span>{{ "Optimised experience" if language == "en" else "Experience optimisee" }}</span></div><div class="stat"><strong>CTA</strong><span>{{ "Conversion-first flow" if language == "en" else "Parcours oriente conversion" }}</span></div>{% endif %}</div>
            </div>
            <div class="visual"><div class="floating top"><div class="mini">{{ content.highlight_title }}</div><h3>{{ content.hero_card_title if is_trade else content.kicker }}</h3><p>{{ content.hero_card_text if is_trade else content.highlight_text }}</p></div><div class="floating bottom"><div class="mini">{{ city }}</div><h3>{{ content.cta_primary }}</h3><p>{{ content.service_note if is_trade else content.intro }}</p></div></div>
        </div>
    </section>
    {% if is_trade %}
    <section class="trade-strip" style="margin-top:18px;"><div class="head"><div><div class="eyebrow">{{ "Trust signals" if language == "en" else "Signaux de confiance" }}</div><h3>{{ "Proof placed where urgent prospects expect it" if language == "en" else "Des preuves placees la ou le prospect les attend" }}</h3></div><p>{{ content.service_note }}</p></div><div class="proof-grid">{% for item in content.proof_items %}<div class="proof-item">{{ item }}</div>{% endfor %}</div></section>
    {% endif %}
    <div class="stack">
        <section class="panel" id="services"><div class="head"><div><div class="eyebrow">{{ content.highlight_title }}</div><h3>{{ content.title }}</h3></div><p>{{ content.highlight_text }}</p></div><div class="services">{% for service in content.services %}<div class="service"><strong>{{ service[0] }}</strong><p>{{ service[1] }}</p></div>{% endfor %}</div></section>
        {% if is_trade %}
        <section class="trade-process"><div class="head"><div><div class="eyebrow">{{ "Process" if language == "en" else "Process" }}</div><h3>{{ content.process_title }}</h3></div><p>{{ content.contact_text }}</p></div><div class="trade-steps">{% for step in content.process_steps %}<div class="trade-step"><div class="num">{{ step[0] }}</div><strong>{{ step[1] }}</strong><p>{{ step[2] }}</p></div>{% endfor %}</div></section>
        {% endif %}
        <section class="panel"><div class="head"><div><div class="eyebrow">{{ "Trust blocks" if language == "en" else "Blocs de confiance" }}</div><h3>{{ "Built to reassure and convert" if language == "en" else "Concu pour rassurer et convertir" }}</h3></div><p>{{ content.intro }}</p></div><div class="benefits">{% for benefit in content.benefits %}<div class="benefit">{{ benefit }}</div>{% endfor %}</div></section>
        <section class="panel"><div class="head"><div><div class="eyebrow">{{ "Client perspective" if language == "en" else "Perspective client" }}</div><h3>{{ "What a stronger first impression looks like" if language == "en" else "Ce qu'une meilleure premiere impression change" }}</h3></div><p>{{ content.highlight_text }}</p></div><div class="quotes">{% for quote in content.testimonials %}<div class="quote"><p>"{{ quote[0] }}"</p><footer>{{ quote[1] }}</footer></div>{% endfor %}</div></section>
        <section class="panel" id="contact">
            <div class="cta-grid">
                <div class="contact"><div class="eyebrow">{{ content.kicker }}</div><h3>{{ content.contact_title if is_trade else content.cta_primary }}</h3><p>{{ content.contact_text if is_trade else content.intro }}</p><div class="actions">{% if is_trade %}<a class="btn-phone" href="#">{{ content.cta_primary }}</a>{% else %}<a class="btn1" href="#">{{ content.cta_primary }}</a>{% endif %}<a class="btn2" href="#">{{ content.cta_secondary }}</a></div></div>
                <div class="contact"><div class="eyebrow">{{ "Contact" if language == "en" else "Contact" }}</div><h3>{{ "A cleaner local conversion page" if language == "en" else "Une page locale plus convaincante" }}</h3><p>{{ content.highlight_text }}</p>{% if is_trade %}{% for line in content.contact_lines %}<div class="contact-line"><span>{{ line[0] }}</span>{{ line[1] }}</div>{% endfor %}{% else %}<div class="contact-line"><span>{{ "Opening hours" if language == "en" else "Horaires" }}</span>{{ "Monday to Saturday · 9:00 to 19:00" if language == "en" else "Du lundi au samedi · 9h00 a 19h00" }}</div><div class="contact-line"><span>{{ "Response promise" if language == "en" else "Promesse de reponse" }}</span>{{ "Fast reply with premium service guidance" if language == "en" else "Reponse rapide avec accompagnement premium" }}</div><div class="contact-line"><span>{{ "Local positioning" if language == "en" else "Ancrage local" }}</span>{{ city }} · {{ category }}</div>{% endif %}</div>
            </div>
            <div class="foot">{{ business_name }} · {{ city }}{% if show_studio_credit %}<div class="credit">Preview prepared by {{ studio_identity.business_name }}</div>{% endif %}</div>
        </section>
    </div>
</div>
</body>
</html>
        """.strip()
