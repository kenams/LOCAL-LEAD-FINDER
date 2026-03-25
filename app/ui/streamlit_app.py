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


def main():
    st.set_page_config(page_title="KAH-Digital", page_icon="K", layout="wide")
    init_db()
    inject_global_styles()
    render_sidebar()
    render_brand_header()
    render_automation_center()
    render_manual_debug_mode()


def render_automation_center():
    scheduler_service = SchedulerService()
    report_service = ReportService()
    status = scheduler_service.get_auto_schedule_status()
    report_rows = report_service.list_reports(limit=20)
    latest_report = report_service.load_report(report_rows[0]["path"]) if report_rows else None
    latest_summary = latest_report.get("summary", {}) if latest_report else {}
    latest_funnel = latest_report.get("quality_funnel", {}) if latest_report else {}
    report_status = "READY" if status.get("last_report_path") else "PENDING"

    render_section("Automation", "Autonomous Outreach Monitor", "Monitor the autonomous engine, review recent runs, inspect reports and adjust the schedule.")
    status_cols = st.columns(6)
    with status_cols[0]:
        render_metric_card("Automation", "ON" if status.get("enabled") else "OFF", "Enabled or disabled")
    with status_cols[1]:
        render_metric_card("Schedule", status.get("cron_expression", settings.AUTO_MODE_CRON), "Cron expression")
    with status_cols[2]:
        render_metric_card("Next run", format_datetime_label(status.get("next_run")), "Planned execution")
    with status_cols[3]:
        render_metric_card("Last run", format_datetime_label(status.get("last_run")), "Latest execution")
    with status_cols[4]:
        render_metric_card("Last status", status.get("last_status", "IDLE"), "Execution result")
    with status_cols[5]:
        render_metric_card("Report status", report_status, "Latest report availability")

    catchup_status = get_latest_catchup_status()
    render_section("Catch-up", "Missed Morning Recovery", "Automatic recovery check that runs 30 minutes after sign-in when no report exists yet for the day.")
    catchup_cols = st.columns(4)
    with catchup_cols[0]:
        render_metric_card("Catch-up mode", "ON", "Active through Windows logon startup")
    with catchup_cols[1]:
        render_metric_card("Last check", format_datetime_label(catchup_status.get("last_check")), "Latest delayed login check")
    with catchup_cols[2]:
        render_metric_card("Last result", catchup_status.get("status", "NEVER"), "Skipped, launched or failed")
    with catchup_cols[3]:
        render_metric_card("Reason", catchup_status.get("reason", "No catch-up log yet"), "Why it ran or skipped")
    if catchup_status.get("log_excerpt"):
        with st.expander("Catch-up log", expanded=False):
            st.text_area(
                "Catch-up output",
                value=catchup_status.get("log_excerpt", ""),
                height=180,
                key="catchup_log_output",
                disabled=True,
                label_visibility="collapsed",
            )

    render_section("Last Run", "Latest Summary", "Key results from the most recent autonomous outreach run.")
    summary_cols = st.columns(7)
    with summary_cols[0]:
        render_metric_card("Raw found", str(latest_funnel.get("raw_found", latest_summary.get("raw_found", latest_summary.get("leads_found", 0)))), "All raw candidates discovered")
    with summary_cols[1]:
        render_metric_card("Validated", str(latest_funnel.get("validated_leads", latest_summary.get("validated_leads", 0))), "Passed the quality filter")
    with summary_cols[2]:
        render_metric_card("Contact ready", str(latest_funnel.get("contact_ready", latest_summary.get("contact_ready", 0))), "Ready for outreach routing")
    with summary_cols[3]:
        render_metric_card("Saved", str(latest_funnel.get("leads_saved", latest_summary.get("leads_saved", 0))), "Persisted prospects")
    with summary_cols[4]:
        render_metric_card("Emails sent", str(latest_funnel.get("email_sent", latest_summary.get("email_sent", 0))), "Email channel")
    with summary_cols[5]:
        render_metric_card("SMS sent", str(latest_funnel.get("sms_sent", latest_summary.get("sms_sent", 0))), "SMS fallback")
    with summary_cols[6]:
        render_metric_card("Failed", str(latest_funnel.get("failed", latest_summary.get("failed", 0))), "Execution errors")

    render_section("Lead Quality", "Found -> Kept -> Sent", "Use the quality funnel and rejection reasons to understand why leads were dropped.")
    quality_cols = st.columns(5)
    with quality_cols[0]:
        render_metric_card("Rejected", str(latest_funnel.get("validation_skipped", latest_summary.get("validation_skipped", 0))), "Rejected before outreach")
    with quality_cols[1]:
        render_metric_card("Selected", str(latest_funnel.get("selected", latest_summary.get("selected", 0))), "Queued for delivery this run")
    with quality_cols[2]:
        render_metric_card("Skipped", str(latest_funnel.get("skipped", latest_summary.get("skipped", 0))), "No usable channel at send time")
    with quality_cols[3]:
        render_metric_card("Send cap", str(settings.SEND_MAX_PER_RUN), "Current max sends per run")
    with quality_cols[4]:
        render_metric_card("Min score", str(settings.AUTO_MODE_MIN_OPPORTUNITY_SCORE), "Current opportunity threshold")

    validation_reasons = latest_report.get("validation_reasons", {}) if latest_report else {}
    if validation_reasons:
        reasons_df = pd.DataFrame(
            [{"Reason": reason, "Count": count} for reason, count in validation_reasons.items()]
        ).sort_values(by="Count", ascending=False)
        st.dataframe(reasons_df, hide_index=True, use_container_width=True)
    else:
        st.info("No validation rejections recorded in the latest report.")

    render_section("Recent Runs", "Execution History", "A compact history of recent autonomous runs and outcomes.")
    if report_rows:
        recent_runs_df = pd.DataFrame([
            {
                "Generated": row.get("generated_at"),
                "Trigger": row.get("trigger"),
                "Schedule": row.get("schedule_name"),
                "Raw": row.get("raw_found", row.get("leads_found", 0)),
                "Validated": row.get("validated_leads", 0),
                "Ready": row.get("contact_ready", 0),
                "Saved": row.get("leads_saved", 0),
                "Emails": row.get("email_sent", 0),
                "SMS": row.get("sms_sent", 0),
                "Skipped": row.get("skipped", 0),
                "Failed": row.get("failed", 0),
            }
            for row in report_rows[:10]
        ])
        st.dataframe(recent_runs_df, hide_index=True, use_container_width=True)
    else:
        st.info("No recent runs available yet.")

    render_section("Reports", "Run Reports", "Open the stored JSON/CSV report payloads from recent autonomous runs.")
    if report_rows:
        report_cols = st.columns([1.4, 1, 1])
        with report_cols[0]:
            selected_report_path = st.selectbox("Report file", [row["path"] for row in report_rows], format_func=lambda path: Path(path).name)
        with report_cols[1]:
            selected_meta = next((row for row in report_rows if row["path"] == selected_report_path), {})
            st.caption(f"Trigger: {selected_meta.get('trigger', '')}")
            st.caption(f"Generated: {selected_meta.get('generated_at', '')}")
        with report_cols[2]:
            if selected_report_path:
                st.caption(selected_report_path)
        report_payload = report_service.load_report(selected_report_path)
        if report_payload:
            report_summary = report_payload.get("summary", {})
            report_funnel = report_payload.get("quality_funnel", {})
            funnel_cols = st.columns(6)
            with funnel_cols[0]:
                render_metric_card("Raw", str(report_funnel.get("raw_found", report_summary.get("raw_found", report_summary.get("leads_found", 0)))), "Candidates found")
            with funnel_cols[1]:
                render_metric_card("Validated", str(report_funnel.get("validated_leads", report_summary.get("validated_leads", 0))), "After quality filter")
            with funnel_cols[2]:
                render_metric_card("Ready", str(report_funnel.get("contact_ready", report_summary.get("contact_ready", 0))), "Contactable leads")
            with funnel_cols[3]:
                render_metric_card("Saved", str(report_funnel.get("leads_saved", report_summary.get("leads_saved", 0))), "Saved to database")
            with funnel_cols[4]:
                render_metric_card("Selected", str(report_funnel.get("selected", report_summary.get("selected", 0))), "Queued to send")
            with funnel_cols[5]:
                render_metric_card("Sent", str(report_funnel.get("email_sent", report_summary.get("email_sent", 0)) + report_funnel.get("sms_sent", report_summary.get("sms_sent", 0))), "Delivered this run")
            if report_payload.get("validation_reasons"):
                st.dataframe(
                    pd.DataFrame(
                        [{"Reason": reason, "Count": count} for reason, count in report_payload.get("validation_reasons", {}).items()]
                    ).sort_values(by="Count", ascending=False),
                    hide_index=True,
                    use_container_width=True,
                )
            if report_payload.get("failure_reasons"):
                st.json(report_payload.get("failure_reasons"))
            report_results_df = pd.DataFrame(report_summary.get("results", []))
            if not report_results_df.empty:
                st.dataframe(report_results_df, use_container_width=True)
    else:
        st.info("No report saved yet.")

    render_section("Logs", "Execution Logs", "Tail of the application log for quick troubleshooting.")
    log_controls = st.columns([1.2, 2.8])
    with log_controls[0]:
        log_height = st.select_slider("Log height", options=[180, 260, 360, 520, 720], value=260, key="log_height")
    with log_controls[1]:
        st.caption("Reduce or expand the log panel depending on how much troubleshooting context you need.")
    log_text = read_log_tail()
    if log_text:
        st.text_area("Log output", value=log_text, height=log_height, key="log_output", disabled=True, label_visibility="collapsed")
    else:
        st.info("No logs available yet.")

    render_section("Lead Summary", "Recent Outreach Activity", "Latest contacted prospects and their send outcomes.")
    lead_summary = pd.DataFrame(
        [
            {
                "Business": prospect.business_name,
                "Location": prospect.location,
                "Channel": prospect.selected_outreach_channel or "",
                "Outreach Status": prospect.outreach_status or "",
                "Send Status": prospect.send_status or "",
                "Last Attempt": format_datetime_label(prospect.last_attempt_at),
                "Error": prospect.last_send_error or "",
            }
            for prospect in get_recent_outreach_prospects(limit=15)
        ]
    )
    if not lead_summary.empty:
        st.dataframe(lead_summary, hide_index=True, use_container_width=True)
    else:
        st.info("No recent outreach activity yet.")

    render_section("Configuration", "Minimal Automation Config", "Adjust the autonomous schedule, scope and runtime settings from one small panel.")
    st.caption("Recommended production rhythm: `0 9,18 * * *` with `5` sends per run for a target of `10` sends per day.")
    config_cols = st.columns([1.2, 1.2, 0.8, 0.8, 1.2])
    with config_cols[0]:
        auto_locations = st.text_input("Locations", value=status.get("locations", settings.AUTO_MODE_LOCATIONS), key="auto_cfg_locations")
    with config_cols[1]:
        auto_categories = st.text_input("Categories", value=status.get("categories", settings.AUTO_MODE_CATEGORIES), key="auto_cfg_categories")
    with config_cols[2]:
        auto_limit = st.number_input("Limit", min_value=1, max_value=50, value=int(status.get("limit", settings.AUTO_MODE_LIMIT)), key="auto_cfg_limit")
    with config_cols[3]:
        auto_language = st.selectbox("Language", ["fr", "en"], index=0 if status.get("language", "fr") == "fr" else 1, key="auto_cfg_language")
    with config_cols[4]:
        auto_cron = st.text_input("Cron", value=status.get("cron_expression", settings.AUTO_MODE_CRON), key="auto_cfg_cron")
    runtime_cols = st.columns(4)
    with runtime_cols[0]:
        send_max_per_run = st.number_input("Send cap / run", min_value=1, max_value=50, value=int(settings.SEND_MAX_PER_RUN), key="auto_cfg_send_cap")
    with runtime_cols[1]:
        send_delay_seconds = st.number_input("Delay between sends", min_value=0.0, max_value=30.0, value=float(settings.SEND_DELAY_SECONDS), step=0.5, key="auto_cfg_send_delay")
    with runtime_cols[2]:
        candidate_multiplier = st.number_input("Search depth", min_value=2, max_value=40, value=int(settings.AUTO_MODE_CONTACT_CANDIDATE_MULTIPLIER), key="auto_cfg_candidate_multiplier")
    with runtime_cols[3]:
        min_opportunity_score = st.number_input("Min opportunity score", min_value=0, max_value=100, value=int(settings.AUTO_MODE_MIN_OPPORTUNITY_SCORE), key="auto_cfg_min_score")
    config_action_cols = st.columns([1, 2])
    with config_action_cols[0]:
        auto_enabled = st.checkbox("Auto mode enabled", value=bool(status.get("enabled")), key="auto_cfg_enabled")
    with config_action_cols[1]:
        if st.button("Save automation config", use_container_width=True):
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
            st.success("Automation configuration updated.")
            st.rerun()

    if status.get("last_error"):
        st.warning(f"Last error: {status.get('last_error')}")


