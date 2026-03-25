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
from app.ui.ui_theme import badge_html, inject_global_styles, priority_badge_html, render_brand_header, render_key_value_card, render_metric_card, render_section, render_sidebar_brand, status_badge_html

SEARCH_LOCATIONS = ["Toulouse", "Montpellier", "Marseille", "Paris", "Geneva", "Zurich", "Lausanne", "New York", "Miami", "Dallas", "Los Angeles", "Sydney", "Melbourne", "Brisbane", "London", "Manchester"]
SEARCH_CATEGORIES = ["coiffeur", "salon de coiffure", "institut de beaute", "spa", "plombier", "electricien", "dentiste", "avocat", "restaurant", "boulangerie", "coach sportif", "garagiste"]


def main():
    st.set_page_config(page_title="KAH-Digital", page_icon="K", layout="wide")
    init_db()
    inject_global_styles()
    render_sidebar()
    render_brand_header()

    metrics = get_dashboard_metrics()
    render_section("Executive Overview", "KAH Dashboard", "A premium internal command center for international prospecting, live mockups and outreach.")
    cols = st.columns(5)
    with cols[0]:
        render_metric_card("Total prospects", str(metrics["total"]), "Live database")
    with cols[1]:
        render_metric_card("High potential", str(metrics["filtered"]), "Qualified pipeline")
    with cols[2]:
        render_metric_card("Contacted", str(metrics["contacted"]), "Outreach activity")
    with cols[3]:
        render_metric_card("Conversion rate", f"{metrics['conversion_rate']}%", "Won vs contacted")
    with cols[4]:
        render_metric_card("Pipeline value", metrics["estimated_revenue"], "Top 10 by priority")

    render_search_section()
    render_section("Search Diagnostics", "Observability", "Queries, providers and raw candidate counts for the latest collection run.")
    render_search_diagnostics()

    render_section("Lead Intelligence", "Filter Console", "Review the active pipeline with premium market tags, deployment status and outreach readiness.")
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

    render_section("Outreach Studio", "Email & Mockup", "Review the selected lead with branded deployment controls, localized pricing and ready-to-send messaging.")
    preview_pool = selected_prospects or prospects
    prospect = resolve_preview_prospect(preview_pool)
    render_prospect_summary(prospect, f"preview_{prospect.id}")
    notes_data = parse_notes(prospect.notes)
    lang = st.selectbox("Preview language", ["fr", "en"], index=0 if (prospect.email_language or "fr") == "fr" else 1)
    outreach_asset = st.selectbox("Outreach asset", ["Primary email", "Short email", "Follow-up J+2", "Follow-up J+5", "Final follow-up J+10", "SMS", "Call script", "Contact form", "Social DM"])
    subject, body, html_body = build_outreach_preview(prospect, notes_data, lang, outreach_asset)

    preview_cols = st.columns([1, 1.2])
    with preview_cols[0]:
        render_key_value_card("Email Context", [
            ("Language", prospect.email_language or "N/A"),
            ("Price", format_price_range(prospect.estimated_price_min, prospect.estimated_price_max, prospect.country)),
            ("Deployment", get_mockup_indicator(prospect.mockup_status)),
            ("Mockup quality", get_mockup_quality_level()),
            ("Mockup URL", prospect.mockup_url or "Unavailable"),
            ("Recommended channel", notes_data.get("recommended_channel", "N/A")),
            ("Preferred social", notes_data.get("preferred_social_channel", "N/A")),
            ("Contact form", notes_data.get("contact_form_url", "Unavailable")),
            ("Instagram", notes_data.get("instagram_url", "Unavailable")),
            ("Facebook", notes_data.get("facebook_url", "Unavailable")),
            ("Recipient", prospect.email or "No email"),
            ("Send status", get_send_indicator(prospect.send_status)),
            ("First sent", format_datetime_label(prospect.first_sent_at)),
            ("Last attempt", format_datetime_label(prospect.last_attempt_at)),
            ("Attempts", str(prospect.send_attempts or 0)),
            ("Last error", prospect.last_send_error or "None"),
        ])
    with preview_cols[1]:
        st.text_input("Subject", value=subject, key=f"subject_{prospect.id}")
        st.text_area("Email body", value=body, height=340, key=f"body_{prospect.id}")
        if html_body:
            with st.expander("HTML email preview", expanded=False):
                components.html(html_body, height=620, scrolling=True)
    if is_public_mockup_url(prospect.mockup_url):
        with st.expander("Live mockup preview", expanded=False):
            components.iframe(prospect.mockup_url, height=720, scrolling=True)
    render_alternative_outreach_panel(prospect, notes_data)

    render_section("Send Outreach", "Direct Send Controls", "Send directly from the dashboard with safe defaults, confirmation gates, test mode and live result tracking.")
    render_send_panel(prospects, selected_prospects, prospect, subject, body, html_body)

    if st.session_state.get("last_send_summary"):
        summary = st.session_state["last_send_summary"]
        st.caption(f"Last send run: selected={summary.get('selected', 0)} | sent={summary.get('sent', 0)} | failed={summary.get('failed', 0)} | skipped={summary.get('skipped', 0)} | simulated={summary.get('simulated', 0)}")
        results_df = pd.DataFrame(summary.get("results", []))
        if not results_df.empty:
            st.dataframe(results_df, use_container_width=True)


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
    edited = st.data_editor(table, hide_index=True, use_container_width=True, key="lead_selection_table", column_config={"Select": st.column_config.CheckboxColumn("Select"), "Priority": st.column_config.NumberColumn("Priority", format="%.2f")}, disabled=["Business", "Country", "Location", "Category", "Priority", "Email", "Phone", "Recommended Channel", "Contact Form", "Instagram", "Facebook", "Send Status", "First Sent", "Last Attempt", "Attempts", "Last Error", "Mockup URL"])
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
        render_key_value_card("Contact Readiness", [("Email", prospect.email or "N/A"), ("Phone", prospect.phone or "N/A"), ("Recommended channel", notes.get("recommended_channel", "unavailable")), ("Contact form", notes.get("contact_form_url", "N/A")), ("Instagram", notes.get("instagram_url", "N/A")), ("Facebook", notes.get("facebook_url", "N/A")), ("Language", prospect.email_language or "N/A"), ("Estimated price", format_price_range(prospect.estimated_price_min, prospect.estimated_price_max, prospect.country)), ("Mockup", get_mockup_indicator(prospect.mockup_status)), ("Send attempts", str(prospect.send_attempts or 0))])
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


