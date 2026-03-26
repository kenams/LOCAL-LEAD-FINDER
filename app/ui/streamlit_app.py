"""
Streamlit UI.
"""
import asyncio
import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.branding import get_business_identity, get_mockup_quality_level, get_sender_preview_rows, get_text_signature
from app.core.config import settings
from app.core.country_config import format_price_range, get_country_display_name
from app.core.logging import logger
from app.core.sender_identity import normalize_sender_content
from app.db.session import SessionLocal, init_db
from app.models.prospect import Prospect
from app.models.search_run import SearchRun
from app.services.export_service import ExportService
from app.services.lead_service import LeadService
from app.services.report_service import ReportService
from app.services.scheduler_service import SchedulerService
from app.ui.ui_theme import badge_html, inject_global_styles, priority_badge_html, render_brand_header, render_key_value_card, render_metric_card, render_section, render_sidebar_brand, status_badge_html

SEARCH_LOCATIONS = ["Toulouse", "Montpellier", "Marseille", "Paris", "Geneva", "Zurich", "Lausanne", "New York", "Miami", "Dallas", "Los Angeles", "Sydney", "Melbourne", "Brisbane", "London", "Manchester"]
SEARCH_CATEGORIES = ["coiffeur", "salon de coiffure", "institut de beaute", "spa", "plombier", "electricien", "dentiste", "avocat", "restaurant", "boulangerie", "coach sportif", "garagiste"]
AUTO_ZONE_GROUPS = {
    "France": ["Paris", "Toulouse", "Montpellier", "Marseille", "Lyon", "Nice", "Bordeaux", "Lille"],
    "Suisse": ["Geneva", "Lausanne", "Zurich", "Basel", "Bern", "Fribourg"],
    "Royaume-Uni": ["London", "Manchester", "Birmingham", "Leeds", "Bristol"],
    "Etats-Unis": ["New York", "Miami", "Dallas", "Los Angeles", "Chicago", "San Francisco", "Austin"],
    "Australie": ["Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide"],
    "Canada": ["Montreal", "Toronto", "Vancouver", "Quebec", "Calgary"],
}
AUTO_CATEGORY_OPTIONS = [
    "marketing",
    "consultant",
    "agency",
    "web design",
    "seo",
    "coach",
    "accountant",
    "lawyer",
    "financial advisor",
    "real estate",
    "coiffeur",
    "institut de beaute",
    "spa",
    "plombier",
    "electricien",
    "dentiste",
    "restaurant",
]
TIME_SLOT_HOURS = {"Matin": 9, "Midi": 13, "Soir": 18}

STATUS_LABELS = {
    "IDLE": "En attente",
    "RUNNING": "En cours",
    "SUCCESS": "Succes",
    "FAILED": "Echec",
    "SENT": "Envoye",
    "SKIPPED": "Ignore",
    "NOT_SENT": "Non envoye",
    "REPLIED": "A repondu",
    "INTERESTED": "Interesse",
    "WON": "Gagne",
    "LOST": "Perdu",
    "NO_RESPONSE": "Pas de reponse",
    "READY": "Pret",
    "PENDING": "En attente",
    "NEVER": "Jamais",
    "LAUNCHED": "Lance",
    "COMPLETED": "Termine",
    "ON": "Actif",
    "OFF": "Inactif",
    "UNKNOWN": "Inconnu",
}

BOOL_LABELS = {True: "Oui", False: "Non"}
FILTER_ALL = "Tous"
CHANNEL_LABELS = {
    "email": "Email",
    "phone": "Telephone",
    "contact_form": "Formulaire de contact",
    "instagram": "Instagram",
    "facebook": "Facebook",
    "unavailable": "Indisponible",
}
OFFER_LABELS = {
    "landing_page": "Landing page",
    "website": "Site vitrine",
}
MOCKUP_LABELS = {
    "deployed": "Deployee",
    "pending": "En attente",
    "failed": "Echec",
}


def main():
    st.set_page_config(page_title="KAH-Digital", page_icon="K", layout="wide")
    init_db()
    inject_global_styles()
    render_sidebar()
    render_brand_header()
    render_automation_center()
    render_manual_debug_mode()


def display_status(value: str | None, default: str = "N/A") -> str:
    if value is None or value == "":
        return default
    normalized = str(value).upper()
    return STATUS_LABELS.get(normalized, str(value))


def display_bool(value: bool) -> str:
    return BOOL_LABELS[bool(value)]


def display_channel(value: str | None, default: str = "N/A") -> str:
    if value is None or value == "":
        return default
    return CHANNEL_LABELS.get(str(value).lower(), str(value))


def display_offer(value: str | None, default: str = "N/A") -> str:
    if value is None or value == "":
        return default
    return OFFER_LABELS.get(str(value).lower(), str(value))


def display_mockup_status(value: str | None, default: str = "N/A") -> str:
    if value is None or value == "":
        return default
    return MOCKUP_LABELS.get(str(value).lower(), str(value))


def split_csv_values(raw_value: str | None) -> list[str]:
    if not raw_value:
        return []
    return [item.strip() for item in str(raw_value).split(",") if item.strip()]


def join_csv_values(selected_values: list[str], custom_values: str | None = None) -> str:
    merged: list[str] = []
    for value in list(selected_values) + split_csv_values(custom_values):
        if value and value not in merged:
            merged.append(value)
    return ",".join(merged)


def infer_time_slots(cron_expression: str | None) -> list[str]:
    if not cron_expression:
        return []
    parts = str(cron_expression).split()
    if len(parts) != 5:
        return []
    hour_field = parts[1]
    selected: list[str] = []
    for slot_label, hour in TIME_SLOT_HOURS.items():
        if str(hour) in hour_field.split(","):
            selected.append(slot_label)
    return selected


def build_daily_cron(selected_slots: list[str]) -> str:
    selected_hours = [str(TIME_SLOT_HOURS[slot]) for slot in selected_slots if slot in TIME_SLOT_HOURS]
    unique_hours = list(dict.fromkeys(selected_hours))
    if not unique_hours:
        return "0 9 * * *"
    return f"0 {','.join(unique_hours)} * * *"


