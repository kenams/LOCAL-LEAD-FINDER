"""
Export service
"""
import pandas as pd
import json
from sqlalchemy.orm import Session
from app.core.branding import get_business_identity, get_mockup_quality_level
from app.core.country_config import format_price_range, get_country_display_name
from app.db.session import SessionLocal
from app.models.prospect import Prospect
from app.core.config import settings
from app.core.logging import logger
from app.core.sender_identity import normalize_sender_content

class ExportService:
    """Handle data exports"""

    def export_leads(self, format_type: str):
        """Export leads to specified format"""
        db = SessionLocal()
        try:
            leads = db.query(Prospect).all()
            identity = get_business_identity()

            if not leads:
                logger.warning("No leads to export")
                return

            data = []
            for lead in leads:
                # Parse notes for additional data
                notes_data = {}
                if lead.notes:
                    try:
                        notes_data = json.loads(lead.notes)
                    except:
                        pass
                notes_data = normalize_sender_content(notes_data, settings.PROFESSIONAL_EMAIL)
                normalized_notes = (
                    json.dumps(notes_data, ensure_ascii=False)
                    if notes_data
                    else normalize_sender_content(lead.notes, settings.PROFESSIONAL_EMAIL)
                )

                # Determine recommended channel
                canal_recommande = notes_data.get("recommended_channel", "")
                if not canal_recommande:
                    if lead.email:
                        canal_recommande = "email"
                    elif lead.phone:
                        canal_recommande = "phone"
                    else:
                        canal_recommande = "contact_form"

                # Get ready message
                message_pret = ""
                if canal_recommande == "email":
                    preferred_email_body = lead.email_body_en if lead.email_language == "en" else lead.email_body_fr
                    message_pret = normalize_sender_content(
                        preferred_email_body or lead.email_body_fr or lead.email_body_en or "",
                        settings.PROFESSIONAL_EMAIL,
                    )
                elif canal_recommande == "phone":
                    message_pret = notes_data.get("sms_message", notes_data.get("sms", ""))
                elif canal_recommande == "contact_form":
                    message_pret = notes_data.get("contact_form_message", "")
                elif canal_recommande in {"instagram", "facebook"}:
                    message_pret = notes_data.get("social_dm_message", "")
                else:
                    message_pret = ""

                # Priority score (higher is better)
                score_priorite = lead.priority_score or (
                    (lead.opportunity_score or 0) + (10 if lead.phone else 0) + (5 if lead.email else 0)
                )

                row = {
                    "business_name": lead.business_name,
                    "category": lead.category,
                    "location": lead.location,
                    "country": lead.country,
                    "country_name": get_country_display_name(lead.country),
                    "currency": lead.currency,
                    "address": lead.address,
                    "phone": lead.phone,
                    "email": lead.email,
                    "website": lead.website,
                    "contact_page": lead.contact_page,
                    "reviews_count": lead.reviews_count,
                    "source": lead.source,
                    "collected_at": lead.collected_at.isoformat() if lead.collected_at else None,
                    "status": lead.status,
                    "opportunity_score": lead.opportunity_score,
                    "site_quality_score": lead.site_quality_score,
                    "new_business_score": lead.new_business_score,
                    "target_type": lead.target_type,
                    "website_page_count": lead.website_page_count,
                    "website_content_length": lead.website_content_length,
                    "has_booking_system": lead.has_booking_system,
                    "has_seo_foundation": lead.has_seo_foundation,
                    "has_modern_ui": lead.has_modern_ui,
                    "social_first_business": lead.social_first_business,
                    "feasibility": lead.feasibility,
                    "estimated_time": lead.estimated_time,
                    "estimated_price_min": lead.estimated_price_min,
                    "estimated_price_max": lead.estimated_price_max,
                    "estimated_price_display": format_price_range(
                        lead.estimated_price_min,
                        lead.estimated_price_max,
                        lead.country,
                    ),
                    "priority_score": lead.priority_score,
                    "detected_issues": lead.detected_issues,
                    "language_used": lead.email_language,
                    "selected_offer_type": lead.selected_offer_type,
                    "selected_email_subject": notes_data.get("selected_email_subject", lead.email_subject_en if lead.email_language == "en" else lead.email_subject_fr),
                    "selected_email_body": notes_data.get("selected_email_body", normalize_sender_content(lead.email_body_en if lead.email_language == "en" else lead.email_body_fr, settings.PROFESSIONAL_EMAIL)),
                    "email_subject_fr": lead.email_subject_fr,
                    "email_body_fr": normalize_sender_content(lead.email_body_fr, settings.PROFESSIONAL_EMAIL),
                    "email_html_fr": normalize_sender_content(lead.email_html_fr, settings.PROFESSIONAL_EMAIL),
                    "email_short_subject_fr": notes_data.get("email_short_subject_fr", ""),
                    "email_short_fr": notes_data.get("email_short_fr", ""),
                    "email_subject_en": lead.email_subject_en,
                    "email_body_en": normalize_sender_content(lead.email_body_en, settings.PROFESSIONAL_EMAIL),
                    "email_html_en": normalize_sender_content(lead.email_html_en, settings.PROFESSIONAL_EMAIL),
                    "email_short_subject_en": notes_data.get("email_short_subject_en", ""),
                    "email_short_en": notes_data.get("email_short_en", ""),
                    "selected_outreach_channel": lead.selected_outreach_channel,
                    "outreach_status": lead.outreach_status,
                    "send_status": lead.send_status,
                    "first_sent_at": lead.first_sent_at.isoformat() if lead.first_sent_at else None,
                    "last_attempt_at": lead.last_attempt_at.isoformat() if lead.last_attempt_at else None,
                    "send_attempts": lead.send_attempts,
                    "last_send_error": lead.last_send_error,
                    "follow_up_day_2_subject": notes_data.get("follow_up_day_2", {}).get("subject", ""),
                    "follow_up_day_2_body": notes_data.get("follow_up_day_2", {}).get("body", ""),
                    "follow_up_day_5_subject": notes_data.get("follow_up_day_5", {}).get("subject", ""),
                    "follow_up_day_5_body": notes_data.get("follow_up_day_5", {}).get("body", ""),
                    "follow_up_day_10_subject": notes_data.get("follow_up_day_10", {}).get("subject", ""),
                    "follow_up_day_10_body": notes_data.get("follow_up_day_10", {}).get("body", ""),
                    "recommended_channel": canal_recommande,
                    "contact_strategy": notes_data.get("contact_strategy", canal_recommande),
                    "contact_form_url": notes_data.get("contact_form_url", ""),
                    "contact_form_detected": notes_data.get("contact_form_detected", False),
                    "instagram_url": notes_data.get("instagram_url", ""),
                    "facebook_url": notes_data.get("facebook_url", ""),
                    "linkedin_url": notes_data.get("linkedin_url", ""),
                    "whatsapp_url": notes_data.get("whatsapp_url", ""),
                    "preferred_social_channel": notes_data.get("preferred_social_channel", ""),
                    "email_unavailable_reason": notes_data.get("email_unavailable_reason", ""),
                    "recommended_cta": notes_data.get("recommended_cta", ""),
                    "early_stage_business": lead.target_type == "early_stage_business",
                    "growth_opportunity": lead.target_type == "growth_opportunity",
                    "sms_message": notes_data.get("sms_message", notes_data.get("sms", "")),
                    "call_script": notes_data.get("call_script", ""),
                    "contact_form_message": notes_data.get("contact_form_message", ""),
                    "social_dm_message": notes_data.get("social_dm_message", ""),
                    "mockup_url": lead.mockup_url,
                    "mockup_status": lead.mockup_status,
                    "netlify_site_id": lead.netlify_site_id,
                    "netlify_deploy_id": lead.netlify_deploy_id,
                    "canal_recommande": canal_recommande,
                    "message_pret": message_pret,
                    "score_priorite": score_priorite,
                    "sender_display_name": identity.sender_display_name,
                    "sender_email": identity.professional_email,
                    "sender_phone": identity.professional_phone,
                    "sender_website": identity.website,
                    "portfolio_url": identity.portfolio_url,
                    "signature_label": identity.signature_label,
                    "mockup_quality_level": get_mockup_quality_level(),
                    "notes": normalized_notes,
                }
                data.append(row)

            df = pd.DataFrame(data)

            if format_type == "csv":
                filename = settings.EXPORT_DIR / "leads.csv"
                df.to_csv(filename, index=False, encoding='utf-8-sig')
            elif format_type == "xlsx":
                filename = settings.EXPORT_DIR / "leads.xlsx"
                df.to_excel(filename, index=False, engine='openpyxl')

            logger.info(f"Exported {len(data)} leads to {filename}")

        except Exception as e:
            logger.error(f"Export failed: {e}")
        finally:
            db.close()