def get_dashboard_metrics():
    db = SessionLocal()
    try:
        total = db.query(Prospect).count()
        filtered = db.query(Prospect).filter(Prospect.opportunity_score >= 70).count()
        contacted = db.query(Prospect).filter(Prospect.status.in_(["CONTACTED", "FOLLOW_UP_1", "FOLLOW_UP_2", "WON", "LOST"])).count()
        won = db.query(Prospect).filter(Prospect.status == "WON").count()
        conversion_rate = (won / contacted * 100) if contacted > 0 else 0
        top_value = db.query(Prospect).order_by(Prospect.priority_score.desc()).limit(10).all()
        estimated_revenue_value = sum((lead.estimated_price_max or 0) for lead in top_value)
        return {"total": total, "filtered": filtered, "contacted": contacted, "conversion_rate": round(conversion_rate, 1), "estimated_revenue": format_price_range(estimated_revenue_value, estimated_revenue_value, "FR")}
    finally:
        db.close()


def get_top_prospects(limit: int = 5):
    db = SessionLocal()
    try:
        return db.query(Prospect).filter(Prospect.status.in_(["NEW", "MAQUETTE_READY", "REVIEWED"])).order_by(Prospect.priority_score.desc(), Prospect.opportunity_score.desc(), Prospect.phone.isnot(None).desc()).limit(limit).all()
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


def run_streamlit_app():
    main()


if __name__ == "__main__":
    main()