def render_manual_debug_mode():
    with st.expander("Debug / Manual Mode", expanded=False):
        render_section("Debug", "Manual and Troubleshooting Tools", "Secondary tools for testing, previews, targeted sends and diagnostics.")
        render_debug_tools()

        render_search_section()
        render_section("Search Diagnostics", "Observability", "Queries, providers and raw candidate counts for the latest collection run.")
        render_search_diagnostics()

        render_section("Lead Intelligence", "Manual Review", "Manual inspection tools kept for debugging and exceptional operator workflows.")
        prospects, selected_prospects = render_lead_console()
        if not prospects:
            st.info("No prospects found. Launch a search to start building the pipeline.")
            return

        export_cols = st.columns(2)
        with export_cols[0]:
            if st.button("Export CSV", use_container_width=True):
                ExportService().export_leads("csv")
                st.success("CSV export created.")
        with export_cols[1]:
            if st.button("Export Excel", use_container_width=True):
                ExportService().export_leads("xlsx")
                st.success("Excel export created.")

        render_section("Sender Identity", "KAH.DIGITAL Outreach", "Professional sender identity, signature and mockup quality settings used across emails, follow-ups and exports.")
        render_sender_identity_preview()

        render_section("Preview", "Manual Preview Examples", "Preview one lead, inspect the generated outreach assets and troubleshoot message quality.")
        preview_pool = selected_prospects or prospects
        prospect = resolve_preview_prospect(preview_pool)
        render_prospect_summary(prospect, f"preview_{prospect.id}")
        notes_data = parse_notes(prospect.notes)
        lang = st.selectbox("Preview language", ["fr", "en"], index=0 if (prospect.email_language or "fr") == "fr" else 1)
        outreach_asset = st.selectbox("Outreach asset", ["Primary email", "Short email", "Follow-up J+2", "Follow-up J+5", "Final follow-up J+10", "SMS", "Call script", "Contact form", "Social DM"])
        subject, body, html_body = build_outreach_preview(prospect, notes_data, lang, outreach_asset)

        preview_cols = st.columns([1, 1.2])
        with preview_cols[0]:
            render_key_value_card("Example Context", [
                ("Language", prospect.email_language or "N/A"),
                ("Price", format_price_range(prospect.estimated_price_min, prospect.estimated_price_max, prospect.country)),
                ("Recommended channel", notes_data.get("recommended_channel", "N/A")),
                ("Selected outreach", prospect.selected_outreach_channel or "N/A"),
                ("Outreach status", prospect.outreach_status or "N/A"),
                ("Recipient", prospect.email or prospect.phone or "Unavailable"),
                ("Send status", get_send_indicator(prospect.send_status)),
                ("Last error", prospect.last_send_error or "None"),
            ])
        with preview_cols[1]:
            st.text_input("Subject", value=subject, key=f"subject_{prospect.id}")
            st.text_area("Message", value=body, height=260, key=f"body_{prospect.id}")
            if html_body:
                with st.expander("HTML preview", expanded=False):
                    components.html(html_body, height=520, scrolling=True)
        render_alternative_outreach_panel(prospect, notes_data)

        render_section("Manual Send", "Targeted Send Controls", "Manual send actions are still available here for isolated testing and support.")
        render_send_panel(prospects, selected_prospects, prospect, subject, body, html_body)

        if st.session_state.get("last_send_summary"):
            summary = st.session_state["last_send_summary"]
            st.caption(f"Last manual send: selected={summary.get('selected', 0)} | sent={summary.get('sent', 0)} | failed={summary.get('failed', 0)} | skipped={summary.get('skipped', 0)} | simulated={summary.get('simulated', 0)}")
            results_df = pd.DataFrame(summary.get("results", []))
            if not results_df.empty:
                st.dataframe(results_df, use_container_width=True)