def render_automation_center():
    scheduler_service = SchedulerService()
    report_service = ReportService()
    status = scheduler_service.get_auto_schedule_status()
    report_rows = report_service.list_reports(limit=20)
    latest_report = report_service.load_report(report_rows[0]["path"]) if report_rows else None
    latest_summary = latest_report.get("summary", {}) if latest_report else {}
    latest_funnel = latest_report.get("quality_funnel", {}) if latest_report else {}
    latest_business = latest_report.get("business_snapshot", {}) if latest_report else {}
    report_status = "READY" if status.get("last_report_path") else "PENDING"

    render_section("Automatisation", "Moniteur d'automatisation", "Surveille le moteur autonome, consulte les derniers runs, les rapports et les reglages du planning.")
    status_cols = st.columns(6)
    with status_cols[0]:
        render_metric_card("Automatisation", display_status("ON" if status.get("enabled") else "OFF"), "Etat du mode auto")
    with status_cols[1]:
        render_metric_card("Planning", status.get("cron_expression", settings.AUTO_MODE_CRON), "Expression cron")
    with status_cols[2]:
        render_metric_card("Prochain run", format_datetime_label(status.get("next_run")), "Execution prevue")
    with status_cols[3]:
        render_metric_card("Dernier run", format_datetime_label(status.get("last_run")), "Derniere execution")
    with status_cols[4]:
        render_metric_card("Dernier statut", display_status(status.get("last_status", "IDLE")), "Resultat du dernier run")
    with status_cols[5]:
        render_metric_card("Statut rapport", display_status(report_status), "Disponibilite du dernier rapport")

    catchup_status = get_latest_catchup_status()
    render_section("Rattrapage", "Recuperation d'un run manque", "Controle automatique lance 30 minutes apres connexion si aucun rapport n'existe encore pour aujourd'hui.")
    catchup_cols = st.columns(4)
    with catchup_cols[0]:
        render_metric_card("Mode rattrapage", display_status("ON"), "Actif via le demarrage a la connexion")
    with catchup_cols[1]:
        render_metric_card("Dernier controle", format_datetime_label(catchup_status.get("last_check")), "Dernier controle differe")
    with catchup_cols[2]:
        render_metric_card("Dernier resultat", display_status(catchup_status.get("status", "NEVER")), "Ignore, lance ou termine")
    with catchup_cols[3]:
        render_metric_card("Raison", catchup_status.get("reason", "Aucun log de rattrapage pour le moment"), "Pourquoi il a tourne ou non")
    if catchup_status.get("log_excerpt"):
        with st.expander("Log de rattrapage", expanded=False):
            st.text_area(
                "Sortie du rattrapage",
                value=catchup_status.get("log_excerpt", ""),
                height=180,
                key="catchup_log_output",
                disabled=True,
                label_visibility="collapsed",
            )

    render_section("Dernier run", "Resume du dernier run", "Principaux resultats du dernier run autonome.")
    summary_cols = st.columns(8)
    with summary_cols[0]:
        render_metric_card("Trouves bruts", str(latest_funnel.get("raw_found", latest_summary.get("raw_found", latest_summary.get("leads_found", 0)))), "Tous les candidats trouves")
    with summary_cols[1]:
        render_metric_card("Valides", str(latest_funnel.get("validated_leads", latest_summary.get("validated_leads", 0))), "Passent le filtre qualite")
    with summary_cols[2]:
        render_metric_card("Contactables", str(latest_funnel.get("contact_ready", latest_summary.get("contact_ready", 0))), "Prets pour l'envoi")
    with summary_cols[3]:
        render_metric_card("Sauvegardes", str(latest_funnel.get("leads_saved", latest_summary.get("leads_saved", 0))), "Prospects enregistres")
    with summary_cols[4]:
        render_metric_card("Emails envoyes", str(latest_funnel.get("email_sent", latest_summary.get("email_sent", 0))), "Canal email")
    with summary_cols[5]:
        render_metric_card("Landing envoyees", str(latest_funnel.get("landing_page_sent", latest_summary.get("landing_page_sent", 0))), "Offres landing page envoyees")
    with summary_cols[6]:
        render_metric_card("Sites envoyes", str(latest_funnel.get("website_sent", latest_summary.get("website_sent", 0))), "Offres site vitrine envoyees")
    with summary_cols[7]:
        render_metric_card("Echecs", str(latest_funnel.get("failed", latest_summary.get("failed", 0))), "Erreurs d'execution")

    render_section("Qualite des leads", "Trouves -> Gardes -> Envoyes", "Utilise l'entonnoir qualite et les raisons de rejet pour comprendre pourquoi des leads sortent du flux.")
    quality_cols = st.columns(8)
    with quality_cols[0]:
        render_metric_card("Rejetes", str(latest_funnel.get("validation_skipped", latest_summary.get("validation_skipped", 0))), "Rejetes avant envoi")
    with quality_cols[1]:
        render_metric_card("Selectionnes", str(latest_funnel.get("selected", latest_summary.get("selected", 0))), "Mis en file pour ce run")
    with quality_cols[2]:
        render_metric_card("Ignores", str(latest_funnel.get("skipped", latest_summary.get("skipped", 0))), "Aucun canal utilisable")
    with quality_cols[3]:
        render_metric_card("Plafond envoi", str(settings.SEND_MAX_PER_RUN), "Maximum par run")
    with quality_cols[4]:
        render_metric_card("Score mini", str(settings.AUTO_MODE_MIN_OPPORTUNITY_SCORE), "Seuil d'opportunite")
    with quality_cols[5]:
        render_metric_card("Debut d'activite", str(latest_funnel.get("early_stage_businesses", latest_summary.get("early_stage_businesses", 0))), "Business plus jeunes ou legers")
    with quality_cols[6]:
        render_metric_card("Offres landing", str(latest_funnel.get("landing_page_offers", latest_summary.get("landing_page_offers", 0))), "Angle landing page")
    with quality_cols[7]:
        render_metric_card("Fort potentiel", str(latest_funnel.get("high_opportunity_leads", latest_summary.get("high_opportunity_leads", 0))), "Meilleurs candidats conversion")

    validation_reasons = latest_report.get("validation_reasons", {}) if latest_report else {}
    if validation_reasons:
        reasons_df = pd.DataFrame(
            [{"Reason": reason, "Count": count} for reason, count in validation_reasons.items()]
        ).sort_values(by="Count", ascending=False)
        st.dataframe(reasons_df, hide_index=True, use_container_width=True)
    else:
        st.info("Aucun rejet de validation enregistre dans le dernier rapport.")

    render_section("Runs recents", "Historique d'execution", "Historique compact des derniers runs autonomes.")
    if report_rows:
        recent_runs_df = pd.DataFrame([
            {
                "Genere": row.get("generated_at"),
                "Declencheur": row.get("trigger"),
                "Planning": row.get("schedule_name"),
                "Brut": row.get("raw_found", row.get("leads_found", 0)),
                "Valides": row.get("validated_leads", 0),
                "Prets": row.get("contact_ready", 0),
                "Sauvegardes": row.get("leads_saved", 0),
                "Debut d'activite": row.get("early_stage_businesses", 0),
                "Fort potentiel": row.get("high_opportunity_leads", 0),
                "Offres landing": row.get("landing_page_offers", 0),
                "Offres site": row.get("website_offers", 0),
                "Emails": row.get("email_sent", 0),
                "Ignores": row.get("skipped", 0),
                "Echecs": row.get("failed", 0),
            }
            for row in report_rows[:10]
        ])
        st.dataframe(recent_runs_df, hide_index=True, use_container_width=True)
    else:
        st.info("Aucun run recent disponible pour le moment.")

    render_section("Rapports", "Rapports de run", "Ouvre les rapports JSON/CSV enregistres des runs autonomes.")
    if report_rows:
        report_cols = st.columns([1.4, 1, 1])
        with report_cols[0]:
            selected_report_path = st.selectbox("Fichier rapport", [row["path"] for row in report_rows], format_func=lambda path: Path(path).name)
        with report_cols[1]:
            selected_meta = next((row for row in report_rows if row["path"] == selected_report_path), {})
            st.caption(f"Declencheur : {selected_meta.get('trigger', '')}")
            st.caption(f"Genere : {selected_meta.get('generated_at', '')}")
        with report_cols[2]:
            if selected_report_path:
                st.caption(selected_report_path)
        report_payload = report_service.load_report(selected_report_path)
        if report_payload:
            report_summary = report_payload.get("summary", {})
            report_funnel = report_payload.get("quality_funnel", {})
            funnel_cols = st.columns(9)
            with funnel_cols[0]:
                render_metric_card("Brut", str(report_funnel.get("raw_found", report_summary.get("raw_found", report_summary.get("leads_found", 0)))), "Candidats trouves")
            with funnel_cols[1]:
                render_metric_card("Valides", str(report_funnel.get("validated_leads", report_summary.get("validated_leads", 0))), "Apres filtre qualite")
            with funnel_cols[2]:
                render_metric_card("Prets", str(report_funnel.get("contact_ready", report_summary.get("contact_ready", 0))), "Leads contactables")
            with funnel_cols[3]:
                render_metric_card("Sauvegardes", str(report_funnel.get("leads_saved", report_summary.get("leads_saved", 0))), "Enregistres en base")
            with funnel_cols[4]:
                render_metric_card("Selectionnes", str(report_funnel.get("selected", report_summary.get("selected", 0))), "Mis en file d'envoi")
            with funnel_cols[5]:
                render_metric_card("Emails envoyes", str(report_funnel.get("email_sent", report_summary.get("email_sent", 0))), "Envoyes sur ce run")
            with funnel_cols[6]:
                render_metric_card("Landing envoyees", str(report_funnel.get("landing_page_sent", report_summary.get("landing_page_sent", 0))), "Offres landing envoyees")
            with funnel_cols[7]:
                render_metric_card("Sites envoyes", str(report_funnel.get("website_sent", report_summary.get("website_sent", 0))), "Offres site vitrine envoyees")
            with funnel_cols[8]:
                render_metric_card("Fort potentiel", str(report_funnel.get("high_opportunity_leads", report_summary.get("high_opportunity_leads", 0))), "Meilleurs candidats")
            offer_cols = st.columns(3)
            with offer_cols[0]:
                render_metric_card("Debut d'activite", str(report_funnel.get("early_stage_businesses", report_summary.get("early_stage_businesses", 0))), "Business plus jeunes")
            with offer_cols[1]:
                render_metric_card("Offres landing", str(report_funnel.get("landing_page_offers", report_summary.get("landing_page_offers", 0))), "Type d'offre")
            with offer_cols[2]:
                render_metric_card("Offres site", str(report_funnel.get("website_offers", report_summary.get("website_offers", 0))), "Type d'offre")
            if report_payload.get("validation_reasons"):
                st.dataframe(
                    pd.DataFrame(
                        [{"Raison": reason, "Nombre": count} for reason, count in report_payload.get("validation_reasons", {}).items()]
                    ).sort_values(by="Nombre", ascending=False),
                    hide_index=True,
                    use_container_width=True,
                )
            if report_payload.get("failure_reasons"):
                st.json(report_payload.get("failure_reasons"))
            report_results_df = pd.DataFrame(report_summary.get("results", []))
            if not report_results_df.empty:
                st.dataframe(report_results_df, use_container_width=True)
    else:
        st.info("Aucun rapport enregistre pour le moment.")

    render_section("Logs", "Logs d'execution", "Fin du log applicatif pour un diagnostic rapide.")
    log_controls = st.columns([1.2, 2.8])
    with log_controls[0]:
        log_height = st.select_slider("Hauteur du log", options=[180, 260, 360, 520, 720], value=260, key="log_height")
    with log_controls[1]:
        st.caption("Reduis ou agrandis le panneau selon le niveau de detail dont tu as besoin.")
    log_text = read_log_tail()
    if log_text:
        st.text_area("Sortie du log", value=log_text, height=log_height, key="log_output", disabled=True, label_visibility="collapsed")
    else:
        st.info("Aucun log disponible pour le moment.")

    render_section("Resume leads", "Activite recente", "Derniers prospects contactes et resultat d'envoi.")
    lead_summary = pd.DataFrame(
        [
            {
                "Entreprise": prospect.business_name,
                "Localisation": prospect.location,
                "Offre": prospect.selected_offer_type or "",
                "Canal": prospect.selected_outreach_channel or "",
                "Statut outreach": display_status(prospect.outreach_status, ""),
                "Statut envoi": display_status(prospect.send_status, ""),
                "Reponse": display_status(prospect.response_status or "NO_RESPONSE"),
                "Derniere tentative": format_datetime_label(prospect.last_attempt_at),
                "Erreur": prospect.last_send_error or "",
            }
            for prospect in get_recent_outreach_prospects(limit=15)
        ]
    )
    if not lead_summary.empty:
        st.dataframe(lead_summary, hide_index=True, use_container_width=True)
    else:
        st.info("Aucune activite recente pour le moment.")

    render_section("Suivi business", "Reponses et performance des offres", "Observe quel angle d'offre genere des reponses et du potentiel commercial.")
    business_cols = st.columns(5)
    with business_cols[0]:
        render_metric_card("Total envoye", str(latest_business.get("sent", 0)), "Tous les envois suivis")
    with business_cols[1]:
        render_metric_card("Reponses", str(latest_business.get("responses", 0)), "Toute reponse recue")
    with business_cols[2]:
        render_metric_card("Interesses", str(latest_business.get("interested", 0)), "Signal commercial positif")
    with business_cols[3]:
        render_metric_card("Gagnes", str(latest_business.get("won", 0)), "Clients signes")
    with business_cols[4]:
        render_metric_card("Valeur potentielle", str(latest_business.get("potential_deal_value", 0.0)), "Pipeline actuel")

    by_offer = latest_business.get("by_offer", {}) if latest_business else {}
    if by_offer:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Offer": "Landing page",
                        "Envoyes": by_offer.get("landing_page", {}).get("sent", 0),
                        "Reponses": by_offer.get("landing_page", {}).get("responses", 0),
                        "Interesses": by_offer.get("landing_page", {}).get("interested", 0),
                        "Gagnes": by_offer.get("landing_page", {}).get("won", 0),
                        "Taux de reponse %": by_offer.get("landing_page", {}).get("reply_rate", 0.0),
                        "Valeur potentielle": by_offer.get("landing_page", {}).get("potential_deal_value", 0.0),
                    },
                    {
                        "Offer": "Site vitrine",
                        "Envoyes": by_offer.get("website", {}).get("sent", 0),
                        "Reponses": by_offer.get("website", {}).get("responses", 0),
                        "Interesses": by_offer.get("website", {}).get("interested", 0),
                        "Gagnes": by_offer.get("website", {}).get("won", 0),
                        "Taux de reponse %": by_offer.get("website", {}).get("reply_rate", 0.0),
                        "Valeur potentielle": by_offer.get("website", {}).get("potential_deal_value", 0.0),
                    },
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )

    render_section("Leads chauds", "Top leads chauds", "Vue directe des leads qui ont deja repondu, montre un interet ou converti.")
    warm_leads = pd.DataFrame(
        [
            {
                "Entreprise": prospect.business_name,
                "Localisation": prospect.location,
                "Offre": prospect.selected_offer_type or "",
                "Reponse": display_status(prospect.response_status or "NO_RESPONSE"),
                "Cycle de vie": prospect.status or "",
                "Valeur potentielle": float(prospect.potential_deal_value or 0.0),
                "Repondu le": format_datetime_label(prospect.replied_at),
                "Email": prospect.email or "",
            }
            for prospect in get_warm_prospects(limit=12)
        ]
    )
    if not warm_leads.empty:
        st.dataframe(warm_leads, hide_index=True, use_container_width=True)
    else:
        st.info("Aucun lead chaud pour le moment. Tu peux marquer les reponses depuis le mode debug.")

    render_section("Configuration", "Configuration simple", "Choisis les pays, les niches et le rythme d'envoi sans toucher aux reglages techniques.")
    configured_locations = split_csv_values(status.get("locations", settings.AUTO_MODE_LOCATIONS))
    configured_categories = split_csv_values(status.get("categories", settings.AUTO_MODE_CATEGORIES))
    current_time_slots = infer_time_slots(status.get("cron_expression", settings.AUTO_MODE_CRON)) or ["Matin", "Midi", "Soir"]
    default_countries = [country for country, cities in AUTO_ZONE_GROUPS.items() if any(city in configured_locations for city in cities)]
    if not default_countries:
        default_countries = ["France", "Suisse"]
    zone_options = []
    for country in default_countries:
        zone_options.extend(AUTO_ZONE_GROUPS.get(country, []))
    zone_options = list(dict.fromkeys(zone_options))
    selected_zone_defaults = [city for city in configured_locations if city in zone_options]
    extra_location_defaults = [city for city in configured_locations if city not in {item for cities in AUTO_ZONE_GROUPS.values() for item in cities}]
    selected_category_defaults = [category for category in configured_categories if category in AUTO_CATEGORY_OPTIONS]
    extra_category_defaults = [category for category in configured_categories if category not in AUTO_CATEGORY_OPTIONS]
    config_cols = st.columns([1.05, 1.15, 1.2, 0.7, 0.7])
    with config_cols[0]:
        auto_countries = st.multiselect("Pays", list(AUTO_ZONE_GROUPS.keys()), default=default_countries, key="auto_cfg_countries")
    with config_cols[1]:
        category_selection = st.multiselect("Categories", AUTO_CATEGORY_OPTIONS, default=selected_category_defaults or configured_categories[: min(len(configured_categories), len(AUTO_CATEGORY_OPTIONS))], key="auto_cfg_categories_select")
    with config_cols[2]:
        send_slots = st.multiselect("Moments d'envoi", list(TIME_SLOT_HOURS.keys()), default=current_time_slots, key="auto_cfg_time_slots", help="Chaque moment choisi declenche une vague automatique.")
    with config_cols[3]:
        auto_limit = st.number_input("Limite", min_value=1, max_value=50, value=int(status.get("limit", settings.AUTO_MODE_LIMIT)), key="auto_cfg_limit")
    with config_cols[4]:
        auto_language = st.selectbox("Langue", ["fr", "en"], index=0 if status.get("language", "fr") == "fr" else 1, key="auto_cfg_language")
    zone_pool = []
    for country in auto_countries:
        zone_pool.extend(AUTO_ZONE_GROUPS.get(country, []))
    zone_pool = list(dict.fromkeys(zone_pool))
    advanced_scope_cols = st.columns(2)
    with advanced_scope_cols[0]:
        location_selection = st.multiselect("Zones", zone_pool, default=[city for city in selected_zone_defaults if city in zone_pool], key="auto_cfg_locations_select", help="Selectionne les villes a cibler parmi les pays choisis.")
        extra_locations = st.text_input("Autres zones (optionnel)", value=",".join(extra_location_defaults), key="auto_cfg_locations_extra", help="Ajoute ici une ville hors liste, separee par des virgules si besoin.")
    with advanced_scope_cols[1]:
        extra_categories = st.text_input("Autres categories (optionnel)", value=",".join(extra_category_defaults), key="auto_cfg_categories_extra", help="Ajoute ici une categorie hors liste, separee par des virgules si besoin.")
    auto_locations = join_csv_values(location_selection, extra_locations)
    auto_categories = join_csv_values(category_selection, extra_categories)
    runtime_cols = st.columns([1, 1, 1.1])
    with runtime_cols[0]:
        send_max_per_run = st.number_input("Emails par vague", min_value=1, max_value=10, value=min(int(settings.SEND_MAX_PER_RUN), 3), key="auto_cfg_send_cap")
    with runtime_cols[1]:
        auto_enabled = st.checkbox("Mode auto actif", value=bool(status.get("enabled")), key="auto_cfg_enabled")
    with runtime_cols[2]:
        estimated_daily_volume = max(1, len(send_slots)) * int(send_max_per_run)
        render_key_value_card(
            "Rythme actif",
            [
                ("Moments choisis", ", ".join(send_slots) if send_slots else "Aucun"),
                ("Emails par vague", str(int(send_max_per_run))),
                ("Objectif par jour", str(estimated_daily_volume)),
                ("Planning calcule", build_daily_cron(send_slots)),
            ],
        )
    with st.expander("Reglages avances", expanded=False):
        advanced_cols = st.columns(3)
        with advanced_cols[0]:
            send_delay_seconds = st.number_input("Delai entre envois", min_value=0.0, max_value=30.0, value=float(settings.SEND_DELAY_SECONDS), step=0.5, key="auto_cfg_send_delay")
        with advanced_cols[1]:
            candidate_multiplier = st.number_input("Profondeur de recherche", min_value=2, max_value=40, value=int(settings.AUTO_MODE_CONTACT_CANDIDATE_MULTIPLIER), key="auto_cfg_candidate_multiplier")
        with advanced_cols[2]:
            min_opportunity_score = st.number_input("Score d'opportunite mini", min_value=0, max_value=100, value=int(settings.AUTO_MODE_MIN_OPPORTUNITY_SCORE), key="auto_cfg_min_score")
        st.caption("Le cron est maintenant calcule automatiquement a partir des moments d'envoi choisis.")
    config_action_cols = st.columns([1, 2])
    with config_action_cols[1]:
        if st.button("Enregistrer la configuration", key="save_automation_config", use_container_width=True):
            if not send_slots:
                st.error("Choisis au moins un moment d'envoi.")
                return
            auto_cron = build_daily_cron(send_slots)
            settings.AUTO_MODE_LOCATIONS = auto_locations
            settings.AUTO_MODE_CATEGORIES = auto_categories
            settings.AUTO_MODE_LIMIT = int(auto_limit)
            settings.AUTO_MODE_LANGUAGE = auto_language
            settings.AUTO_MODE_CRON = auto_cron
            settings.AUTO_MODE_ENABLED = auto_enabled
            settings.SEND_MAX_PER_RUN = int(send_max_per_run)
            settings.SEND_BATCH_SIZE = int(send_max_per_run)
            settings.SEND_DELAY_SECONDS = float(send_delay_seconds)
            settings.AUTO_MODE_CONTACT_CANDIDATE_MULTIPLIER = int(candidate_multiplier)
            settings.AUTO_MODE_MIN_OPPORTUNITY_SCORE = int(min_opportunity_score)
            scheduler_service.update_auto_schedule(
                cron_expression=auto_cron,
                locations=auto_locations,
                categories=auto_categories,
                limit=int(auto_limit),
                language=auto_language,
                enabled=auto_enabled,
            )
            persist_runtime_config(
                {
                    "AUTO_MODE_ENABLED": auto_enabled,
                    "AUTO_MODE_CRON": auto_cron,
                    "AUTO_MODE_LOCATIONS": auto_locations,
                    "AUTO_MODE_CATEGORIES": auto_categories,
                    "AUTO_MODE_LIMIT": int(auto_limit),
                    "AUTO_MODE_LANGUAGE": auto_language,
                    "SEND_MAX_PER_RUN": int(send_max_per_run),
                    "SEND_BATCH_SIZE": int(send_max_per_run),
                    "SEND_DELAY_SECONDS": float(send_delay_seconds),
                    "AUTO_MODE_CONTACT_CANDIDATE_MULTIPLIER": int(candidate_multiplier),
                    "AUTO_MODE_MIN_OPPORTUNITY_SCORE": int(min_opportunity_score),
                }
            )
            st.success("Configuration d'automatisation mise a jour.")
            st.rerun()

    if status.get("last_error"):
        st.warning(f"Derniere erreur : {status.get('last_error')}")