def render_debug_tools():
    scheduler_service = SchedulerService()
    status = scheduler_service.get_auto_schedule_status()
    lead_service = LeadService()
    debug_cols = st.columns([1, 1, 1.2])
    with debug_cols[0]:
        debug_run_dry = st.checkbox("Dry run manual trigger", value=True, key="debug_run_dry")
    with debug_cols[1]:
        test_to_self = st.checkbox("Test send to self", value=True, key="debug_test_to_self")
    with debug_cols[2]:
        st.caption("Use these tools for one-off checks only. The autonomous scheduler remains the primary flow.")

    button_cols = st.columns(2)
    with button_cols[0]:
        if st.button("Run auto flow now", use_container_width=True):
            summary = scheduler_service.run_auto_outreach_now(simulate=debug_run_dry)
            st.session_state["last_auto_outreach_summary"] = summary
            st.success(
                f"Manual auto run complete. leads_found={summary.get('leads_found', 0)} "
                f"email_sent={summary.get('email_sent', 0)} sms_sent={summary.get('sms_sent', 0)} "
                f"skipped={summary.get('skipped', 0)} failed={summary.get('failed', 0)}"
            )
    with button_cols[1]:
        if st.button("Send one test email to self", use_container_width=True):
            prospects = get_prospects(has_email=True, send_status=None)
            if not prospects:
                st.warning("No lead with email is available for a self-test.")
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
                    f"Test send complete. sent={summary.get('sent', 0)} failed={summary.get('failed', 0)} "
                    f"skipped={summary.get('skipped', 0)} simulated={summary.get('simulated', 0)}"
                )

    render_key_value_card("Troubleshooting", [
        ("Scheduler running", "Yes" if status.get("scheduler_running") else "No"),
        ("Automation enabled", "Yes" if status.get("enabled") else "No"),
        ("Next run", format_datetime_label(status.get("next_run"))),
        ("Last status", status.get("last_status", "IDLE")),
        ("SMTP host", settings.SMTP_HOST or "Missing"),
        ("SMS provider", settings.SMS_PROVIDER or "Missing"),
    ])
    for warning in settings.get_smtp_identity_warnings():
        st.warning(warning)


def render_search_section():
    render_section("Search Studio", "Lead Collection", "Launch multi-market searches across countries while keeping the existing business pipeline intact.")
    search_col1, search_col2 = st.columns([1.25, 1])
    with search_col1:
        locations = st.multiselect("Locations", SEARCH_LOCATIONS, default=["Toulouse", "Geneva", "New York"])
        categories = st.multiselect("Categories", SEARCH_CATEGORIES, default=["coiffeur"])
    with search_col2:
        limit = st.number_input("Prospects per location", min_value=1, max_value=50, value=10)
        language = st.selectbox("Fallback language", ["fr", "en"], index=0)
        with st.expander("Search depth", expanded=False):
            queries_per_combo = st.slider("Queries per location/category", 3, 20, settings.SEARCH_QUERIES_PER_COMBO)
            max_raw_candidates = st.slider("Max raw candidates", 10, 60, settings.SEARCH_MAX_RAW_CANDIDATES, step=2)
            fallback_enabled = st.checkbox("Enable provider fallback", value=settings.SEARCH_FALLBACK_ENABLED)
            broaden_if_empty = st.checkbox("Broaden search if empty", value=settings.SEARCH_BROADEN_IF_EMPTY)
            reset_before_collect = st.checkbox("Clear previous leads before collection", value=settings.SEARCH_RESET_BEFORE_COLLECT)
    action_col1, action_col2, action_col3, _ = st.columns([1, 1, 1.2, 1.4])
    with action_col1:
        collect_clicked = st.button("Collect Leads", type="primary", use_container_width=True)
    with action_col2:
        st.button("Generate", disabled=True, use_container_width=True)
    with action_col3:
        reset_clicked = st.button("Reset leads / Clear database", use_container_width=True)
    if reset_clicked:
        deleted = LeadService().reset_leads(clear_search_history=True)
        st.success(f"Database cleared. {deleted} leads deleted.")
        st.rerun()
    if collect_clicked:
        if not (locations and categories):
            st.error("Select at least one location and one category.")
            return
        settings.SEARCH_QUERIES_PER_COMBO = queries_per_combo
        settings.SEARCH_MAX_RAW_CANDIDATES = max_raw_candidates
        settings.SEARCH_FALLBACK_ENABLED = fallback_enabled
        settings.SEARCH_BROADEN_IF_EMPTY = broaden_if_empty
        settings.SEARCH_RESET_BEFORE_COLLECT = reset_before_collect
        if reset_before_collect:
            LeadService().reset_leads(clear_search_history=True)
        saved_count = asyncio.run(LeadService().collect_leads(locations, categories, limit, language))
        st.success(f"Collection complete. {saved_count} new leads saved.")
        st.rerun()