def render_manual_debug_mode():
    with st.expander("Debug / Mode manuel", expanded=False):
        render_section("Debug", "Outils manuels et diagnostic", "Outils secondaires pour les tests, apercus, envois cibles et diagnostics.")
        render_debug_tools()

        render_search_section()
        render_section("Diagnostic recherche", "Observabilite", "Requetes, providers et volumes bruts du dernier run de collecte.")
        render_search_diagnostics()

        render_section("Analyse lead", "Revue manuelle", "Outils d'inspection manuelle gardes pour le debug et les cas exceptionnels.")
        prospects, selected_prospects = render_lead_console()
        if not prospects:
            st.info("Aucun prospect trouve. Lance une recherche pour alimenter le pipeline.")
            return

        export_cols = st.columns(2)
        with export_cols[0]:
            if st.button("Exporter CSV", key="export_csv_manual", use_container_width=True):
                ExportService().export_leads("csv")
                st.success("Export CSV cree.")
        with export_cols[1]:
            if st.button("Exporter Excel", key="export_excel_manual", use_container_width=True):
                ExportService().export_leads("xlsx")
                st.success("Export Excel cree.")

        render_section("Identite expediteur", "KAH.DIGITAL Outreach", "Identite expediteur pro, signature et reglage maquette utilises partout.")
        render_sender_identity_preview()

        render_section("Apercu", "Exemples d'apercu manuel", "Previsualise un lead, inspecte les contenus generes et controle la qualite du message.")
        preview_pool = selected_prospects or prospects
        prospect = resolve_preview_prospect(preview_pool)
        render_prospect_summary(prospect, f"preview_{prospect.id}")
        notes_data = parse_notes(prospect.notes)
        lang = st.selectbox("Langue d'apercu", ["fr", "en"], index=0 if (prospect.email_language or "fr") == "fr" else 1)
        preview_assets = ["Email principal", "Email court", "Relance J+2", "Relance J+5", "Relance finale J+10"]
        outreach_asset = st.selectbox("Contenu a previsualiser", preview_assets)
        subject, body, html_body = build_outreach_preview(prospect, notes_data, lang, outreach_asset)

        preview_cols = st.columns([1, 1.2])
        with preview_cols[0]:
            render_key_value_card("Contexte de l'exemple", [
                ("Langue", prospect.email_language or "N/A"),
                ("Prix", format_price_range(prospect.estimated_price_min, prospect.estimated_price_max, prospect.country)),
                ("Canal recommande", notes_data.get("recommended_channel", "N/A")),
                ("Offre selectionnee", prospect.selected_offer_type or "N/A"),
                ("Outreach selectionnee", prospect.selected_outreach_channel or "N/A"),
                ("Statut outreach", display_status(prospect.outreach_status, "N/A")),
                ("Statut reponse", display_status(prospect.response_status or "NO_RESPONSE")),
                ("Deal potentiel", str(prospect.potential_deal_value or 0.0)),
                ("Destinataire", prospect.email or prospect.phone or "Indisponible"),
                ("Statut envoi", display_status(get_send_indicator(prospect.send_status))),
                ("Derniere erreur", prospect.last_send_error or "Aucune"),
            ])
        with preview_cols[1]:
            st.text_input("Sujet", value=subject, key=f"subject_{prospect.id}")
            st.text_area("Message", value=body, height=260, key=f"body_{prospect.id}")
            if html_body:
                with st.expander("Apercu HTML", expanded=False):
                    components.html(html_body, height=520, scrolling=True)
        render_section("Envoi manuel", "Controles d'envoi cible", "Les actions d'envoi manuel restent disponibles ici pour les tests isoles.")
        render_send_panel(prospects, selected_prospects, prospect, subject, body, html_body)

        if st.session_state.get("last_send_summary"):
            summary = st.session_state["last_send_summary"]
            st.caption(f"Dernier envoi manuel : selectionnes={summary.get('selected', 0)} | envoyes={summary.get('sent', 0)} | echecs={summary.get('failed', 0)} | ignores={summary.get('skipped', 0)} | simulation={summary.get('simulated', 0)}")
            results_df = pd.DataFrame(summary.get("results", []))
            if not results_df.empty:
                st.dataframe(results_df, use_container_width=True)