def render_lead_console():
    cols = st.columns(6)
    with cols[0]:
        filter_country = st.selectbox("Country", ["All"] + sorted(set(get_countries())))
    with cols[1]:
        filter_location = st.selectbox("Location", ["All"] + sorted(set(get_locations())))
    with cols[2]:
        filter_category = st.selectbox("Category", ["All"] + sorted(set(get_categories())))
    with cols[3]:
        filter_status = st.selectbox("Lifecycle", ["All", "NEW", "REVIEWED", "MAQUETTE_READY", "CONTACTED", "WON", "LOST"])
    with cols[4]:
        filter_email = st.selectbox("Has email", ["All", "Yes", "No"])
    with cols[5]:
        filter_send_status = st.selectbox("Send status", ["All", "NOT_SENT", "FAILED", "SKIPPED", "SENT"])
    extra_cols = st.columns(4)
    with extra_cols[0]:
        filter_only_not_sent = st.checkbox("NOT_SENT only", value=False)
    with extra_cols[1]:
        filter_min_priority = st.slider("Minimum priority", 0, 200, 0)
    with extra_cols[2]:
        filter_phone_available = st.checkbox("Phone available", value=False)
    with extra_cols[3]:
        filter_contact_form_available = st.checkbox("Contact form available", value=False)
    channel_cols = st.columns(2)
    with channel_cols[0]:
        filter_social_available = st.checkbox("Social available", value=False)
    with channel_cols[1]:
        filter_recommended_channel = st.selectbox("Recommended channel", ["All", "email", "phone", "contact_form", "instagram", "facebook", "unavailable"])
    prospects = get_prospects(
        country=filter_country if filter_country != "All" else None,
        location=filter_location if filter_location != "All" else None,
        category=filter_category if filter_category != "All" else None,
        status=filter_status if filter_status != "All" else None,
        has_email=(filter_email == "Yes") if filter_email != "All" else None,
        send_status="NOT_SENT" if filter_only_not_sent else (filter_send_status if filter_send_status != "All" else None),
        min_priority=filter_min_priority if filter_min_priority > 0 else None,
    )
    prospects = apply_channel_filters(
        prospects,
        phone_available=filter_phone_available,
        contact_form_available=filter_contact_form_available,
        social_available=filter_social_available,
        recommended_channel=filter_recommended_channel if filter_recommended_channel != "All" else None,
    )
    if not prospects:
        return [], []
    select_cols = st.columns(2)
    with select_cols[0]:
        if st.button("Select valid email leads", use_container_width=True):
            st.session_state["selected_lead_ids"] = [prospect.id for prospect in prospects if prospect.email]
            st.rerun()
    with select_cols[1]:
        if st.button("Clear selected leads", use_container_width=True):
            st.session_state["selected_lead_ids"] = []
            st.rerun()
    selected_ids = set(st.session_state.get("selected_lead_ids", []))
    table = pd.DataFrame([{
        "Select": prospect.id in selected_ids,
        "Business": prospect.business_name,
        "Country": prospect.country,
        "Location": prospect.location,
        "Category": prospect.category,
        "Priority": prospect.priority_score or 0,
        "Email": prospect.email or "",
        "Phone": prospect.phone or "",
        "Recommended Channel": parse_notes(prospect.notes).get("recommended_channel", "unavailable"),
        "Outreach Channel": prospect.selected_outreach_channel or "",
        "Outreach Status": prospect.outreach_status or "",
        "Contact Form": parse_notes(prospect.notes).get("contact_form_url", ""),
        "Instagram": parse_notes(prospect.notes).get("instagram_url", ""),
        "Facebook": parse_notes(prospect.notes).get("facebook_url", ""),
        "Send Status": get_send_indicator(prospect.send_status),
        "First Sent": format_datetime_label(prospect.first_sent_at),
        "Last Attempt": format_datetime_label(prospect.last_attempt_at),
        "Attempts": int(prospect.send_attempts or 0),
        "Last Error": prospect.last_send_error or "",
        "Mockup URL": prospect.mockup_url or "",
    } for prospect in prospects])
    edited = st.data_editor(table, hide_index=True, use_container_width=True, key="lead_selection_table", column_config={"Select": st.column_config.CheckboxColumn("Select"), "Priority": st.column_config.NumberColumn("Priority", format="%.2f")}, disabled=["Business", "Country", "Location", "Category", "Priority", "Email", "Phone", "Recommended Channel", "Outreach Channel", "Outreach Status", "Contact Form", "Instagram", "Facebook", "Send Status", "First Sent", "Last Attempt", "Attempts", "Last Error", "Mockup URL"])
    selected_rows = [index for index, row in edited.iterrows() if row["Select"]]
    st.session_state["selected_lead_ids"] = [prospects[index].id for index in selected_rows]
    selected_prospects = [prospect for prospect in prospects if prospect.id in st.session_state["selected_lead_ids"]]
    st.caption(f"Filtered leads: {len(prospects)} | Selected leads: {len(selected_prospects)} | Leads with valid email: {sum(1 for prospect in prospects if prospect.email)}")
    return prospects, selected_prospects


def render_send_panel(prospects, selected_prospects, current_prospect, current_subject, current_body, current_html_body):
    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL or not settings.SMTP_PASSWORD:
        st.warning("SMTP configuration looks incomplete. Sending may fail until SMTP host, from email and password are configured.")
    for warning in settings.get_smtp_identity_warnings():
        st.warning(warning)
    cols = st.columns(5)
    with cols[0]:
        auto_send_enabled = st.toggle("Auto-send enabled", value=settings.AUTO_SEND_ENABLED)
    with cols[1]:
        send_only_not_sent = st.checkbox("Only NOT_SENT", value=True)
    with cols[2]:
        send_only_with_email = st.checkbox("Only leads with email", value=True)
    with cols[3]:
        send_allow_resend = st.checkbox("Allow resend", value=settings.SEND_ALLOW_RESEND)
    with cols[4]:
        test_mode_enabled = st.checkbox("Test mode", value=True)
    opt_cols = st.columns(4)
    with opt_cols[0]:
        send_status_filter = st.selectbox("Send status filter", ["All", "NOT_SENT", "FAILED", "SKIPPED", "SENT"], index=1)
    with opt_cols[1]:
        min_send_priority = st.slider("Min priority for send", 0, 200, 70)
    with opt_cols[2]:
        send_limit = st.number_input("Max emails this action", min_value=1, max_value=50, value=min(settings.SEND_MAX_PER_RUN, 5))
    with opt_cols[3]:
        confirm_bulk_send = st.checkbox("Confirm bulk send", value=False)
    test_to = st.text_input("Test recipient", value=settings.PROFESSIONAL_EMAIL if test_mode_enabled else "", disabled=not test_mode_enabled)
    send_pool = selected_prospects or prospects
    send_candidates = [candidate for candidate in send_pool if (candidate.email or not send_only_with_email)]
    if send_status_filter != "All":
        send_candidates = [candidate for candidate in send_candidates if get_send_indicator(candidate.send_status) == send_status_filter]
    if send_only_not_sent:
        send_candidates = [candidate for candidate in send_candidates if get_send_indicator(candidate.send_status) == "NOT_SENT"]
    send_candidates = [candidate for candidate in send_candidates if (candidate.priority_score or 0) >= min_send_priority]
    selected_ids = set(st.session_state.get("selected_lead_ids", []))
    selected_send_ids = [candidate.id for candidate in send_candidates if candidate.id in selected_ids]
    top_send_ids = [candidate.id for candidate in send_candidates[:send_limit]]
    valid_email_send_ids = [candidate.id for candidate in send_candidates if candidate.email][:send_limit]
    eligible_with_email = sum(1 for candidate in send_candidates if candidate.email)
    render_key_value_card("Bulk Send Preview", [("Current scope", "Selected leads" if selected_prospects else "Filtered leads"), ("Scoped leads", str(len(send_pool))), ("Eligible now", str(len(send_candidates))), ("With valid email", str(eligible_with_email)), ("Selected for send", str(len(selected_send_ids))), ("Action max", str(send_limit)), ("Test recipient", test_to if test_mode_enabled and test_to else "Disabled")])
    render_key_value_card("Current Send Preview", [("Business", current_prospect.business_name), ("Sender", get_business_identity().sender_display_name), ("Recipient", test_to if test_mode_enabled and test_to else (current_prospect.email or "No email")), ("Subject", current_subject or "Not generated"), ("Language", current_prospect.email_language or "N/A"), ("Send status", get_send_indicator(current_prospect.send_status)), ("Mockup URL", current_prospect.mockup_url or "Unavailable")])
    with st.expander("Body preview before send", expanded=False):
        st.text_area("Preview", value=current_body or "Email body not generated", height=220, key=f"send_preview_{current_prospect.id}")
        if current_html_body:
            with st.expander("HTML preview", expanded=False):
                components.html(current_html_body, height=520, scrolling=True)
        render_copy_text_button(f"To: {test_to if test_mode_enabled and test_to else (current_prospect.email or '')}\nSubject: {current_subject or ''}\n\n{current_body or ''}", f"copy_preview_{current_prospect.id}", label="Copy email")
    if send_only_with_email and not eligible_with_email:
        st.warning("No valid extracted email is available in the current send scope.")
    settings.AUTO_SEND_ENABLED = auto_send_enabled
    btns = st.columns(5)
    with btns[0]:
        send_selected_clicked = st.button("Send selected emails", use_container_width=True)
    with btns[1]:
        send_top_clicked = st.button("Send top priority emails", use_container_width=True)
    with btns[2]:
        send_test_clicked = st.button("Send one test email to myself", use_container_width=True)
    with btns[3]:
        valid_email_clicked = st.button("Send only leads with valid email", use_container_width=True)
    with btns[4]:
        simulate_clicked = st.button("Simulate send (dry run)", use_container_width=True)
    if valid_email_clicked:
        if not valid_email_send_ids:
            st.warning("No eligible lead with a valid email matches the current send filters.")
        elif len(valid_email_send_ids) > 1 and not confirm_bulk_send:
            st.warning("Confirm the bulk send action before sending multiple emails.")
        else:
            execute_and_rerender("send_valid_email", valid_email_send_ids, min(send_limit, len(valid_email_send_ids)), send_only_not_sent, test_to if test_mode_enabled and test_to else None, False, send_allow_resend)
    if send_selected_clicked:
        if not selected_send_ids:
            st.warning("Select at least one eligible lead to send.")
        elif len(selected_send_ids) > 1 and not confirm_bulk_send:
            st.warning("Confirm the bulk send action before sending multiple emails.")
        else:
            execute_and_rerender("send_selected", selected_send_ids, send_limit, send_only_not_sent, test_to if test_mode_enabled and test_to else None, False, send_allow_resend)
    if send_top_clicked:
        if not top_send_ids:
            st.warning("No eligible leads match the current send filters.")
        elif len(top_send_ids) > 1 and not confirm_bulk_send:
            st.warning("Confirm the bulk send action before sending multiple emails.")
        else:
            execute_and_rerender("send_top_priority", top_send_ids, send_limit, send_only_not_sent, test_to if test_mode_enabled and test_to else None, False, send_allow_resend)
    if send_test_clicked:
        execute_and_rerender("send_single_test", [current_prospect.id], 1, False, test_to if test_mode_enabled and test_to else settings.PROFESSIONAL_EMAIL, False, True)
    if simulate_clicked:
        simulation_ids = selected_send_ids or top_send_ids
        if not simulation_ids:
            st.warning("No eligible leads are available for simulation.")
        else:
            execute_and_rerender("simulate_send", simulation_ids, min(send_limit, len(simulation_ids)), send_only_not_sent, test_to if test_mode_enabled and test_to else None, True, send_allow_resend)
    render_section("Selected Actions", "Per-Lead Controls", "Preview, send, skip and update workflow state directly on selected leads or on the current preview lead.")
    for prospect in (selected_prospects or [current_prospect])[:8]:
        notes = parse_notes(prospect.notes)
        subject, body, _ = build_outreach_preview(prospect, notes, prospect.email_language or "fr", "Primary email")
        with st.expander(f"{prospect.business_name} | {prospect.location} | {get_send_indicator(prospect.send_status)}", expanded=(prospect.id == current_prospect.id)):
            render_key_value_card("Lead Delivery Card", [("Recipient", prospect.email or "No email"), ("Fallback channel", notes.get("recommended_channel", "N/A")), ("Phone", prospect.phone or "N/A"), ("Contact form", notes.get("contact_form_url", "N/A")), ("Instagram", notes.get("instagram_url", "N/A")), ("Facebook", notes.get("facebook_url", "N/A")), ("Subject", subject or "Not generated"), ("First sent", format_datetime_label(prospect.first_sent_at)), ("Last attempt", format_datetime_label(prospect.last_attempt_at)), ("Attempts", str(prospect.send_attempts or 0)), ("Last error", prospect.last_send_error or "None")])
            if not prospect.email:
                st.info(f"Send disabled because no email was extracted. Recommended fallback: {notes.get('recommended_channel', 'manual follow-up')}.")
            action_cols = st.columns(6)
            with action_cols[0]:
                send_now = st.button("Send now", key=f"send_now_{prospect.id}", use_container_width=True, disabled=not bool(prospect.email))
            with action_cols[1]:
                preview_btn = st.button("Preview email", key=f"preview_email_{prospect.id}", use_container_width=True)
            with action_cols[2]:
                render_copy_text_button(f"To: {prospect.email or ''}\nSubject: {subject or ''}\n\n{body or ''}", f"copy_email_{prospect.id}", label="Copy email")
            with action_cols[3]:
                skip_btn = st.button("Skip", key=f"skip_{prospect.id}", use_container_width=True)
            with action_cols[4]:
                review_btn = st.button("Mark reviewed", key=f"review_{prospect.id}", use_container_width=True)
            with action_cols[5]:
                contact_btn = st.button("Mark as contacted", key=f"contact_{prospect.id}", use_container_width=True)
            fallback_cols = st.columns(6)
            with fallback_cols[0]:
                render_copy_text_button(notes.get("sms_message", notes.get("sms", "")) or "SMS unavailable", f"sms_{prospect.id}", label="Copy SMS")
            with fallback_cols[1]:
                render_copy_text_button(notes.get("call_script", "") or "Call script unavailable", f"call_{prospect.id}", label="Copy call script")
            with fallback_cols[2]:
                if notes.get("contact_form_url"):
                    st.link_button("Open contact form", notes.get("contact_form_url"), use_container_width=True)
                else:
                    st.button("Open contact form", key=f"contact_form_missing_{prospect.id}", disabled=True, use_container_width=True)
            with fallback_cols[3]:
                if notes.get("instagram_url"):
                    st.link_button("Open Instagram", notes.get("instagram_url"), use_container_width=True)
                else:
                    st.button("Open Instagram", key=f"instagram_missing_{prospect.id}", disabled=True, use_container_width=True)
            with fallback_cols[4]:
                if notes.get("facebook_url"):
                    st.link_button("Open Facebook", notes.get("facebook_url"), use_container_width=True)
                else:
                    st.button("Open Facebook", key=f"facebook_missing_{prospect.id}", disabled=True, use_container_width=True)
            with fallback_cols[5]:
                render_copy_text_button(notes.get("social_dm_message", "") or "DM unavailable", f"dm_{prospect.id}", label="Copy DM message")
            with st.expander("Prepared fallback messages", expanded=False):
                st.text_area("SMS", value=notes.get("sms_message", notes.get("sms", "")), height=90, key=f"sms_preview_{prospect.id}")
                st.text_area("Call script", value=notes.get("call_script", ""), height=180, key=f"call_preview_{prospect.id}")
                st.text_area("Contact form message", value=notes.get("contact_form_message", ""), height=140, key=f"form_preview_{prospect.id}")
                st.text_area("Social DM", value=notes.get("social_dm_message", ""), height=120, key=f"dm_preview_{prospect.id}")
            if preview_btn:
                st.session_state["preview_prospect_id"] = prospect.id
                st.rerun()
            if send_now:
                execute_and_rerender("send_single_now", [prospect.id], 1, send_only_not_sent, test_to if test_mode_enabled and test_to else None, False, send_allow_resend)
            if skip_btn and update_prospect_from_ui(prospect.id, send_status="SKIPPED", last_send_error="ui_skipped"):
                st.success("Lead marked as skipped.")
                st.rerun()
            if review_btn and update_prospect_from_ui(prospect.id, status="REVIEWED"):
                st.success("Lead marked as reviewed.")
                st.rerun()
            if contact_btn and update_prospect_from_ui(prospect.id, status="CONTACTED"):
                st.success("Lead marked as contacted.")
                st.rerun()