def render_debug_tools():
    scheduler_service = SchedulerService()
    status = scheduler_service.get_auto_schedule_status()
    lead_service = LeadService()
    debug_cols = st.columns([1, 1, 1.2])
    with debug_cols[0]:
        debug_run_dry = st.checkbox("Declenchement manuel en simulation", value=True, key="debug_run_dry")
    with debug_cols[1]:
        test_to_self = st.checkbox("Test d'envoi vers moi", value=True, key="debug_test_to_self")
    with debug_cols[2]:
        st.caption("Utilise ces outils pour des verifications ponctuelles. Le mode autonome reste le flux principal.")

    button_cols = st.columns(2)
    with button_cols[0]:
        if st.button("Lancer le flux auto maintenant", key="run_auto_now_debug", use_container_width=True):
            summary = scheduler_service.run_auto_outreach_now(simulate=debug_run_dry)
            st.session_state["last_auto_outreach_summary"] = summary
            st.success(
                f"Run manuel termine. leads_found={summary.get('leads_found', 0)} "
                f"email_sent={summary.get('email_sent', 0)} landing_sent={summary.get('landing_page_sent', 0)} "
                f"website_sent={summary.get('website_sent', 0)} "
                f"skipped={summary.get('skipped', 0)} failed={summary.get('failed', 0)}"
            )
    with button_cols[1]:
        if st.button("M'envoyer un email test", key="send_test_to_self_debug", use_container_width=True):
            prospects = get_prospects(has_email=True, send_status=None)
            if not prospects:
                st.warning("Aucun lead avec email n'est disponible pour un auto-test.")
            else:
                summary = lead_service.send_emails(
                    selected_ids=[prospects[0].id],
                    limit=1,
                    only_not_sent=False,
                    test_to=settings.PROFESSIONAL_EMAIL if test_to_self else None,
                    simulate=debug_run_dry,
                    allow_resend=True,
                )
                st.session_state["last_send_summary"] = summary
                st.success(
                    f"Envoi test termine. sent={summary.get('sent', 0)} failed={summary.get('failed', 0)} "
                    f"skipped={summary.get('skipped', 0)} simulated={summary.get('simulated', 0)}"
                )

    render_key_value_card("Diagnostic", [
        ("Scheduler actif", display_bool(status.get("scheduler_running"))),
        ("Automatisation active", display_bool(status.get("enabled"))),
        ("Prochain run", format_datetime_label(status.get("next_run"))),
        ("Dernier statut", display_status(status.get("last_status", "IDLE"))),
        ("Mode email-only", display_bool(settings.EMAIL_ONLY_OUTREACH)),
        ("SMTP host", settings.SMTP_HOST or "Manquant"),
        ("Plafond d'envoi / run", str(settings.SEND_MAX_PER_RUN)),
    ])
    for warning in settings.get_smtp_identity_warnings():
        st.warning(warning)


def render_search_section():
    render_section("Recherche", "Collecte de leads", "Lance des recherches multi-marches tout en gardant le pipeline existant intact.")
    search_col1, search_col2 = st.columns([1.25, 1])
    with search_col1:
        locations = st.multiselect("Zones", SEARCH_LOCATIONS, default=["Toulouse", "Geneva", "New York"])
        categories = st.multiselect("Categories", SEARCH_CATEGORIES, default=["coiffeur"])
    with search_col2:
        limit = st.number_input("Prospects par zone", min_value=1, max_value=50, value=10)
        language = st.selectbox("Langue de repli", ["fr", "en"], index=0)
        with st.expander("Profondeur de recherche", expanded=False):
            queries_per_combo = st.slider("Requetes par couple zone/categorie", 3, 20, settings.SEARCH_QUERIES_PER_COMBO)
            max_raw_candidates = st.slider("Maximum de candidats bruts", 10, 60, settings.SEARCH_MAX_RAW_CANDIDATES, step=2)
            fallback_enabled = st.checkbox("Activer le fallback provider", value=settings.SEARCH_FALLBACK_ENABLED)
            broaden_if_empty = st.checkbox("Elargir la recherche si vide", value=settings.SEARCH_BROADEN_IF_EMPTY)
            reset_before_collect = st.checkbox("Vider les anciens leads avant collecte", value=settings.SEARCH_RESET_BEFORE_COLLECT)
    action_col1, action_col2, action_col3, _ = st.columns([1, 1, 1.2, 1.4])
    with action_col1:
        collect_clicked = st.button("Collecter les leads", key="collect_leads_manual", type="primary", use_container_width=True)
    with action_col2:
        st.button("Generer", key="generate_disabled_placeholder", disabled=True, use_container_width=True)
    with action_col3:
        reset_clicked = st.button("Reinitialiser les leads / Vider la base", key="reset_leads_database", use_container_width=True)
    if reset_clicked:
        deleted = LeadService().reset_leads(clear_search_history=True)
        st.success(f"Base videe. {deleted} leads supprimes.")
        st.rerun()
    if collect_clicked:
        if not (locations and categories):
            st.error("Selectionne au moins une zone et une categorie.")
            return
        settings.SEARCH_QUERIES_PER_COMBO = queries_per_combo
        settings.SEARCH_MAX_RAW_CANDIDATES = max_raw_candidates
        settings.SEARCH_FALLBACK_ENABLED = fallback_enabled
        settings.SEARCH_BROADEN_IF_EMPTY = broaden_if_empty
        settings.SEARCH_RESET_BEFORE_COLLECT = reset_before_collect
        if reset_before_collect:
            LeadService().reset_leads(clear_search_history=True)
        saved_count = asyncio.run(LeadService().collect_leads(locations, categories, limit, language))
        st.success(f"Collecte terminee. {saved_count} nouveaux leads sauvegardes.")
        st.rerun()