def execute_and_rerender(action_name, selected_ids, limit, only_not_sent, test_to, simulate, allow_resend):
    summary = execute_ui_send_action(action_name, selected_ids=selected_ids, limit=limit, only_not_sent=only_not_sent, test_to=test_to, simulate=simulate, allow_resend=allow_resend)
    st.success(f"Action complete. sent={summary.get('sent', 0)} failed={summary.get('failed', 0)} skipped={summary.get('skipped', 0)} simulated={summary.get('simulated', 0)}")
    st.rerun()


def render_sidebar():
    render_sidebar_brand()
    st.sidebar.markdown(f"""<div class="kah-card"><div class="kah-section-label">Status System</div><div class="kah-inline-badges">{status_badge_html("deployed")}{status_badge_html("pending")}{status_badge_html("failed")}</div><div class="kah-inline-badges" style="margin-top:0.7rem;">{priority_badge_html(125)}{priority_badge_html(90)}{priority_badge_html(45)}</div></div>""", unsafe_allow_html=True)
    st.sidebar.markdown("""<div class="kah-card"><div class="kah-section-label">Brand Notes</div><div style="color:var(--kah-muted); font-size:0.9rem; line-height:1.65;">Black and gold visual system inspired by KAH.DIGITAL and KAH-PROD. Built to feel like a premium digital studio control panel rather than a generic admin dashboard.</div></div>""", unsafe_allow_html=True)


def render_prospect_summary(prospect, key_prefix: str):
    notes = parse_notes(prospect.notes)
    badges = "".join([badge_html(prospect.country or "N/A", "neutral"), badge_html(prospect.currency or "N/A", "neutral"), status_badge_html(get_mockup_indicator(prospect.mockup_status)), priority_badge_html(prospect.priority_score)])
    st.markdown(f'<div class="kah-inline-badges">{badges}</div>', unsafe_allow_html=True)
    cols = st.columns(2)
    with cols[0]:
        render_key_value_card("Market Profile", [("Country", f"{prospect.country} - {get_country_display_name(prospect.country)}"), ("Location", prospect.location), ("Category", prospect.category), ("Website", prospect.website or "N/A"), ("Priority", str(round(prospect.priority_score or 0, 2))), ("Send status", get_send_indicator(prospect.send_status))])
    with cols[1]:
        render_key_value_card("Contact Readiness", [("Email", prospect.email or "N/A"), ("Phone", prospect.phone or "N/A"), ("Recommended channel", notes.get("recommended_channel", "unavailable")), ("Selected outreach", prospect.selected_outreach_channel or "N/A"), ("Outreach status", prospect.outreach_status or "N/A"), ("Contact form", notes.get("contact_form_url", "N/A")), ("Instagram", notes.get("instagram_url", "N/A")), ("Facebook", notes.get("facebook_url", "N/A")), ("Language", prospect.email_language or "N/A"), ("Estimated price", format_price_range(prospect.estimated_price_min, prospect.estimated_price_max, prospect.country)), ("Mockup", get_mockup_indicator(prospect.mockup_status)), ("Send attempts", str(prospect.send_attempts or 0))])
    render_mockup_actions(prospect, key_prefix)


def render_sender_identity_preview():
    identity = get_business_identity()
    for warning in settings.get_smtp_identity_warnings():
        st.warning(warning)
    cols = st.columns([1, 1.1])
    with cols[0]:
        render_key_value_card("Sender Profile", get_sender_preview_rows())
    with cols[1]:
        render_key_value_card("Email Signature", [("Display name", identity.sender_display_name), ("Label", identity.signature_label), ("Email", identity.professional_email), ("Phone", identity.professional_phone), ("Website", identity.website)])
        with st.expander("Signature preview", expanded=False):
            st.code(get_text_signature("fr"), language="text")


def render_search_diagnostics():
    latest_run = get_latest_search_run()
    if not latest_run or not latest_run.diagnostics_json:
        st.info("No search diagnostics available yet.")
        return
    try:
        diagnostics = json.loads(latest_run.diagnostics_json)
    except json.JSONDecodeError:
        st.warning("Search diagnostics are present but could not be parsed.")
        return
    st.caption(f"Latest run: {latest_run.locations} | {latest_run.categories} | queries/combo={settings.SEARCH_QUERIES_PER_COMBO} | raw target={settings.SEARCH_MAX_RAW_CANDIDATES} | fallback={settings.SEARCH_FALLBACK_ENABLED} | broaden={settings.SEARCH_BROADEN_IF_EMPTY}")
    for item in diagnostics:
        title = f"{item.get('location')} | {item.get('requested_category')} | {item.get('country')}"
        with st.expander(title):
            cols = st.columns(2)
            with cols[0]:
                render_key_value_card("Search Plan", [("Normalized location", item.get("normalized_location", "")), ("Country", item.get("country", "")), ("Language", item.get("language", "")), ("Category terms", ", ".join(item.get("translated_terms", [])[:4])), ("OSM tags", ", ".join(f'{tag.get("key")}={tag.get("value")}' for tag in item.get("osm_tags", [])[:3])), ("Raw candidates", str(item.get("raw_candidates", 0)))])
            with cols[1]:
                render_key_value_card("Outcome", [("Processed", str(item.get("processed_candidates", 0))), ("Valid kept", str(item.get("valid_prospects_kept", 0))), ("Rejected", str(item.get("rejected_after_filter", 0))), ("Aliases", ", ".join(item.get("location_aliases", [])[:4])), ("Queries", str(len(item.get("queries", []))))])
            st.markdown("**Generated queries**")
            st.code("\n".join(item.get("queries", [])), language="text")
            if item.get("broadened_queries"):
                st.markdown("**Broadened fallback queries**")
                st.code("\n".join(item.get("broadened_queries", [])), language="text")
            if item.get("generic_queries"):
                st.markdown("**Generic fallback queries**")
                st.code("\n".join(item.get("generic_queries", [])), language="text")
            for provider_diag in item.get("providers", []):
                provider_title = f"{provider_diag.get('provider')} | kept={provider_diag.get('kept_candidates', 0)} | raw={provider_diag.get('raw_results', 0)}"
                st.markdown(f"**{provider_title}**")
                if provider_diag.get("notes"):
                    st.caption(provider_diag.get("notes"))
                st.caption(f"Fallback triggered: {provider_diag.get('fallback_triggered', False)}")
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
    render_section("Fallback Outreach", "Alternative Channels", "Use the best backup contact path when no email is available.")
    render_key_value_card("Channel Routing", [
        ("Recommended channel", notes_data.get("recommended_channel", "unavailable")),
        ("Contact strategy", notes_data.get("contact_strategy", "unavailable")),
        ("Recommended CTA", notes_data.get("recommended_cta", "N/A")),
        ("Email unavailable reason", notes_data.get("email_unavailable_reason", "N/A")),
        ("Phone", prospect.phone or "N/A"),
        ("Contact form", notes_data.get("contact_form_url", "N/A")),
        ("Instagram", notes_data.get("instagram_url", "N/A")),
        ("Facebook", notes_data.get("facebook_url", "N/A")),
        ("WhatsApp", notes_data.get("whatsapp_url", "N/A")),
    ])
    action_cols = st.columns(6)
    with action_cols[0]:
        render_copy_text_button(notes_data.get("sms_message", notes_data.get("sms", "")) or "SMS unavailable", f"alt_sms_{prospect.id}", label="Copy SMS")
    with action_cols[1]:
        render_copy_text_button(notes_data.get("call_script", "") or "Call script unavailable", f"alt_call_{prospect.id}", label="Copy call script")
    with action_cols[2]:
        if notes_data.get("contact_form_url"):
            st.link_button("Open contact form", notes_data.get("contact_form_url"), use_container_width=True)
        else:
            st.button("Open contact form", key=f"alt_form_missing_{prospect.id}", disabled=True, use_container_width=True)
    with action_cols[3]:
        if notes_data.get("instagram_url"):
            st.link_button("Open Instagram", notes_data.get("instagram_url"), use_container_width=True)
        else:
            st.button("Open Instagram", key=f"alt_instagram_missing_{prospect.id}", disabled=True, use_container_width=True)
    with action_cols[4]:
        if notes_data.get("facebook_url"):
            st.link_button("Open Facebook", notes_data.get("facebook_url"), use_container_width=True)
        else:
            st.button("Open Facebook", key=f"alt_facebook_missing_{prospect.id}", disabled=True, use_container_width=True)
    with action_cols[5]:
        render_copy_text_button(notes_data.get("social_dm_message", "") or "DM unavailable", f"alt_dm_{prospect.id}", label="Copy DM message")
    with st.expander("Prepared fallback copy", expanded=False):
        st.text_area("Prepared SMS", value=notes_data.get("sms_message", notes_data.get("sms", "")), height=90, key=f"alt_sms_preview_{prospect.id}")
        st.text_area("Prepared call script", value=notes_data.get("call_script", ""), height=180, key=f"alt_call_preview_{prospect.id}")
        st.text_area("Prepared contact form message", value=notes_data.get("contact_form_message", ""), height=130, key=f"alt_form_preview_{prospect.id}")
        st.text_area("Prepared DM message", value=notes_data.get("social_dm_message", ""), height=120, key=f"alt_dm_preview_{prospect.id}")