def render_lead_console():
    cols = st.columns(6)
    with cols[0]:
        filter_country = st.selectbox("Pays", [FILTER_ALL] + sorted(set(get_countries())))
    with cols[1]:
        filter_location = st.selectbox("Zone", [FILTER_ALL] + sorted(set(get_locations())))
    with cols[2]:
        filter_category = st.selectbox("Categorie", [FILTER_ALL] + sorted(set(get_categories())))
    with cols[3]:
        filter_status = st.selectbox("Cycle de vie", [FILTER_ALL, "NEW", "REVIEWED", "MAQUETTE_READY", "CONTACTED", "WON", "LOST"], format_func=lambda x: FILTER_ALL if x == FILTER_ALL else display_status(x))
    with cols[4]:
        filter_email = st.selectbox("Email disponible", [FILTER_ALL, "Oui", "Non"])
    with cols[5]:
        filter_send_status = st.selectbox("Statut d'envoi", [FILTER_ALL, "NOT_SENT", "FAILED", "SKIPPED", "SENT"], format_func=lambda x: FILTER_ALL if x == FILTER_ALL else display_status(x))
    extra_cols = st.columns(4)
    with extra_cols[0]:
        filter_only_not_sent = st.checkbox("Seulement NON ENVOYE", value=False)
    with extra_cols[1]:
        filter_min_priority = st.slider("Priorite minimale", 0, 200, 0)
    with extra_cols[2]:
        filter_phone_available = st.checkbox("Telephone disponible", value=False)
    with extra_cols[3]:
        filter_contact_form_available = st.checkbox("Formulaire disponible", value=False)
    channel_cols = st.columns(2)
    with channel_cols[0]:
        filter_social_available = st.checkbox("Reseaux sociaux disponibles", value=False)
    with channel_cols[1]:
        filter_recommended_channel = st.selectbox("Canal recommande", [FILTER_ALL, "email", "phone", "contact_form", "instagram", "facebook", "unavailable"], format_func=lambda x: FILTER_ALL if x == FILTER_ALL else display_channel(x))
    prospects = get_prospects(
        country=filter_country if filter_country != FILTER_ALL else None,
        location=filter_location if filter_location != FILTER_ALL else None,
        category=filter_category if filter_category != FILTER_ALL else None,
        status=filter_status if filter_status != FILTER_ALL else None,
        has_email=(filter_email == "Oui") if filter_email != FILTER_ALL else None,
        send_status="NOT_SENT" if filter_only_not_sent else (filter_send_status if filter_send_status != FILTER_ALL else None),
        min_priority=filter_min_priority if filter_min_priority > 0 else None,
    )
    prospects = apply_channel_filters(
        prospects,
        phone_available=filter_phone_available,
        contact_form_available=filter_contact_form_available,
        social_available=filter_social_available,
        recommended_channel=filter_recommended_channel if filter_recommended_channel != FILTER_ALL else None,
    )
    if not prospects:
        return [], []
    select_cols = st.columns(2)
    with select_cols[0]:
        if st.button("Selectionner les leads avec email", key="select_leads_with_email", use_container_width=True):
            st.session_state["selected_lead_ids"] = [prospect.id for prospect in prospects if prospect.email]
            st.rerun()
    with select_cols[1]:
        if st.button("Vider la selection", key="clear_selected_leads", use_container_width=True):
            st.session_state["selected_lead_ids"] = []
            st.rerun()
    selected_ids = set(st.session_state.get("selected_lead_ids", []))
    table = pd.DataFrame([{
        "Selectionner": prospect.id in selected_ids,
        "Entreprise": prospect.business_name,
        "Pays": prospect.country,
        "Zone": prospect.location,
        "Categorie": prospect.category,
        "Priorite": prospect.priority_score or 0,
        "Email": prospect.email or "",
        "Telephone": prospect.phone or "",
        "Canal recommande": display_channel(parse_notes(prospect.notes).get("recommended_channel", "unavailable")),
        "Canal outreach": display_channel(prospect.selected_outreach_channel, ""),
        "Statut outreach": display_status(prospect.outreach_status, ""),
        "Formulaire": parse_notes(prospect.notes).get("contact_form_url", ""),
        "Instagram": parse_notes(prospect.notes).get("instagram_url", ""),
        "Facebook": parse_notes(prospect.notes).get("facebook_url", ""),
        "Statut envoi": display_status(get_send_indicator(prospect.send_status)),
        "Premier envoi": format_datetime_label(prospect.first_sent_at),
        "Derniere tentative": format_datetime_label(prospect.last_attempt_at),
        "Tentatives": int(prospect.send_attempts or 0),
        "Derniere erreur": prospect.last_send_error or "",
        "URL maquette": prospect.mockup_url or "",
    } for prospect in prospects])
    edited = st.data_editor(table, hide_index=True, use_container_width=True, key="lead_selection_table", column_config={"Selectionner": st.column_config.CheckboxColumn("Selectionner"), "Priorite": st.column_config.NumberColumn("Priorite", format="%.2f")}, disabled=["Entreprise", "Pays", "Zone", "Categorie", "Priorite", "Email", "Telephone", "Canal recommande", "Canal outreach", "Statut outreach", "Formulaire", "Instagram", "Facebook", "Statut envoi", "Premier envoi", "Derniere tentative", "Tentatives", "Derniere erreur", "URL maquette"])
    selected_rows = [index for index, row in edited.iterrows() if row["Selectionner"]]
    st.session_state["selected_lead_ids"] = [prospects[index].id for index in selected_rows]
    selected_prospects = [prospect for prospect in prospects if prospect.id in st.session_state["selected_lead_ids"]]
    st.caption(f"Leads filtres : {len(prospects)} | Leads selectionnes : {len(selected_prospects)} | Leads avec email valide : {sum(1 for prospect in prospects if prospect.email)}")
    return prospects, selected_prospects


def render_send_panel(prospects, selected_prospects, current_prospect, current_subject, current_body, current_html_body):
    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL or not settings.SMTP_PASSWORD:
        st.warning("La configuration SMTP semble incomplete. L'envoi peut echouer tant que le host, l'email expediteur et le mot de passe ne sont pas configures.")
    for warning in settings.get_smtp_identity_warnings():
        st.warning(warning)
    cols = st.columns(5)
    with cols[0]:
        auto_send_enabled = st.toggle("Envoi auto actif", value=settings.AUTO_SEND_ENABLED)
    with cols[1]:
        send_only_not_sent = st.checkbox("Seulement NON ENVOYE", value=True)
    with cols[2]:
        send_only_with_email = st.checkbox("Seulement les leads avec email", value=True)
    with cols[3]:
        send_allow_resend = st.checkbox("Autoriser le renvoi", value=settings.SEND_ALLOW_RESEND)
    with cols[4]:
        test_mode_enabled = st.checkbox("Mode test", value=True)
    opt_cols = st.columns(4)
    with opt_cols[0]:
        send_status_filter = st.selectbox("Filtre statut d'envoi", [FILTER_ALL, "NOT_SENT", "FAILED", "SKIPPED", "SENT"], index=1, format_func=lambda x: FILTER_ALL if x == FILTER_ALL else display_status(x))
    with opt_cols[1]:
        min_send_priority = st.slider("Priorite mini pour envoyer", 0, 200, 70)
    with opt_cols[2]:
        send_limit = st.number_input("Max emails pour cette action", min_value=1, max_value=50, value=min(settings.SEND_MAX_PER_RUN, 5))
    with opt_cols[3]:
        confirm_bulk_send = st.checkbox("Confirmer l'envoi en lot", value=False)
    test_to = st.text_input("Destinataire de test", value=settings.PROFESSIONAL_EMAIL if test_mode_enabled else "", disabled=not test_mode_enabled)
    send_pool = selected_prospects or prospects
    send_candidates = [candidate for candidate in send_pool if (candidate.email or not send_only_with_email)]
    if send_status_filter != FILTER_ALL:
        send_candidates = [candidate for candidate in send_candidates if get_send_indicator(candidate.send_status) == send_status_filter]
    if send_only_not_sent:
        send_candidates = [candidate for candidate in send_candidates if get_send_indicator(candidate.send_status) == "NOT_SENT"]
    send_candidates = [candidate for candidate in send_candidates if (candidate.priority_score or 0) >= min_send_priority]
    selected_ids = set(st.session_state.get("selected_lead_ids", []))
    selected_send_ids = [candidate.id for candidate in send_candidates if candidate.id in selected_ids]
    top_send_ids = [candidate.id for candidate in send_candidates[:send_limit]]
    valid_email_send_ids = [candidate.id for candidate in send_candidates if candidate.email][:send_limit]
    eligible_with_email = sum(1 for candidate in send_candidates if candidate.email)
    render_key_value_card("Apercu envoi en lot", [("Scope actuel", "Leads selectionnes" if selected_prospects else "Leads filtres"), ("Leads dans le scope", str(len(send_pool))), ("Eligibles maintenant", str(len(send_candidates))), ("Avec email valide", str(eligible_with_email)), ("Selectionnes pour envoi", str(len(selected_send_ids))), ("Maximum de l'action", str(send_limit)), ("Destinataire de test", test_to if test_mode_enabled and test_to else "Desactive")])
    render_key_value_card("Apercu de l'envoi courant", [("Entreprise", current_prospect.business_name), ("Expediteur", get_business_identity().sender_display_name), ("Destinataire", test_to if test_mode_enabled and test_to else (current_prospect.email or "Pas d'email")), ("Sujet", current_subject or "Non genere"), ("Langue", current_prospect.email_language or "N/A"), ("Statut d'envoi", display_status(get_send_indicator(current_prospect.send_status))), ("URL maquette", current_prospect.mockup_url or "Indisponible")])
    with st.expander("Apercu du message avant envoi", expanded=False):
        st.text_area("Apercu", value=current_body or "Corps d'email non genere", height=220, key=f"send_preview_{current_prospect.id}")
        if current_html_body:
            with st.expander("Apercu HTML", expanded=False):
                components.html(current_html_body, height=520, scrolling=True)
        render_copy_text_button(f"A: {test_to if test_mode_enabled and test_to else (current_prospect.email or '')}\nSujet: {current_subject or ''}\n\n{current_body or ''}", f"copy_preview_{current_prospect.id}", label="Copier l'email")
    if send_only_with_email and not eligible_with_email:
        st.warning("Aucun email valide extrait n'est disponible dans le scope actuel.")
    settings.AUTO_SEND_ENABLED = auto_send_enabled
    btns = st.columns(5)
    with btns[0]:
        send_selected_clicked = st.button("Envoyer les emails selectionnes", key="send_selected_emails_bulk", use_container_width=True)
    with btns[1]:
        send_top_clicked = st.button("Envoyer les emails prioritaires", key="send_top_priority_emails", use_container_width=True)
    with btns[2]:
        send_test_clicked = st.button("M'envoyer un email test", key="send_test_to_self_panel", use_container_width=True)
    with btns[3]:
        valid_email_clicked = st.button("Envoyer seulement les leads avec email valide", key="send_valid_email_only", use_container_width=True)
    with btns[4]:
        simulate_clicked = st.button("Simuler l'envoi", key="simulate_send_panel", use_container_width=True)
    if valid_email_clicked:
        if not valid_email_send_ids:
            st.warning("Aucun lead eligible avec email valide ne correspond aux filtres.")
        elif len(valid_email_send_ids) > 1 and not confirm_bulk_send:
            st.warning("Confirme l'envoi en lot avant d'envoyer plusieurs emails.")
        else:
            execute_and_rerender("send_valid_email", valid_email_send_ids, min(send_limit, len(valid_email_send_ids)), send_only_not_sent, test_to if test_mode_enabled and test_to else None, False, send_allow_resend)
    if send_selected_clicked:
        if not selected_send_ids:
            st.warning("Selectionne au moins un lead eligible a envoyer.")
        elif len(selected_send_ids) > 1 and not confirm_bulk_send:
            st.warning("Confirme l'envoi en lot avant d'envoyer plusieurs emails.")
        else:
            execute_and_rerender("send_selected", selected_send_ids, send_limit, send_only_not_sent, test_to if test_mode_enabled and test_to else None, False, send_allow_resend)
    if send_top_clicked:
        if not top_send_ids:
            st.warning("Aucun lead eligible ne correspond aux filtres actuels.")
        elif len(top_send_ids) > 1 and not confirm_bulk_send:
            st.warning("Confirme l'envoi en lot avant d'envoyer plusieurs emails.")
        else:
            execute_and_rerender("send_top_priority", top_send_ids, send_limit, send_only_not_sent, test_to if test_mode_enabled and test_to else None, False, send_allow_resend)
    if send_test_clicked:
        execute_and_rerender("send_single_test", [current_prospect.id], 1, False, test_to if test_mode_enabled and test_to else settings.PROFESSIONAL_EMAIL, False, True)
    if simulate_clicked:
        simulation_ids = selected_send_ids or top_send_ids
        if not simulation_ids:
            st.warning("Aucun lead eligible n'est disponible pour la simulation.")
        else:
            execute_and_rerender("simulate_send", simulation_ids, min(send_limit, len(simulation_ids)), send_only_not_sent, test_to if test_mode_enabled and test_to else None, True, send_allow_resend)
    render_section("Actions selectionnees", "Controles par lead", "Previsualise, envoie, ignore et mets a jour l'etat directement sur les leads.")
    for prospect in (selected_prospects or [current_prospect])[:8]:
        notes = parse_notes(prospect.notes)
        subject, body, _ = build_outreach_preview(prospect, notes, prospect.email_language or "fr", "Email principal")
        with st.expander(f"{prospect.business_name} | {prospect.location} | {display_status(get_send_indicator(prospect.send_status))}", expanded=(prospect.id == current_prospect.id)):
            render_key_value_card("Carte de livraison du lead", [("Destinataire", prospect.email or "Pas d'email"), ("Canal de repli", display_channel(notes.get("recommended_channel", "unavailable"))), ("Telephone", prospect.phone or "N/A"), ("Formulaire", notes.get("contact_form_url", "N/A")), ("Instagram", notes.get("instagram_url", "N/A")), ("Facebook", notes.get("facebook_url", "N/A")), ("Sujet", subject or "Non genere"), ("Premier envoi", format_datetime_label(prospect.first_sent_at)), ("Derniere tentative", format_datetime_label(prospect.last_attempt_at)), ("Tentatives", str(prospect.send_attempts or 0)), ("Derniere erreur", prospect.last_send_error or "Aucune")])
            tracking_cols = st.columns([1.1, 1.1, 1.1, 1.1, 1.6])
            with tracking_cols[0]:
                if st.button("Marquer repondu", key=f"reply_{prospect.id}", use_container_width=True):
                    if update_prospect_from_ui(prospect.id, response_status="REPLIED"):
                        st.success("Lead marque comme ayant repondu.")
                        st.rerun()
            with tracking_cols[1]:
                if st.button("Marquer interesse", key=f"interested_{prospect.id}", use_container_width=True):
                    if update_prospect_from_ui(prospect.id, response_status="INTERESTED"):
                        st.success("Lead marque comme interesse.")
                        st.rerun()
            with tracking_cols[2]:
                if st.button("Marquer gagne", key=f"won_{prospect.id}", use_container_width=True):
                    if update_prospect_from_ui(prospect.id, response_status="WON", status="WON"):
                        st.success("Lead marque comme gagne.")
                        st.rerun()
            with tracking_cols[3]:
                if st.button("Marquer perdu", key=f"lost_{prospect.id}", use_container_width=True):
                    if update_prospect_from_ui(prospect.id, response_status="LOST", status="LOST"):
                        st.success("Lead marque comme perdu.")
                        st.rerun()
            with tracking_cols[4]:
                potential_value = st.number_input("Valeur potentielle du deal", min_value=0.0, value=float(prospect.potential_deal_value or 0.0), step=50.0, key=f"potential_value_{prospect.id}")
                if st.button("Enregistrer la valeur", key=f"save_value_{prospect.id}", use_container_width=True):
                    if update_prospect_from_ui(prospect.id, potential_deal_value=float(potential_value)):
                        st.success("Valeur potentielle mise a jour.")
                        st.rerun()
            if not prospect.email:
                st.info(f"Envoi desactive car aucun email n'a ete extrait. Repli recommande : {display_channel(notes.get('recommended_channel', 'unavailable'), 'suivi manuel')}.")
            action_cols = st.columns(6)
            with action_cols[0]:
                send_now = st.button("Envoyer maintenant", key=f"send_now_{prospect.id}", use_container_width=True, disabled=not bool(prospect.email))
            with action_cols[1]:
                preview_btn = st.button("Previsualiser l'email", key=f"preview_email_{prospect.id}", use_container_width=True)
            with action_cols[2]:
                render_copy_text_button(f"A: {prospect.email or ''}\nSujet: {subject or ''}\n\n{body or ''}", f"copy_email_{prospect.id}", label="Copier l'email")
            with action_cols[3]:
                skip_btn = st.button("Ignorer", key=f"skip_{prospect.id}", use_container_width=True)
            with action_cols[4]:
                review_btn = st.button("Marquer revise", key=f"review_{prospect.id}", use_container_width=True)
            with action_cols[5]:
                contact_btn = st.button("Marquer contacte", key=f"contact_{prospect.id}", use_container_width=True)
            st.caption("Mode email-only actif : aucun canal alternatif n'est propose dans le produit actuel.")
            if preview_btn:
                st.session_state["preview_prospect_id"] = prospect.id
                st.rerun()
            if send_now:
                execute_and_rerender("send_single_now", [prospect.id], 1, send_only_not_sent, test_to if test_mode_enabled and test_to else None, False, send_allow_resend)
            if skip_btn and update_prospect_from_ui(prospect.id, send_status="SKIPPED", last_send_error="ui_skipped"):
                st.success("Lead marque comme ignore.")
                st.rerun()
            if review_btn and update_prospect_from_ui(prospect.id, status="REVIEWED"):
                st.success("Lead marque comme revise.")
                st.rerun()
            if contact_btn and update_prospect_from_ui(prospect.id, status="CONTACTED"):
                st.success("Lead marque comme contacte.")
                st.rerun()


def execute_and_rerender(action_name, selected_ids, limit, only_not_sent, test_to, simulate, allow_resend):
    summary = execute_ui_send_action(action_name, selected_ids=selected_ids, limit=limit, only_not_sent=only_not_sent, test_to=test_to, simulate=simulate, allow_resend=allow_resend)
    st.success(f"Action terminee. envoyes={summary.get('sent', 0)} echecs={summary.get('failed', 0)} ignores={summary.get('skipped', 0)} simulation={summary.get('simulated', 0)}")
    st.rerun()


def render_sidebar():
    render_sidebar_brand()
    st.sidebar.markdown(f"""<div class="kah-card"><div class="kah-section-label">Systeme de statut</div><div class="kah-inline-badges">{status_badge_html("deployed")}{status_badge_html("pending")}{status_badge_html("failed")}</div><div class="kah-inline-badges" style="margin-top:0.7rem;">{priority_badge_html(125)}{priority_badge_html(90)}{priority_badge_html(45)}</div></div>""", unsafe_allow_html=True)
    st.sidebar.markdown("""<div class="kah-card"><div class="kah-section-label">Notes de marque</div><div style="color:var(--kah-muted); font-size:0.9rem; line-height:1.65;">Systeme visuel noir et or inspire de KAH.DIGITAL et KAH-PROD. L'interface doit ressembler a un poste de pilotage premium de studio digital, pas a un back-office generique.</div></div>""", unsafe_allow_html=True)