def build_outreach_preview(prospect, notes_data: dict, lang: str, outreach_asset: str) -> tuple[str, str, str]:
    if lang == "fr":
        subject = prospect.email_subject_fr or "Sujet non genere"
        body = normalize_sender_content(prospect.email_body_fr or "Corps non genere", settings.PROFESSIONAL_EMAIL)
        html_body = normalize_sender_content(prospect.email_html_fr or "", settings.PROFESSIONAL_EMAIL)
    else:
        subject = prospect.email_subject_en or "Subject not generated"
        body = normalize_sender_content(prospect.email_body_en or "Body not generated", settings.PROFESSIONAL_EMAIL)
        html_body = normalize_sender_content(prospect.email_html_en or "", settings.PROFESSIONAL_EMAIL)
    if outreach_asset == "Short email":
        prefix = "fr" if lang == "fr" else "en"
        subject = notes_data.get(f"email_short_subject_{prefix}", subject)
        body = notes_data.get(f"email_short_{prefix}", body)
        html_body = ""
    elif outreach_asset == "Follow-up J+2":
        follow_up = notes_data.get("follow_ups_fr", {}) if lang == "fr" else notes_data.get("follow_ups_en", {})
        subject = follow_up.get("day_2", {}).get("subject", subject)
        body = follow_up.get("day_2", {}).get("body", body)
        html_body = ""
    elif outreach_asset == "Follow-up J+5":
        follow_up = notes_data.get("follow_ups_fr", {}) if lang == "fr" else notes_data.get("follow_ups_en", {})
        subject = follow_up.get("day_5", {}).get("subject", subject)
        body = follow_up.get("day_5", {}).get("body", body)
        html_body = ""
    elif outreach_asset == "Final follow-up J+10":
        follow_up = notes_data.get("follow_ups_fr", {}) if lang == "fr" else notes_data.get("follow_ups_en", {})
        subject = follow_up.get("day_10", {}).get("subject", subject)
        body = follow_up.get("day_10", {}).get("body", body)
        html_body = ""
    elif outreach_asset == "SMS":
        subject = "SMS"
        body = notes_data.get("sms_message", notes_data.get("sms", "SMS not generated"))
        html_body = ""
    elif outreach_asset == "Call script":
        subject = "Call script"
        body = notes_data.get("call_script", "Call script not generated")
        html_body = ""
    elif outreach_asset == "Contact form":
        subject = "Contact form"
        body = notes_data.get("contact_form_message", "Contact form message not generated")
        html_body = ""
    elif outreach_asset == "Social DM":
        subject = notes_data.get("preferred_social_channel", "social") or "social"
        body = notes_data.get("social_dm_message", "Social DM not generated")
        html_body = ""
    return subject, body, html_body


def format_datetime_label(value) -> str:
    if not value:
        return "Never"
    if isinstance(value, (int, float)):
        return pd.to_datetime(value, unit="s").strftime("%Y-%m-%d %H:%M")
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d %H:%M")
    return str(value)


def render_copy_text_button(text: str, key: str, label: str = "Copy Email"):
    safe_key = key.replace(" ", "_")
    components.html(f"""<button id="{safe_key}" style="width:100%;padding:0.72rem 0.9rem;border:1px solid rgba(201,168,106,0.34);border-radius:14px;background:linear-gradient(180deg, rgba(17,19,23,0.98), rgba(10,11,14,0.98));color:#F5EFE3;font-weight:700;letter-spacing:0.05em;cursor:pointer;">{label}</button><div id="{safe_key}_status" style="font-size:12px;color:#9C968A;margin-top:0.35rem;"></div><script>const button=document.getElementById("{safe_key}");const status=document.getElementById("{safe_key}_status");button.addEventListener("click",async()=>{{try{{await navigator.clipboard.writeText({json.dumps(text)});status.textContent="Copied";}}catch(error){{status.textContent="Copy unavailable here.";}}}});</script>""", height=74)


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
        progress_placeholder.caption(f"Progress: {index}/{total_count} | sent={summary.get('sent', 0)} failed={summary.get('failed', 0)} skipped={summary.get('skipped', 0)} simulated={summary.get('simulated', 0)} | recipient={result_row.get('actual_recipient', '')}")

    summary = service.send_emails(limit=limit, only_not_sent=only_not_sent, test_to=test_to, simulate=simulate, selected_ids=selected_ids, allow_resend=allow_resend, progress_callback=handle_progress)
    progress_bar.progress(1.0 if selected_ids else 0.0)
    st.session_state["last_send_summary"] = summary
    return summary


def update_prospect_from_ui(prospect_id: int, *, status: str | None = None, send_status: str | None = None, last_send_error: str | None = None) -> bool:
    return LeadService().update_prospect_status(prospect_id, status=status, send_status=send_status, last_send_error=last_send_error)


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
        return query.order_by(Prospect.priority_score.desc(), Prospect.collected_at.desc()).all()
    finally:
        db.close()


def get_top_prospects(limit: int = 5):
    db = SessionLocal()
    try:
        return db.query(Prospect).filter(Prospect.status.in_(["NEW", "MAQUETTE_READY", "REVIEWED"])).order_by(Prospect.priority_score.desc(), Prospect.opportunity_score.desc(), Prospect.phone.isnot(None).desc()).limit(limit).all()
    finally:
        db.close()


def get_recent_outreach_prospects(limit: int = 15):
    db = SessionLocal()
    try:
        return db.query(Prospect).filter(Prospect.last_attempt_at.isnot(None)).order_by(Prospect.last_attempt_at.desc()).limit(limit).all()
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
    components.html(f"""<button id="{safe_key}" style="width:100%;padding:0.72rem 0.9rem;border:1px solid rgba(201,168,106,0.34);border-radius:14px;background:linear-gradient(180deg, rgba(17,19,23,0.98), rgba(10,11,14,0.98));color:#F5EFE3;font-weight:700;letter-spacing:0.05em;cursor:pointer;">Copy Link</button><div id="{safe_key}_status" style="font-size:12px;color:#9C968A;margin-top:0.35rem;"></div><script>const button=document.getElementById("{safe_key}");const status=document.getElementById("{safe_key}_status");button.addEventListener("click",async()=>{{try{{await navigator.clipboard.writeText({json.dumps(url)});status.textContent="Link copied";}}catch(error){{status.textContent="Copy unavailable here. Use the URL below.";}}}});</script>""", height=74)


def render_mockup_actions(prospect, key_prefix: str):
    mockup_url = prospect.mockup_url or ""
    if not mockup_url:
        st.caption("Mockup URL unavailable")
        return
    cols = st.columns(2)
    with cols[0]:
        if is_public_mockup_url(mockup_url):
            st.link_button("Open Mockup", mockup_url, use_container_width=True)
        else:
            st.button("Open Mockup", disabled=True, key=f"{key_prefix}_open_disabled", use_container_width=True)
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
        return {"last_check": latest_log.stat().st_mtime, "status": "UNKNOWN", "reason": "could_not_read_log"}

    joined = "\n".join(lines[-40:])
    status = "UNKNOWN"
    reason = "catchup_log_detected"

    if any("Skipping startup catch-up because a report already exists for today." in line for line in lines):
        status = "SKIPPED"
        reason = "report already exists today"
    elif any("No report found for today. Launching autonomous outreach catch-up run." in line for line in lines):
        status = "LAUNCHED"
        reason = "missed run recovered after sign-in"
    elif any("Startup catch-up exit code:" in line for line in lines):
        status = "COMPLETED"
        reason = next((line.replace("Startup catch-up exit code:", "exit code").strip() for line in lines if "Startup catch-up exit code:" in line), "completed")

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