def render_prospect_summary(prospect, key_prefix: str):
    notes = parse_notes(prospect.notes)
    badges = "".join([badge_html(prospect.country or "N/A", "neutral"), badge_html(prospect.currency or "N/A", "neutral"), status_badge_html(get_mockup_indicator(prospect.mockup_status)), priority_badge_html(prospect.priority_score)])
    st.markdown(f'<div class="kah-inline-badges">{badges}</div>', unsafe_allow_html=True)
    cols = st.columns(2)
    with cols[0]:
        render_key_value_card("Profil marche", [("Pays", f"{prospect.country} - {get_country_display_name(prospect.country)}"), ("Zone", prospect.location), ("Categorie", prospect.category), ("Site web", prospect.website or "N/A"), ("Priorite", str(round(prospect.priority_score or 0, 2))), ("Score nouveau business", str(round(prospect.new_business_score or 0, 2))), ("Type de cible", prospect.target_type or "N/A"), ("Statut d'envoi", display_status(get_send_indicator(prospect.send_status)))])
    with cols[1]:
        render_key_value_card("Preparation contact", [("Email", prospect.email or "N/A"), ("Telephone", prospect.phone or "N/A"), ("Canal recommande", display_channel(notes.get("recommended_channel", "unavailable"))), ("Offre selectionnee", display_offer(prospect.selected_offer_type)), ("Outreach selectionnee", display_channel(prospect.selected_outreach_channel, "N/A")), ("Statut outreach", display_status(prospect.outreach_status, "N/A")), ("Statut reponse", display_status(prospect.response_status or "NO_RESPONSE")), ("Deal potentiel", str(prospect.potential_deal_value or 0.0)), ("Formulaire", notes.get("contact_form_url", "N/A")), ("Instagram", notes.get("instagram_url", "N/A")), ("Social-first", display_bool(prospect.social_first_business)), ("Pages", str(prospect.website_page_count or 0)), ("Systeme de reservation", display_bool(prospect.has_booking_system)), ("Base SEO", display_bool(prospect.has_seo_foundation)), ("UI moderne", display_bool(prospect.has_modern_ui)), ("Langue", prospect.email_language or "N/A"), ("Prix estime", format_price_range(prospect.estimated_price_min, prospect.estimated_price_max, prospect.country)), ("Maquette", display_mockup_status(get_mockup_indicator(prospect.mockup_status))), ("Tentatives d'envoi", str(prospect.send_attempts or 0))])
    render_mockup_actions(prospect, key_prefix)


def render_sender_identity_preview():
    identity = get_business_identity()
    label_map = {
        "Business": "Entreprise",
        "Sender": "Expediteur",
        "Email": "Email",
        "Phone": "Telephone",
        "Website": "Site web",
        "Portfolio": "Portfolio",
        "Mockup quality": "Qualite maquette",
    }
    for warning in settings.get_smtp_identity_warnings():
        st.warning(warning)
    cols = st.columns([1, 1.1])
    with cols[0]:
        render_key_value_card("Profil expediteur", [(label_map.get(label, label), value) for label, value in get_sender_preview_rows()])
    with cols[1]:
        render_key_value_card("Signature email", [("Nom affiche", identity.sender_display_name), ("Label", identity.signature_label), ("Email", identity.professional_email), ("Telephone", identity.professional_phone), ("Site web", identity.website)])
        with st.expander("Apercu signature", expanded=False):
            st.code(get_text_signature("fr"), language="text")


def render_search_diagnostics():
    latest_run = get_latest_search_run()
    if not latest_run or not latest_run.diagnostics_json:
        st.info("Aucun diagnostic de recherche disponible pour le moment.")
        return
    try:
        diagnostics = json.loads(latest_run.diagnostics_json)
    except json.JSONDecodeError:
        st.warning("Les diagnostics de recherche sont presents mais n'ont pas pu etre lus.")
        return
    st.caption(f"Dernier run : {latest_run.locations} | {latest_run.categories} | requetes/combo={settings.SEARCH_QUERIES_PER_COMBO} | cible brute={settings.SEARCH_MAX_RAW_CANDIDATES} | fallback={settings.SEARCH_FALLBACK_ENABLED} | elargissement={settings.SEARCH_BROADEN_IF_EMPTY}")
    for item in diagnostics:
        title = f"{item.get('location')} | {item.get('requested_category')} | {item.get('country')}"
        with st.expander(title):
            cols = st.columns(2)
            with cols[0]:
                render_key_value_card("Plan de recherche", [("Zone normalisee", item.get("normalized_location", "")), ("Pays", item.get("country", "")), ("Langue", item.get("language", "")), ("Termes categorie", ", ".join(item.get("translated_terms", [])[:4])), ("Tags OSM", ", ".join(f'{tag.get("key")}={tag.get("value")}' for tag in item.get("osm_tags", [])[:3])), ("Candidats bruts", str(item.get("raw_candidates", 0)))])
            with cols[1]:
                render_key_value_card("Resultat", [("Traites", str(item.get("processed_candidates", 0))), ("Valides gardes", str(item.get("valid_prospects_kept", 0))), ("Rejetes", str(item.get("rejected_after_filter", 0))), ("Alias", ", ".join(item.get("location_aliases", [])[:4])), ("Requetes", str(len(item.get("queries", []))))])
            st.markdown("**Requetes generees**")
            st.code("\n".join(item.get("queries", [])), language="text")
            if item.get("broadened_queries"):
                st.markdown("**Requetes de fallback elargies**")
                st.code("\n".join(item.get("broadened_queries", [])), language="text")
            if item.get("generic_queries"):
                st.markdown("**Requetes de fallback generiques**")
                st.code("\n".join(item.get("generic_queries", [])), language="text")
            for provider_diag in item.get("providers", []):
                provider_title = f"{provider_diag.get('provider')} | kept={provider_diag.get('kept_candidates', 0)} | raw={provider_diag.get('raw_results', 0)}"
                st.markdown(f"**{provider_title}**")
                if provider_diag.get("notes"):
                    st.caption(provider_diag.get("notes"))
                st.caption(f"Repli declenche : {provider_diag.get('fallback_triggered', False)}")
                if provider_diag.get("queries"):
                    st.dataframe(pd.DataFrame(provider_diag.get("queries", [])), use_container_width=True)


def parse_notes(notes_value: str | None) -> dict:
    if not notes_value:
        return {}
    try:
        return normalize_sender_content(json.loads(notes_value), settings.PROFESSIONAL_EMAIL)
    except json.JSONDecodeError:
        return {}


def resolve_preview_prospect(prospects):
    if not prospects:
        return None
    selected_id = st.session_state.get("preview_prospect_id")
    for prospect in prospects:
        if prospect.id == selected_id:
            return prospect
    return prospects[0]


def apply_channel_filters(prospects, *, phone_available: bool, contact_form_available: bool, social_available: bool, recommended_channel: str | None):
    filtered = []
    for prospect in prospects:
        notes = parse_notes(prospect.notes)
        if phone_available and not prospect.phone:
            continue
        if contact_form_available and not notes.get("contact_form_url"):
            continue
        if social_available and not (notes.get("instagram_url") or notes.get("facebook_url")):
            continue
        if recommended_channel and notes.get("recommended_channel", "unavailable") != recommended_channel:
            continue
        filtered.append(prospect)
    return filtered


def render_alternative_outreach_panel(prospect, notes_data: dict):
    render_section("Canaux de repli", "Canaux alternatifs", "Le produit actuel ne propose plus de fallback manuel en dehors de l'email.")
    st.info("Mode email-only actif : si aucun email n'est disponible, le lead est ignore.")


def build_outreach_preview(prospect, notes_data: dict, lang: str, outreach_asset: str) -> tuple[str, str, str]:
    if lang == "fr":
        subject = prospect.email_subject_fr or "Sujet non genere"
        body = normalize_sender_content(prospect.email_body_fr or "Corps non genere", settings.PROFESSIONAL_EMAIL)
        html_body = normalize_sender_content(prospect.email_html_fr or "", settings.PROFESSIONAL_EMAIL)
    else:
        subject = prospect.email_subject_en or "Sujet non genere"
        body = normalize_sender_content(prospect.email_body_en or "Corps non genere", settings.PROFESSIONAL_EMAIL)
        html_body = normalize_sender_content(prospect.email_html_en or "", settings.PROFESSIONAL_EMAIL)
    if outreach_asset == "Email court":
        prefix = "fr" if lang == "fr" else "en"
        subject = notes_data.get(f"email_short_subject_{prefix}", subject)
        body = notes_data.get(f"email_short_{prefix}", body)
        html_body = ""
    elif outreach_asset == "Relance J+2":
        follow_up = notes_data.get("follow_ups_fr", {}) if lang == "fr" else notes_data.get("follow_ups_en", {})
        subject = follow_up.get("day_2", {}).get("subject", subject)
        body = follow_up.get("day_2", {}).get("body", body)
        html_body = ""
    elif outreach_asset == "Relance J+5":
        follow_up = notes_data.get("follow_ups_fr", {}) if lang == "fr" else notes_data.get("follow_ups_en", {})
        subject = follow_up.get("day_5", {}).get("subject", subject)
        body = follow_up.get("day_5", {}).get("body", body)
        html_body = ""
    elif outreach_asset == "Relance finale J+10":
        follow_up = notes_data.get("follow_ups_fr", {}) if lang == "fr" else notes_data.get("follow_ups_en", {})
        subject = follow_up.get("day_10", {}).get("subject", subject)
        body = follow_up.get("day_10", {}).get("body", body)
        html_body = ""
    return subject, body, html_body


def format_datetime_label(value) -> str:
    if not value:
        return "Jamais"
    if isinstance(value, (int, float)):
        return pd.to_datetime(value, unit="s").strftime("%Y-%m-%d %H:%M")
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d %H:%M")
    return str(value)


def render_copy_text_button(text: str, key: str, label: str = "Copier l'email"):
    safe_key = key.replace(" ", "_")
    components.html(f"""<button id="{safe_key}" style="width:100%;padding:0.72rem 0.9rem;border:1px solid rgba(201,168,106,0.34);border-radius:14px;background:linear-gradient(180deg, rgba(17,19,23,0.98), rgba(10,11,14,0.98));color:#F5EFE3;font-weight:700;letter-spacing:0.05em;cursor:pointer;">{label}</button><div id="{safe_key}_status" style="font-size:12px;color:#9C968A;margin-top:0.35rem;"></div><script>const button=document.getElementById("{safe_key}");const status=document.getElementById("{safe_key}_status");button.addEventListener("click",async()=>{{try{{await navigator.clipboard.writeText({json.dumps(text)});status.textContent="Copie";}}catch(error){{status.textContent="Copie indisponible ici.";}}}});</script>""", height=74)


def execute_ui_send_action(action_name: str, *, selected_ids: list[int], limit: int, only_not_sent: bool, test_to: str | None, simulate: bool, allow_resend: bool) -> dict:
    logger.info(f"UI send action started: action={action_name}, selected_count={len(selected_ids)}, simulate={simulate}, test_mode={bool(test_to)}")
    if test_to:
        logger.info(f"UI send action using test override recipient: {test_to}")
    progress_placeholder = st.empty()
    progress_bar = st.progress(0)
    service = LeadService()

    def handle_progress(index: int, total: int, result_row: dict, summary: dict) -> None:
        total_count = max(total, 1)
        progress_bar.progress(index / total_count)
        progress_placeholder.caption(f"Progression : {index}/{total_count} | envoyes={summary.get('sent', 0)} echecs={summary.get('failed', 0)} ignores={summary.get('skipped', 0)} simulation={summary.get('simulated', 0)} | destinataire={result_row.get('actual_recipient', '')}")

    summary = service.send_emails(limit=limit, only_not_sent=only_not_sent, test_to=test_to, simulate=simulate, selected_ids=selected_ids, allow_resend=allow_resend, progress_callback=handle_progress)
    progress_bar.progress(1.0 if selected_ids else 0.0)
    st.session_state["last_send_summary"] = summary
    return summary


def update_prospect_from_ui(
    prospect_id: int,
    *,
    status: str | None = None,
    send_status: str | None = None,
    last_send_error: str | None = None,
    response_status: str | None = None,
    potential_deal_value: float | None = None,
    reply_notes: str | None = None,
) -> bool:
    return LeadService().update_prospect_status(
        prospect_id,
        status=status,
        send_status=send_status,
        last_send_error=last_send_error,
        response_status=response_status,
        potential_deal_value=potential_deal_value,
        reply_notes=reply_notes,
    )


def get_locations():
    db = SessionLocal()
    try:
        return [row[0] for row in db.query(Prospect.location).distinct().all() if row[0]]
    finally:
        db.close()


def get_categories():
    db = SessionLocal()
    try:
        return [row[0] for row in db.query(Prospect.category).distinct().all() if row[0]]
    finally:
        db.close()


def get_countries():
    db = SessionLocal()
    try:
        return [row[0] for row in db.query(Prospect.country).distinct().all() if row[0]]
    finally:
        db.close()


def get_latest_search_run():
    db = SessionLocal()
    try:
        return db.query(SearchRun).order_by(SearchRun.started_at.desc()).first()
    finally:
        db.close()


def get_prospects(country=None, location=None, category=None, status=None, has_email=None, send_status=None, min_priority=None):
    db = SessionLocal()
    try:
        query = db.query(Prospect)
        if country:
            query = query.filter(Prospect.country == country)
        if location:
            query = query.filter(Prospect.location == location)
        if category:
            query = query.filter(Prospect.category == category)
        if status:
            query = query.filter(Prospect.status == status)
        if has_email is not None:
            query = query.filter(Prospect.email.isnot(None) if has_email else Prospect.email.is_(None))
        if send_status:
            query = query.filter(Prospect.send_status == send_status)
        if min_priority is not None:
            query = query.filter(Prospect.priority_score >= min_priority)
        return query.order_by(Prospect.priority_score.desc(), Prospect.new_business_score.desc(), Prospect.collected_at.desc()).all()
    finally:
        db.close()


def get_top_prospects(limit: int = 5):
    db = SessionLocal()
    try:
        return db.query(Prospect).filter(Prospect.status.in_(["NEW", "MAQUETTE_READY", "REVIEWED"])).order_by(Prospect.priority_score.desc(), Prospect.new_business_score.desc(), Prospect.opportunity_score.desc(), Prospect.phone.isnot(None).desc()).limit(limit).all()
    finally:
        db.close()


def get_recent_outreach_prospects(limit: int = 15):
    db = SessionLocal()
    try:
        return db.query(Prospect).filter(Prospect.last_attempt_at.isnot(None)).order_by(Prospect.last_attempt_at.desc()).limit(limit).all()
    finally:
        db.close()


def get_warm_prospects(limit: int = 12):
    db = SessionLocal()
    try:
        return (
            db.query(Prospect)
            .filter(Prospect.response_status.in_(["REPLIED", "INTERESTED", "WON", "LOST"]))
            .order_by(
                Prospect.response_status.desc(),
                Prospect.potential_deal_value.desc().nullslast(),
                Prospect.replied_at.desc().nullslast(),
            )
            .limit(limit)
            .all()
        )
    finally:
        db.close()


def get_mockup_indicator(status: str | None) -> str:
    normalized = (status or "pending").lower()
    if normalized == "deployed":
        return "deployed"
    if normalized == "failed":
        return "failed"
    return "pending"


def get_send_indicator(status: str | None) -> str:
    normalized = (status or "NOT_SENT").upper()
    if normalized in {"SENT", "FAILED", "SKIPPED", "NOT_SENT"}:
        return normalized
    return "NOT_SENT"


def is_public_mockup_url(url: str | None) -> bool:
    return bool(url and url.startswith(("http://", "https://")))


def render_copy_link_button(url: str, key: str):
    safe_key = key.replace(" ", "_")
    components.html(f"""<button id="{safe_key}" style="width:100%;padding:0.72rem 0.9rem;border:1px solid rgba(201,168,106,0.34);border-radius:14px;background:linear-gradient(180deg, rgba(17,19,23,0.98), rgba(10,11,14,0.98));color:#F5EFE3;font-weight:700;letter-spacing:0.05em;cursor:pointer;">Copier le lien</button><div id="{safe_key}_status" style="font-size:12px;color:#9C968A;margin-top:0.35rem;"></div><script>const button=document.getElementById("{safe_key}");const status=document.getElementById("{safe_key}_status");button.addEventListener("click",async()=>{{try{{await navigator.clipboard.writeText({json.dumps(url)});status.textContent="Lien copie";}}catch(error){{status.textContent="Copie indisponible ici. Utilise l'URL ci-dessous.";}}}});</script>""", height=74)


def render_mockup_actions(prospect, key_prefix: str):
    mockup_url = prospect.mockup_url or ""
    if not mockup_url:
        st.caption("URL maquette indisponible")
        return
    cols = st.columns(2)
    with cols[0]:
        if is_public_mockup_url(mockup_url):
            st.link_button("Ouvrir la maquette", mockup_url, use_container_width=True)
        else:
            st.button("Ouvrir la maquette", disabled=True, key=f"{key_prefix}_open_disabled", use_container_width=True)
    with cols[1]:
        render_copy_link_button(mockup_url, f"{key_prefix}_copy")
    st.caption(mockup_url)


def read_log_tail(lines: int = 120) -> str:
    try:
        if not settings.LOG_FILE.exists():
            return ""
        content = settings.LOG_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
        return "\n".join(content[-lines:])
    except Exception:
        return ""


def get_latest_catchup_status() -> dict[str, str]:
    run_logs_dir = settings.LOG_DIR / "runs"
    latest_log = next(iter(sorted(run_logs_dir.glob("startup_catchup_*.log"), reverse=True)), None)
    if not latest_log or not latest_log.exists():
        return {}

    try:
        lines = latest_log.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return {"last_check": latest_log.stat().st_mtime, "status": "UNKNOWN", "reason": "impossible de lire le log"}

    joined = "\n".join(lines[-40:])
    status = "UNKNOWN"
    reason = "log de rattrapage detecte"

    if any("Skipping startup catch-up because a report already exists for today." in line for line in lines):
        status = "SKIPPED"
        reason = "un rapport existe deja aujourd'hui"
    elif any("No report found for today. Launching autonomous outreach catch-up run." in line for line in lines):
        status = "LAUNCHED"
        reason = "run manque relance apres connexion"
    elif any("Startup catch-up exit code:" in line for line in lines):
        status = "COMPLETED"
        reason = next((line.replace("Startup catch-up exit code:", "code de sortie").strip() for line in lines if "Startup catch-up exit code:" in line), "termine")

    return {
        "last_check": latest_log.stat().st_mtime,
        "status": status,
        "reason": reason,
        "log_excerpt": joined,
    }


def persist_runtime_config(updates: dict[str, object]) -> None:
    env_path = settings.BASE_DIR / ".env"
    existing_lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    keys = set(updates.keys())
    new_lines: list[str] = []
    replaced_keys: set[str] = set()

    for line in existing_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            new_lines.append(line)
            continue
        key, _, _ = line.partition("=")
        key = key.strip()
        if key in keys:
            new_lines.append(f"{key}={format_env_value(updates[key])}")
            replaced_keys.add(key)
        else:
            new_lines.append(line)

    for key, value in updates.items():
        if key not in replaced_keys:
            new_lines.append(f"{key}={format_env_value(value)}")

    env_path.write_text("\n".join(new_lines).rstrip() + "\n", encoding="utf-8")


def format_env_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:g}"
    if isinstance(value, int):
        return str(value)
    text = str(value)
    if any(char in text for char in [' ', '#', '"']):
        escaped = text.replace('"', '\\"')
        return f'"{escaped}"'
    return text


def run_streamlit_app():
    main()


if __name__ == "__main__":
    main()
