"""
Main lead service
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import time
from typing import Callable, Dict, List

from app.core.config import settings
from app.core.country_config import detect_country, get_country_profile, resolve_email_language
from app.core.logging import logger
from app.core.search_config import SearchPlan, build_search_plan, canonicalize_category
from app.core.sender_identity import contains_legacy_sender_identity
from app.db.session import SessionLocal
from app.models.prospect import Prospect
from app.models.search_run import SearchRun
from app.services.contact_extractor import ContactExtractor
from app.services.contact_strategy import ContactStrategy
from app.services.deduplicator import Deduplicator
from app.services.email_generator import EmailGenerator
from app.services.email_sender import EmailSender
from app.services.lead_filter import LeadFilter
from app.services.mockup_generator import MockupGenerator
from app.services.netlify_deployer import NetlifyDeployer
from app.services.netlify_preparer import NetlifyPreparer
from app.services.osm_provider import OSMProvider
from app.services.serpapi_provider import SerpApiProvider
from app.services.simple_provider import SimpleProvider
from app.services.site_analyzer import SiteAnalyzer


class LeadService:
    """Main service for lead operations."""

    PRIORITY_NICHE_BONUSES = {
        "marketing": 14,
        "consultant": 12,
        "agency": 12,
        "web design": 14,
        "seo": 14,
        "coach": 10,
        "accountant": 12,
        "lawyer": 14,
        "financial advisor": 14,
        "real estate": 10,
    }

    def __init__(self):
        self.providers = [SerpApiProvider(), OSMProvider(), SimpleProvider()]
        self.contact_extractor = ContactExtractor()
        self.site_analyzer = SiteAnalyzer()
        self.email_generator = EmailGenerator()
        self.email_sender = EmailSender()
        self.deduplicator = Deduplicator()
        self.lead_filter = LeadFilter()
        self.contact_strategy = ContactStrategy()
        self.mockup_generator = MockupGenerator()
        self.netlify_deployer = NetlifyDeployer()
        self.netlify_preparer = NetlifyPreparer()

    def reset_leads(self, clear_search_history: bool = True) -> int:
        """Clear stored leads and optionally search history."""
        db = SessionLocal()
        try:
            deleted_leads = db.query(Prospect).delete()
            if clear_search_history:
                db.query(SearchRun).delete()
            db.commit()
            logger.info(f"Reset leads completed: deleted_leads={deleted_leads}, clear_search_history={clear_search_history}")
            return deleted_leads
        except Exception as exc:
            db.rollback()
            logger.error(f"Reset leads failed: {exc}")
            return 0
        finally:
            db.close()

    async def collect_leads(self, locations: List[str], categories: List[str], limit: int, language: str) -> int:
        """Collect leads from multiple locations and categories."""
        logger.info(f"Starting lead collection: {locations}, {categories}, limit={limit}")
        search_run = self._create_search_run(locations, categories, limit, language)

        try:
            all_leads: List[dict] = []
            search_diagnostics: List[dict] = []

            for location in locations:
                for category in categories:
                    collection_result = await self._collect_location_category(location, category, limit, language)
                    all_leads.extend(collection_result["leads"])
                    search_diagnostics.append(collection_result["diagnostics"])

            unique_leads = self.deduplicator.deduplicate_leads(all_leads)
            processed_leads, prevalidated_rejected = await self._process_leads(unique_leads, language)
            filtered_leads, rejected_leads = self.lead_filter.filter_leads(processed_leads)
            rejected_leads = prevalidated_rejected + rejected_leads
            outreach_ready_leads = await self._prepare_outreach_assets(filtered_leads, language, auto_mode=False)
            saved_count = self._save_leads(outreach_ready_leads)

            self._finalize_search_diagnostics(search_diagnostics, processed_leads, outreach_ready_leads, rejected_leads)
            self._update_search_run(search_run, saved_count, "COMPLETED", diagnostics=search_diagnostics)

            logger.info(f"Lead collection completed: {saved_count} leads saved")
            return saved_count
        except Exception as e:
            logger.error(f"Lead collection failed: {e}")
            self._update_search_run(search_run, 0, "FAILED", str(e), diagnostics=search_diagnostics if "search_diagnostics" in locals() else [])
            return 0

    async def auto_outreach(
        self,
        locations: List[str],
        categories: List[str],
        limit: int,
        language: str,
        *,
        simulate: bool = False,
        progress_callback: Callable[[int, int, Dict[str, object], Dict[str, object]], None] | None = None,
    ) -> Dict[str, object]:
        """Run the simplified search -> generate -> send flow with email-only delivery."""
        logger.info(f"Starting auto outreach flow: locations={locations}, categories={categories}, limit={limit}, simulate={simulate}")
        search_run = self._create_search_run(locations, categories, limit, language)

        try:
            all_leads: List[dict] = []
            search_diagnostics: List[dict] = []

            for location in locations:
                for category in categories:
                    collection_result = await self._collect_location_category(
                        location,
                        category,
                        limit,
                        language,
                        prefer_contact_details=settings.AUTO_MODE_REQUIRE_EMAIL_AND_PHONE,
                    )
                    all_leads.extend(collection_result["leads"])
                    search_diagnostics.append(collection_result["diagnostics"])

            unique_leads = self.deduplicator.deduplicate_leads(all_leads)
            processed_leads, prevalidated_rejected = await self._process_leads(unique_leads, language)
            filtered_leads, rejected_leads = self.lead_filter.filter_leads(processed_leads)
            rejected_leads = prevalidated_rejected + rejected_leads
            auto_ready_leads, auto_rejected_leads = self._filter_auto_mode_contacts(
                filtered_leads,
                fallback_pool=processed_leads,
                target_count=limit,
            )
            rejected_leads.extend(auto_rejected_leads)
            outreach_ready_leads = await self._prepare_outreach_assets(auto_ready_leads, language, auto_mode=True)
            saved_count, prospect_ids = self._save_leads_with_ids(outreach_ready_leads)

            self._finalize_search_diagnostics(search_diagnostics, processed_leads, outreach_ready_leads, rejected_leads)
            self._update_search_run(search_run, saved_count, "COMPLETED", diagnostics=search_diagnostics)

            if not prospect_ids:
                return {
                    "selected": 0,
                    "raw_found": len(unique_leads),
                    "email_sent": 0,
                    "sms_sent": 0,
                    "failed": 0,
                    "skipped": 0,
                    "simulated": 0,
                    "results": [],
                    "locations": locations,
                    "categories": categories,
                    "leads_found": len(unique_leads),
                    "validated_leads": len(filtered_leads),
                    "validation_skipped": len(rejected_leads),
                    "validation_reasons": self._count_rejection_reasons(rejected_leads),
                    "contact_ready": len(auto_ready_leads),
                    "landing_page_offers": self._count_offer_type(auto_ready_leads, "landing_page"),
                    "website_offers": self._count_offer_type(auto_ready_leads, "website"),
                    "landing_page_sent": 0,
                    "website_sent": 0,
                    "early_stage_businesses": self._count_target_type(processed_leads, "early_stage_business"),
                    "growth_opportunities": self._count_target_type(processed_leads, "growth_opportunity"),
                    "high_opportunity_leads": self._count_high_opportunity_leads(processed_leads),
                    "leads_saved": saved_count,
                }

            send_summary = self.send_outreach(
                selected_ids=prospect_ids,
                limit=limit * max(1, len(locations) * len(categories)),
                only_not_sent=True,
                simulate=simulate,
                allow_resend=settings.SEND_ALLOW_RESEND,
                progress_callback=progress_callback,
            )
            send_summary.update(
                {
                    "locations": locations,
                    "categories": categories,
                    "raw_found": len(unique_leads),
                    "leads_found": len(unique_leads),
                    "validated_leads": len(filtered_leads),
                    "validation_skipped": len(rejected_leads),
                    "validation_reasons": self._count_rejection_reasons(rejected_leads),
                    "contact_ready": len(auto_ready_leads),
                    "landing_page_offers": self._count_offer_type(auto_ready_leads, "landing_page"),
                    "website_offers": self._count_offer_type(auto_ready_leads, "website"),
                    "early_stage_businesses": self._count_target_type(processed_leads, "early_stage_business"),
                    "growth_opportunities": self._count_target_type(processed_leads, "growth_opportunity"),
                    "high_opportunity_leads": self._count_high_opportunity_leads(processed_leads),
                    "leads_saved": saved_count,
                }
            )
            return send_summary
        except Exception as exc:
            logger.error(f"Auto outreach failed: {exc}")
            self._update_search_run(search_run, 0, "FAILED", str(exc), diagnostics=search_diagnostics if "search_diagnostics" in locals() else [])
            return {
                "selected": 0,
                "raw_found": 0,
                "leads_found": 0,
                "validated_leads": 0,
                "validation_skipped": 0,
                "validation_reasons": {},
                "landing_page_offers": 0,
                "website_offers": 0,
                "landing_page_sent": 0,
                "website_sent": 0,
                "early_stage_businesses": 0,
                "growth_opportunities": 0,
                "high_opportunity_leads": 0,
                "leads_saved": 0,
                "email_sent": 0,
                "sms_sent": 0,
                "failed": 1,
                "skipped": 0,
                "simulated": 0,
                "results": [],
                "error": str(exc),
            }

    def get_auto_outreach_preflight(self, *, simulate: bool = False) -> Dict[str, object]:
        """Return a lightweight configuration snapshot before one-shot auto runs."""
        warnings = list(settings.get_smtp_identity_warnings())
        smtp_ready = self.email_sender.is_configured()
        require_full_contact = settings.AUTO_MODE_REQUIRE_EMAIL_AND_PHONE
        generate_mockups = self._should_generate_mockups(auto_mode=True)
        deploy_mockups = self._should_deploy_mockups(auto_mode=True)

        if not settings.AUTO_SEND_ENABLED and not simulate:
            warnings.append("AUTO_SEND_ENABLED is false: real delivery is disabled for this run.")
        if not smtp_ready:
            warnings.append("SMTP is incomplete: email-capable leads will fail with smtp_not_configured.")
        if require_full_contact:
            warnings.append("AUTO_MODE_REQUIRE_EMAIL_AND_PHONE is true: leads missing email or phone will be skipped before outreach.")
            warnings.append(
                f"AUTO_MODE_CONTACT_CANDIDATE_MULTIPLIER={settings.AUTO_MODE_CONTACT_CANDIDATE_MULTIPLIER}: auto mode scans more candidates to find full-contact sites."
            )
        if settings.EMAIL_ONLY_OUTREACH:
            warnings.append("EMAIL_ONLY_OUTREACH is true: leads without email will be skipped.")
        if deploy_mockups and not settings.NETLIFY_TOKEN:
            warnings.append("AUTO_MODE_DEPLOY_MOCKUPS is enabled but NETLIFY_TOKEN is missing: mockup deployment will fail.")

        return {
            "auto_send_enabled": settings.AUTO_SEND_ENABLED,
            "simulate": simulate,
            "require_website": settings.REQUIRE_WEBSITE,
            "require_contact": settings.REQUIRE_CONTACT,
            "priority_niches_enabled": settings.PRIORITY_NICHES_ENABLED,
            "smtp_ready": smtp_ready,
            "email_only_outreach": settings.EMAIL_ONLY_OUTREACH,
            "min_opportunity_score": settings.AUTO_MODE_MIN_OPPORTUNITY_SCORE,
            "require_full_contact": require_full_contact,
            "contact_candidate_multiplier": settings.AUTO_MODE_CONTACT_CANDIDATE_MULTIPLIER,
            "send_max_per_run": settings.SEND_MAX_PER_RUN,
            "generate_mockups": generate_mockups,
            "deploy_mockups": deploy_mockups,
            "warnings": warnings,
        }

    async def _collect_location_category(
        self,
        location: str,
        category: str,
        limit: int,
        fallback_language: str,
        *,
        prefer_contact_details: bool = False,
    ) -> Dict[str, object]:
        """Collect leads for a specific location/category using the provider chain."""
        plan = build_search_plan(location, category, fallback_language)
        logger.info(
            f"Search plan for {location}/{category}: normalized_location={plan.normalized_location}, country={plan.country}, language={plan.language}, queries={plan.queries}"
        )

        candidate_target = max(limit * 2, settings.SEARCH_MAX_RAW_CANDIDATES)
        primary_queries = plan.queries
        if prefer_contact_details:
            candidate_target = max(
                candidate_target,
                limit * max(2, settings.AUTO_MODE_CONTACT_CANDIDATE_MULTIPLIER),
            )
            primary_queries = list(dict.fromkeys(plan.contact_queries + plan.queries))
        collected_leads: List[dict] = []
        provider_diagnostics: List[dict] = []

        collected_leads.extend(
            await self._run_provider_chain(
                plan=plan,
                category=category,
                limit=limit,
                candidate_target=candidate_target,
                provider_diagnostics=provider_diagnostics,
                search_queries=primary_queries,
                broaden=False,
            )
        )

        if not collected_leads and settings.SEARCH_BROADEN_IF_EMPTY:
            logger.info(f"Broadening search for {location}/{category} with queries {plan.broadened_queries}")
            collected_leads.extend(
                await self._run_provider_chain(
                    plan=plan,
                    category=category,
                    limit=limit,
                    candidate_target=candidate_target,
                    provider_diagnostics=provider_diagnostics,
                    search_queries=plan.broadened_queries,
                    broaden=True,
                )
            )

        if not collected_leads and settings.SEARCH_FALLBACK_ENABLED:
            logger.info(f"Running generic fallback search for {location}/{category} with queries {plan.generic_queries}")
            collected_leads.extend(
                await self._run_provider_chain(
                    plan=plan,
                    category=category,
                    limit=limit,
                    candidate_target=candidate_target,
                    provider_diagnostics=provider_diagnostics,
                    search_queries=plan.generic_queries,
                    broaden=True,
                )
            )

        diagnostics = {
            "location": location,
            "normalized_location": plan.normalized_location,
            "country": plan.country,
            "language": plan.language,
            "market_language_tag": plan.market_language_tag,
            "requested_category": category,
            "translated_terms": plan.category_terms,
            "contact_queries": plan.contact_queries,
            "location_aliases": plan.location_aliases,
            "osm_tags": plan.osm_tags,
            "queries": primary_queries,
            "broadened_queries": plan.broadened_queries,
            "generic_queries": plan.generic_queries,
            "providers": provider_diagnostics,
            "raw_candidates": len(collected_leads),
            "valid_prospects_kept": 0,
            "rejected_after_filter": 0,
            "prefer_contact_details": prefer_contact_details,
        }

        logger.info(
            f"Discovery summary for {location}/{category}: raw_candidates={len(collected_leads)}, providers_attempted={len(provider_diagnostics)}"
        )
        return {"leads": collected_leads, "diagnostics": diagnostics}

    async def _run_provider_chain(
        self,
        plan: SearchPlan,
        category: str,
        limit: int,
        candidate_target: int,
        provider_diagnostics: List[dict],
        search_queries: List[str],
        broaden: bool,
    ) -> List[dict]:
        """Run the configured providers and aggregate candidates."""
        collected: List[dict] = []

        for provider in self.providers:
            provider_name = provider.__class__.__name__
            if not provider.is_available():
                provider_diagnostics.append(
                    {
                        "provider": provider_name,
                        "available": False,
                        "queries": search_queries,
                        "raw_results": 0,
                        "kept_candidates": 0,
                        "fallback_triggered": broaden,
                        "notes": "provider_unavailable",
                    }
                )
                continue

            remaining = max(candidate_target - len(collected), limit)
            try:
                provider_result = await provider.search_leads(
                    location=plan.location,
                    category=category,
                    limit=limit,
                    search_queries=search_queries,
                    max_candidates=remaining,
                )
            except Exception as exc:
                logger.warning(f"{provider_name} failed for {plan.location}/{category}: {exc}")
                provider_diagnostics.append(
                    {
                        "provider": provider_name,
                        "available": True,
                        "queries": search_queries,
                        "raw_results": 0,
                        "kept_candidates": 0,
                        "fallback_triggered": broaden,
                        "notes": str(exc),
                    }
                )
                continue

            provider_diagnostics.append(
                {
                    "provider": provider_name,
                    "available": True,
                    "queries": provider_result.queries_attempted,
                    "raw_results": provider_result.raw_count,
                    "kept_candidates": len(provider_result.leads),
                    "fallback_triggered": provider_result.fallback_triggered or broaden,
                    "notes": provider_result.notes,
                }
            )

            logger.info(
                f"{provider_name} search diagnostics for {plan.location}/{category}: raw_results={provider_result.raw_count}, kept_candidates={len(provider_result.leads)}, broaden={broaden}"
            )

            collected.extend(provider_result.leads)

            if not settings.SEARCH_FALLBACK_ENABLED:
                break
            if len(collected) >= candidate_target:
                break

        return collected

    async def _process_leads(self, leads: List[dict], language: str) -> tuple[List[dict], List[dict]]:
        """Process leads: validate, extract contacts, analyze sites and compute qualification."""
        processed: List[dict] = []
        rejected: List[dict] = []

        for lead in leads:
            try:
                self._apply_market_context(lead, language)
                validation_reason = self.lead_filter.validate_before_analysis(lead)
                if validation_reason:
                    rejected.append({**lead, "rejection_reason": validation_reason})
                    continue

                if lead.get("website"):
                    contacts = await self.contact_extractor.extract_contacts(lead["website"])
                    lead.update(contacts)
                    extraction = contacts.get("contact_extraction", {})
                    logger.info(
                        f"Lead channels detected for {lead.get('business_name')}: "
                        f"email={bool(contacts.get('email'))} phone={bool(contacts.get('phone'))} "
                        f"contact_form={bool(contacts.get('contact_form_url'))} instagram={bool(contacts.get('instagram_url'))} "
                        f"facebook={bool(contacts.get('facebook_url'))} selected={extraction.get('selected_channel', 'unavailable')} "
                        f"email_reason={extraction.get('email_unavailable_reason') or 'available'}"
                    )

                validation_reason = self.lead_filter.validate_after_contact_extraction(lead)
                if validation_reason:
                    rejected.append({**lead, "rejection_reason": validation_reason})
                    continue

                analysis = await self.site_analyzer.analyze_site(
                    lead.get("website", ""),
                    country=lead.get("country", "FR"),
                    language=lead.get("email_language", language),
                    reviews_count=lead.get("reviews_count"),
                    instagram_url=lead.get("instagram_url"),
                )
                lead.update(analysis)

                self._apply_market_context(lead, language)
                lead["priority_score"] = self._calculate_priority_score(lead)
                processed.append(lead)
            except Exception as e:
                logger.warning(f"Processing failed for lead {lead.get('business_name')}: {e}")
                rejected.append({**lead, "rejection_reason": "processing_error"})

        return processed, rejected

    async def _prepare_outreach_assets(self, leads: List[dict], language: str, *, auto_mode: bool = False) -> List[dict]:
        """Generate mockups, deploy them and build outreach assets only for qualified leads."""
        prepared: List[dict] = []
        generate_mockups = self._should_generate_mockups(auto_mode)
        deploy_mockups = self._should_deploy_mockups(auto_mode)

        for lead in leads:
            try:
                mockup_path = ""
                netlify_zip = ""
                deploy_result = {
                    "status": "disabled_auto_mode" if auto_mode else "pending",
                    "mockup_status": "pending",
                    "site_id": "",
                    "deploy_id": "",
                    "url": "",
                    "error": "",
                }

                if generate_mockups:
                    mockup_path = self.mockup_generator.generate_mockup(
                        lead.get("business_name", ""),
                        lead.get("category", ""),
                        lead.get("location", ""),
                        language=lead.get("email_language", language),
                        quality_level=settings.MOCKUP_QUALITY_LEVEL,
                    )
                    deploy_result["url"] = mockup_path or ""
                    if mockup_path and deploy_mockups:
                        netlify_zip = self.netlify_preparer.prepare_for_deployment(
                            mockup_path,
                            lead.get("business_name", ""),
                        )
                        deploy_result = self.netlify_deployer.deploy_mockup(
                            mockup_path,
                            lead.get("business_name", ""),
                        )
                    elif auto_mode and not deploy_mockups:
                        logger.info(f"Skipping Netlify deployment for {lead.get('business_name')} in auto mode")
                        deploy_result["status"] = "skipped_auto_mode"
                elif auto_mode:
                    logger.info(f"Skipping mockup generation for {lead.get('business_name')} in auto mode")

                lead.update(
                    {
                        "mockup_url": deploy_result.get("url", mockup_path or ""),
                        "mockup_status": deploy_result.get("mockup_status", "pending"),
                        "netlify_site_id": deploy_result.get("site_id", ""),
                        "netlify_deploy_id": deploy_result.get("deploy_id", ""),
                    }
                )

                email_fr = self.email_generator.generate_email({**lead, "email_language": "fr"}, "fr")
                email_en = self.email_generator.generate_email({**lead, "email_language": "en"}, "en")
                lead.update(
                    {
                        "selected_offer_type": email_fr.get("selected_offer_type") or email_en.get("selected_offer_type") or lead.get("selected_offer_type", "website"),
                        "email_subject_fr": email_fr["subject"],
                        "email_body_fr": email_fr.get("long_body", email_fr.get("body", "")),
                        "email_html_fr": email_fr.get("html_body", ""),
                        "email_short_subject_fr": email_fr.get("short_subject", ""),
                        "email_short_fr": email_fr.get("short_body", ""),
                        "follow_ups_fr": email_fr.get("follow_ups", {}),
                        "email_subject_en": email_en["subject"],
                        "email_body_en": email_en.get("long_body", email_en.get("body", "")),
                        "email_html_en": email_en.get("html_body", ""),
                        "email_short_subject_en": email_en.get("short_subject", ""),
                        "email_short_en": email_en.get("short_body", ""),
                        "follow_ups_en": email_en.get("follow_ups", {}),
                    }
                )

                contact_messages = self.contact_strategy.generate_messages(lead)
                logger.info(
                    f"Outreach fallback prepared for {lead.get('business_name')}: "
                    f"channel={contact_messages.get('recommended_channel')} "
                    f"email_reason={contact_messages.get('email_unavailable_reason') or 'available'}"
                )
                lead.update(
                    {
                        "email_language": lead.get("email_language", language),
                        "status": "MAQUETTE_READY",
                        "selected_outreach_channel": "email" if lead.get("email") else "skipped",
                        "outreach_status": "NOT_SENT" if lead.get("email") else "SKIPPED",
                        "notes": json.dumps(
                            {
                                **contact_messages,
                                "mockup_path": mockup_path,
                                "netlify_zip": netlify_zip,
                                "netlify_status": deploy_result.get("status", "pending"),
                                "netlify_error": deploy_result.get("error", ""),
                                "contact_extraction": lead.get("contact_extraction", {}),
                                "email_short_subject_fr": lead.get("email_short_subject_fr", ""),
                                "email_short_fr": lead.get("email_short_fr", ""),
                                "email_short_subject_en": lead.get("email_short_subject_en", ""),
                                "email_short_en": lead.get("email_short_en", ""),
                                "follow_ups_fr": lead.get("follow_ups_fr", {}),
                                "follow_ups_en": lead.get("follow_ups_en", {}),
                                "selected_offer_type": lead.get("selected_offer_type", ""),
                                "selected_email_subject": lead.get("email_subject_en") if lead.get("email_language") == "en" else lead.get("email_subject_fr"),
                                "selected_email_body": lead.get("email_body_en") if lead.get("email_language") == "en" else lead.get("email_body_fr"),
                                "new_business_score": lead.get("new_business_score", 0),
                                "target_type": lead.get("target_type", ""),
                                "website_page_count": lead.get("website_page_count", 0),
                                "website_content_length": lead.get("website_content_length", 0),
                                "has_booking_system": bool(lead.get("has_booking_system")),
                                "has_seo_foundation": bool(lead.get("has_seo_foundation")),
                                "has_modern_ui": bool(lead.get("has_modern_ui")),
                                "social_first_business": bool(lead.get("social_first_business")),
                            }
                        ),
                    }
                )
                prepared.append(lead)
            except Exception as e:
                logger.warning(f"Outreach preparation failed for lead {lead.get('business_name')}: {e}")
                lead.update({"status": lead.get("status", "REVIEWED"), "mockup_status": "failed"})
                prepared.append(lead)

        return prepared

    def _filter_auto_mode_contacts(
        self,
        leads: List[dict],
        *,
        fallback_pool: List[dict] | None = None,
        target_count: int | None = None,
    ) -> tuple[List[dict], List[dict]]:
        """Keep only leads that match the current autonomous contact quality policy."""
        if not settings.AUTO_MODE_REQUIRE_EMAIL_AND_PHONE:
            return leads, []

        eligible: List[dict] = []
        rejected: List[dict] = []
        seen_keys: set[str] = set()
        for lead in leads:
            if lead.get("email") and lead.get("phone"):
                eligible.append(lead)
                seen_keys.add(self._build_auto_contact_key(lead))
                continue
            rejected.append({**lead, "rejection_reason": "missing_email_or_phone_for_auto_mode"})

        desired_count = max(1, target_count or 0)
        if fallback_pool and len(eligible) < desired_count:
            supplemental = sorted(
                fallback_pool,
                key=lambda lead: (
                    1 if lead.get("email") else 0,
                    1 if lead.get("phone") else 0,
                    float(lead.get("new_business_score") or 0),
                    float(lead.get("priority_score") or 0),
                    float(lead.get("opportunity_score") or 0),
                ),
                reverse=True,
            )
            added = 0
            for lead in supplemental:
                lead_key = self._build_auto_contact_key(lead)
                if lead_key in seen_keys:
                    continue
                if not lead.get("website") or not lead.get("email") or not lead.get("phone"):
                    continue
                eligible.append(lead)
                seen_keys.add(lead_key)
                added += 1
                if len(eligible) >= desired_count:
                    break
            if added:
                logger.info(f"Auto-mode contact quality filter supplemented {added} full-contact leads from the processed pool")

        logger.info(
            f"Auto-mode contact quality filter kept {len(eligible)} leads and rejected {len(rejected)} leads requiring both email and phone"
        )
        return eligible, rejected

    def _build_auto_contact_key(self, lead: dict) -> str:
        """Build a stable dedupe key for autonomous full-contact selection."""
        return "|".join(
            [
                str(lead.get("business_name", "")).strip().lower(),
                str(lead.get("website", "")).strip().lower(),
                str(lead.get("location", "")).strip().lower(),
            ]
        )

    def _count_rejection_reasons(self, rejected_leads: List[dict]) -> dict[str, int]:
        """Aggregate rejection reasons for reporting."""
        reasons: dict[str, int] = {}
        for lead in rejected_leads:
            reason = (lead.get("rejection_reason") or "").strip()
            if reason:
                reasons[reason] = reasons.get(reason, 0) + 1
        return reasons

    def _count_target_type(self, leads: List[dict], target_type: str) -> int:
        """Count analyzed leads matching one target profile."""
        return sum(1 for lead in leads if str(lead.get("target_type") or "").strip() == target_type)

    def _count_offer_type(self, leads: List[dict], offer_type: str) -> int:
        """Count leads matching one selected offer type."""
        return sum(1 for lead in leads if str(lead.get("selected_offer_type") or "").strip() == offer_type)

    def _count_high_opportunity_leads(self, leads: List[dict]) -> int:
        """Count leads that should be prioritized immediately."""
        return sum(
            1
            for lead in leads
            if float(lead.get("opportunity_score") or 0) >= 75 or float(lead.get("new_business_score") or 0) >= 60
        )

    def _should_generate_mockups(self, auto_mode: bool) -> bool:
        """Only generate mockups in auto mode when explicitly enabled."""
        if not auto_mode:
            return True
        return settings.AUTO_MODE_GENERATE_MOCKUPS or settings.AUTO_MODE_DEPLOY_MOCKUPS

    def _should_deploy_mockups(self, auto_mode: bool) -> bool:
        """Only deploy mockups in auto mode when explicitly enabled."""
        if not auto_mode:
            return True
        return settings.AUTO_MODE_DEPLOY_MOCKUPS

    def _save_leads(self, leads: List[dict]) -> int:
        """Save leads to database."""
        saved_count, _ = self._save_leads_with_ids(leads)
        return saved_count

    def _save_leads_with_ids(self, leads: List[dict]) -> tuple[int, List[int]]:
        """Save leads to database and return affected prospect ids."""
        db = SessionLocal()
        try:
            saved = 0
            prospect_ids: List[int] = []
            for lead_data in leads:
                if "detected_issues" in lead_data and isinstance(lead_data["detected_issues"], list):
                    lead_data["detected_issues"] = json.dumps(lead_data["detected_issues"])

                existing = (
                    db.query(Prospect)
                    .filter(
                        Prospect.business_name == lead_data.get("business_name"),
                        Prospect.location == lead_data.get("location"),
                    )
                    .first()
                )

                if existing:
                    self._apply_lead_data(existing, lead_data)
                    db.flush()
                    prospect_ids.append(existing.id)
                else:
                    prospect = Prospect()
                    self._apply_lead_data(prospect, lead_data)
                    db.add(prospect)
                    db.flush()
                    prospect_ids.append(prospect.id)
                    saved += 1

            db.commit()
            return saved, prospect_ids
        except Exception as e:
            db.rollback()
            logger.error(f"Save leads failed: {e}")
            return 0, []
        finally:
            db.close()

    async def generate_emails(self):
        """Regenerate emails for existing leads without them."""
        db = SessionLocal()
        try:
            leads = [lead for lead in db.query(Prospect).all() if self._prospect_needs_email_refresh(lead)]

            for lead in leads:
                lead_dict = {
                    "business_name": lead.business_name,
                    "category": lead.category,
                    "location": lead.location,
                    "country": lead.country,
                    "currency": lead.currency,
                    "email_language": lead.email_language,
                    "website": lead.website,
                    "detected_issues": self._parse_detected_issues(lead.detected_issues),
                    "estimated_price_min": lead.estimated_price_min,
                    "estimated_price_max": lead.estimated_price_max,
                    "estimated_time": lead.estimated_time,
                    "mockup_url": lead.mockup_url,
                }
                notes_payload = self._load_notes_payload(lead.notes)
                lead_dict.update(
                    {
                        "contact_form_url": notes_payload.get("contact_form_url", ""),
                        "contact_form_detected": notes_payload.get("contact_form_detected", False),
                        "instagram_url": notes_payload.get("instagram_url", ""),
                        "facebook_url": notes_payload.get("facebook_url", ""),
                        "linkedin_url": notes_payload.get("linkedin_url", ""),
                        "whatsapp_url": notes_payload.get("whatsapp_url", ""),
                        "contact_extraction": notes_payload.get("contact_extraction", {}),
                    }
                )

                email_fr = self.email_generator.generate_email({**lead_dict, "email_language": "fr"}, "fr")
                email_en = self.email_generator.generate_email({**lead_dict, "email_language": "en"}, "en")

                lead.email_subject_fr = email_fr["subject"]
                lead.email_body_fr = email_fr.get("body", email_fr.get("long_body", ""))
                lead.email_html_fr = email_fr.get("html_body", "")
                lead.email_subject_en = email_en["subject"]
                lead.email_body_en = email_en.get("body", email_en.get("long_body", ""))
                lead.email_html_en = email_en.get("html_body", "")
                lead.selected_offer_type = email_fr.get("selected_offer_type") or email_en.get("selected_offer_type") or lead.selected_offer_type

                lead_dict.update(
                    {
                        "email_short_subject_fr": email_fr.get("short_subject", ""),
                        "email_short_fr": email_fr.get("short_body", ""),
                        "follow_ups_fr": email_fr.get("follow_ups", {}),
                        "email_short_subject_en": email_en.get("short_subject", ""),
                        "email_short_en": email_en.get("short_body", ""),
                        "follow_ups_en": email_en.get("follow_ups", {}),
                    }
                )

                contact_messages = self.contact_strategy.generate_messages(lead_dict)
                notes_payload.update(contact_messages)
                notes_payload.update(
                    {
                        "contact_extraction": lead_dict.get("contact_extraction", notes_payload.get("contact_extraction", {})),
                        "email_short_subject_fr": lead_dict.get("email_short_subject_fr", ""),
                        "email_short_fr": lead_dict.get("email_short_fr", ""),
                        "email_short_subject_en": lead_dict.get("email_short_subject_en", ""),
                        "email_short_en": lead_dict.get("email_short_en", ""),
                        "follow_ups_fr": lead_dict.get("follow_ups_fr", {}),
                        "follow_ups_en": lead_dict.get("follow_ups_en", {}),
                    }
                )
                lead.notes = json.dumps(notes_payload)

            db.commit()
            logger.info(f"Generated emails for {len(leads)} leads")
        except Exception as e:
            db.rollback()
            logger.error(f"Email generation failed: {e}")
        finally:
            db.close()

    def send_outreach(
        self,
        limit: int | None = None,
        only_not_sent: bool = True,
        simulate: bool = False,
        country: str | None = None,
        category: str | None = None,
        min_priority: float | None = None,
        selected_ids: List[int] | None = None,
        allow_resend: bool = False,
        progress_callback: Callable[[int, int, Dict[str, object], Dict[str, object]], None] | None = None,
    ) -> Dict[str, object]:
        """Send outreach automatically by email, otherwise skip."""
        if not settings.AUTO_SEND_ENABLED and not simulate:
            logger.warning("Automatic outreach send skipped because AUTO_SEND_ENABLED is false")
            return {
                "selected": 0,
                "email_sent": 0,
                "sms_sent": 0,
                "landing_page_sent": 0,
                "website_sent": 0,
                "failed": 1,
                "skipped": 0,
                "simulated": 0,
                "results": [],
                "error": "auto_send_disabled",
            }
        db = SessionLocal()
        try:
            send_limit = max(1, limit or settings.SEND_MAX_PER_RUN)
            if settings.SEND_BATCH_SIZE > 0:
                send_limit = min(send_limit, settings.SEND_BATCH_SIZE)
            query = db.query(Prospect)
            if selected_ids is not None:
                query = query.filter(Prospect.id.in_(selected_ids))
            if country:
                query = query.filter(Prospect.country == country)
            if category:
                query = query.filter(Prospect.category == category)
            if min_priority is not None:
                query = query.filter(Prospect.priority_score >= min_priority)
            prospects = (
                query.order_by(
                    Prospect.priority_score.desc(),
                    Prospect.new_business_score.desc(),
                    Prospect.email.isnot(None).desc(),
                    Prospect.phone.isnot(None).desc(),
                    Prospect.collected_at.desc(),
                )
                .all()
            )
            prospects = [prospect for prospect in prospects if self._should_send_prospect(prospect, only_not_sent=only_not_sent, allow_resend=allow_resend)][:send_limit]

            summary = {
                "selected": len(prospects),
                "email_sent": 0,
                "sms_sent": 0,
                "landing_page_sent": 0,
                "website_sent": 0,
                "failed": 0,
                "skipped": 0,
                "simulated": 0,
                "results": [],
            }

            for index, prospect in enumerate(prospects, 1):
                self._ensure_email_assets(prospect)
                notes_payload = self._ensure_contact_strategy_assets(db, prospect)
                channel = self._select_outreach_channel(prospect, notes_payload)
                recipient = ""
                error = ""
                simulated_result = False

                if channel == "email":
                    prepared_email = self.email_sender.prepare_email(prospect)
                    email_result = self.email_sender.send_prepared_email(prepared_email, simulate=simulate)
                    recipient = prepared_email.actual_recipient
                    error = email_result.error
                    simulated_result = email_result.simulated
                    self._apply_outreach_result(
                        db,
                        prospect,
                        channel=channel,
                        success=email_result.success,
                        skipped=email_result.skipped,
                        simulated=email_result.simulated,
                        error=email_result.error,
                    )
                    if email_result.simulated:
                        summary["simulated"] += 1
                    elif email_result.success:
                        summary["email_sent"] += 1
                        if (prospect.selected_offer_type or "") == "landing_page":
                            summary["landing_page_sent"] += 1
                        else:
                            summary["website_sent"] += 1
                    elif email_result.skipped:
                        summary["skipped"] += 1
                    else:
                        summary["failed"] += 1
                else:
                    error = "no_email"
                    recipient = ""
                    self._apply_outreach_result(db, prospect, channel="skipped", success=False, skipped=True, simulated=False, error=error)
                    summary["skipped"] += 1

                summary["results"].append(
                    {
                        "prospect_id": prospect.id,
                        "business_name": prospect.business_name,
                        "location": prospect.location,
                        "selected_offer_type": prospect.selected_offer_type or "",
                        "channel_used": prospect.selected_outreach_channel,
                        "recipient_used": recipient,
                        "send_result": prospect.send_status,
                        "error": error,
                        "simulated": simulated_result,
                    }
                )

                db.commit()
                if progress_callback:
                    progress_callback(index, len(prospects), summary["results"][-1], summary)
                if index < len(prospects) and not simulate and settings.SEND_DELAY_SECONDS > 0:
                    time.sleep(settings.SEND_DELAY_SECONDS)

            return summary
        except Exception as exc:
            db.rollback()
            logger.error(f"Auto outreach sending batch failed: {exc}")
            return {
                "selected": 0,
                "email_sent": 0,
                "sms_sent": 0,
                "landing_page_sent": 0,
                "website_sent": 0,
                "failed": 1,
                "skipped": 0,
                "simulated": 0,
                "results": [],
                "error": str(exc),
            }
        finally:
            db.close()

    def send_emails(
        self,
        limit: int | None = None,
        only_not_sent: bool = False,
        test_to: str | None = None,
        simulate: bool = False,
        country: str | None = None,
        category: str | None = None,
        min_priority: float | None = None,
        selected_ids: List[int] | None = None,
        allow_resend: bool = False,
        progress_callback: Callable[[int, int, Dict[str, object], Dict[str, object]], None] | None = None,
    ) -> Dict[str, object]:
        """Send initial outreach emails for qualified leads."""
        db = SessionLocal()
        try:
            send_limit = max(1, limit or settings.SEND_MAX_PER_RUN)
            if settings.SEND_BATCH_SIZE > 0:
                send_limit = min(send_limit, settings.SEND_BATCH_SIZE)
            query = db.query(Prospect)

            if selected_ids is not None:
                query = query.filter(Prospect.id.in_(selected_ids))
            if country:
                query = query.filter(Prospect.country == country)
            if category:
                query = query.filter(Prospect.category == category)
            if min_priority is not None:
                query = query.filter(Prospect.priority_score >= min_priority)
            prospects = (
                query.order_by(
                    Prospect.priority_score.desc(),
                    Prospect.new_business_score.desc(),
                    Prospect.email.isnot(None).desc(),
                    Prospect.collected_at.desc(),
                )
                .all()
            )
            prospects = [
                prospect
                for prospect in prospects
                if self._should_send_prospect(prospect, only_not_sent=only_not_sent, allow_resend=allow_resend)
            ][:send_limit]

            summary = {
                "selected": len(prospects),
                "sent": 0,
                "failed": 0,
                "skipped": 0,
                "simulated": 0,
                "test_mode": bool(test_to),
                "warnings": settings.get_smtp_identity_warnings(),
                "results": [],
            }

            for warning in summary["warnings"]:
                logger.warning(warning)

            for index, prospect in enumerate(prospects, 1):
                self._ensure_email_assets(prospect)
                prepared = self.email_sender.prepare_email(prospect, test_to=test_to)
                result = self.email_sender.send_prepared_email(prepared, simulate=simulate)
                self._apply_send_result(db, prospect, prepared, result)

                if result.simulated:
                    summary["simulated"] += 1
                elif result.success and not prepared.is_test_mode:
                    summary["sent"] += 1
                elif result.skipped:
                    summary["skipped"] += 1
                else:
                    summary["failed"] += 1

                summary["results"].append(
                    {
                        "prospect_id": prospect.id,
                        "business_name": prospect.business_name,
                        "recipient": prepared.recipient,
                        "actual_recipient": prepared.actual_recipient,
                        "subject": prepared.subject,
                        "status": prospect.send_status,
                        "error": result.error,
                        "test_mode": prepared.is_test_mode,
                        "simulated": result.simulated,
                    }
                )

                db.commit()
                if progress_callback:
                    progress_callback(index, len(prospects), summary["results"][-1], summary)

                if index < len(prospects) and not simulate and settings.SEND_DELAY_SECONDS > 0:
                    time.sleep(settings.SEND_DELAY_SECONDS)

            return summary
        except Exception as exc:
            db.rollback()
            logger.error(f"Email sending batch failed: {exc}")
            return {
                "selected": 0,
                "sent": 0,
                "failed": 1,
                "skipped": 0,
                "simulated": 0,
                "test_mode": bool(test_to),
                "results": [],
                "error": str(exc),
            }
        finally:
            db.close()

    def _create_search_run(self, locations: List[str], categories: List[str], limit: int, language: str) -> SearchRun:
        """Create search run record."""
        db = SessionLocal()
        try:
            search_run = SearchRun(
                locations=",".join(locations),
                categories=",".join(categories),
                limit_per_location=limit,
                language=language,
                status="RUNNING",
            )
            db.add(search_run)
            db.commit()
            db.refresh(search_run)
            return search_run
        finally:
            db.close()

    def _update_search_run(
        self,
        search_run: SearchRun,
        prospects_found: int,
        status: str,
        error: str | None = None,
        diagnostics: List[dict] | None = None,
    ):
        """Update search run status."""
        db = SessionLocal()
        try:
            db_search_run = db.query(SearchRun).filter(SearchRun.id == search_run.id).first()
            if not db_search_run:
                return

            db_search_run.prospects_found = prospects_found
            db_search_run.status = status
            db_search_run.completed_at = datetime.utcnow()
            db_search_run.diagnostics_json = json.dumps(diagnostics or [])
            if error:
                db_search_run.error_message = error
            db.commit()
        finally:
            db.close()

    def _parse_detected_issues(self, detected_issues: str | None) -> List[str]:
        """Convert persisted detected issues back to a list."""
        if not detected_issues:
            return []
        if isinstance(detected_issues, list):
            return [str(issue).strip() for issue in detected_issues if str(issue).strip()]

        try:
            parsed = json.loads(detected_issues)
        except json.JSONDecodeError:
            parsed = None

        if isinstance(parsed, list):
            return parsed
        return [issue.strip() for issue in detected_issues.split(",") if issue.strip()]

    def _load_notes_payload(self, notes: str | None) -> dict:
        """Parse stored notes JSON safely."""
        if not notes:
            return {}
        try:
            parsed = json.loads(notes)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _apply_lead_data(self, prospect: Prospect, lead_data: dict):
        """Apply service-managed lead fields to a Prospect instance."""
        allowed_fields = {
            "business_name",
            "category",
            "location",
            "country",
            "currency",
            "address",
            "phone",
            "email",
            "website",
            "contact_page",
            "reviews_count",
            "source",
            "status",
            "opportunity_score",
            "site_quality_score",
            "new_business_score",
            "target_type",
            "selected_offer_type",
            "website_page_count",
            "website_content_length",
            "has_booking_system",
            "has_seo_foundation",
            "has_modern_ui",
            "social_first_business",
            "feasibility",
            "estimated_time",
            "estimated_price_min",
            "estimated_price_max",
            "priority_score",
            "detected_issues",
            "email_language",
            "email_subject_fr",
            "email_body_fr",
            "email_html_fr",
            "email_subject_en",
            "email_body_en",
            "email_html_en",
            "selected_outreach_channel",
            "outreach_status",
            "send_status",
            "first_sent_at",
            "last_attempt_at",
            "send_attempts",
            "last_send_error",
            "response_status",
            "replied_at",
            "potential_deal_value",
            "reply_notes",
            "mockup_url",
            "mockup_status",
            "netlify_site_id",
            "netlify_deploy_id",
            "notes",
        }

        for field_name in allowed_fields:
            if field_name in lead_data:
                setattr(prospect, field_name, lead_data[field_name])

    def _apply_market_context(self, lead: dict, fallback_language: str):
        """Apply country, currency and localized defaults to a lead."""
        country = lead.get("country") or detect_country(lead.get("location", ""))
        language = resolve_email_language(lead.get("location", ""), country, fallback_language)
        profile = get_country_profile(country)

        lead["country"] = country
        lead["currency"] = lead.get("currency") or profile.currency
        lead["email_language"] = language

    def _calculate_priority_score(self, lead: dict) -> float:
        """Calculate a revenue-oriented priority score."""
        country_weight = get_country_profile(lead.get("country")).country_value_weight
        opportunity = float(lead.get("opportunity_score") or 0)
        contact_bonus = 0
        contact_penalty = 0
        if lead.get("website"):
            contact_bonus += 8
        if lead.get("email"):
            contact_bonus += 16
        else:
            contact_penalty += 8
        if lead.get("phone"):
            contact_bonus += 10
        else:
            contact_penalty += 4
        site_quality = float(lead.get("site_quality_score") or 0)
        quality_bonus = 0
        if site_quality >= 70:
            quality_bonus += 8
        elif site_quality >= 40:
            quality_bonus += 4
        elif site_quality > 0:
            quality_bonus -= 8
        issues_penalty = min(len(self._parse_detected_issues(lead.get("detected_issues"))) * 1.5, 9)
        niche_bonus = 0
        if settings.PRIORITY_NICHES_ENABLED:
            niche_bonus = self.PRIORITY_NICHE_BONUSES.get(canonicalize_category(str(lead.get("category", ""))), 0)
        new_business_score = float(lead.get("new_business_score") or 0)
        new_business_bonus = new_business_score * 0.45
        target_type_bonus = 0
        if lead.get("target_type") == "early_stage_business":
            target_type_bonus += 8
        elif lead.get("target_type") == "growth_opportunity":
            target_type_bonus += 4
        if lead.get("social_first_business"):
            target_type_bonus += 5
        price_anchor = float(lead.get("estimated_price_max") or 0) / 250.0
        return round(
            opportunity * country_weight + contact_bonus + quality_bonus + niche_bonus + new_business_bonus + target_type_bonus + price_anchor - contact_penalty - issues_penalty,
            2,
        )

    def _finalize_search_diagnostics(
        self,
        diagnostics: List[dict],
        processed_leads: List[dict],
        filtered_leads: List[dict],
        rejected_leads: List[dict],
    ):
        """Add post-processing counts to diagnostics."""
        for entry in diagnostics:
            location = entry["location"]
            category = entry["requested_category"]
            entry["processed_candidates"] = sum(
                1 for lead in processed_leads if lead.get("location") == location and lead.get("category") == category
            )
            entry["valid_prospects_kept"] = sum(
                1 for lead in filtered_leads if lead.get("location") == location and lead.get("category") == category
            )
            entry["rejected_after_filter"] = sum(
                1 for lead in rejected_leads if lead.get("location") == location and lead.get("category") == category
            )

    def _ensure_email_assets(self, prospect: Prospect) -> None:
        """Generate email content on demand when a lead has not been hydrated yet."""
        language = prospect.email_language or "fr"
        if not self._prospect_needs_email_refresh(prospect):
            return

        lead_dict = {
            "business_name": prospect.business_name,
            "category": prospect.category,
            "location": prospect.location,
            "country": prospect.country,
            "currency": prospect.currency,
            "email_language": language,
            "website": prospect.website,
            "detected_issues": self._parse_detected_issues(prospect.detected_issues),
            "estimated_price_min": prospect.estimated_price_min,
            "estimated_price_max": prospect.estimated_price_max,
            "estimated_time": prospect.estimated_time,
            "mockup_url": prospect.mockup_url,
        }

        email_fr = self.email_generator.generate_email({**lead_dict, "email_language": "fr"}, "fr")
        email_en = self.email_generator.generate_email({**lead_dict, "email_language": "en"}, "en")
        prospect.email_subject_fr = email_fr["subject"]
        prospect.email_body_fr = email_fr.get("long_body", email_fr.get("body", ""))
        prospect.email_html_fr = email_fr.get("html_body", "")
        prospect.email_subject_en = email_en["subject"]
        prospect.email_body_en = email_en.get("long_body", email_en.get("body", ""))
        prospect.email_html_en = email_en.get("html_body", "")
        prospect.selected_offer_type = email_fr.get("selected_offer_type") or email_en.get("selected_offer_type") or prospect.selected_offer_type

    def _ensure_contact_strategy_assets(self, db, prospect: Prospect) -> dict:
        """Ensure stored notes contain the generated outreach routing assets."""
        notes_payload = self._load_notes_payload(prospect.notes)
        if notes_payload.get("contact_strategy") and "sms_message" in notes_payload:
            return notes_payload

        lead_dict = {
            "business_name": prospect.business_name,
            "category": prospect.category,
            "location": prospect.location,
            "country": prospect.country,
            "currency": prospect.currency,
            "email_language": prospect.email_language or "fr",
            "email": prospect.email,
            "phone": prospect.phone,
            "contact_form_url": notes_payload.get("contact_form_url", ""),
            "contact_form_detected": notes_payload.get("contact_form_detected", False),
            "instagram_url": notes_payload.get("instagram_url", ""),
            "facebook_url": notes_payload.get("facebook_url", ""),
            "linkedin_url": notes_payload.get("linkedin_url", ""),
            "whatsapp_url": notes_payload.get("whatsapp_url", ""),
            "contact_extraction": notes_payload.get("contact_extraction", {}),
            "email_body_fr": prospect.email_body_fr,
            "email_body_en": prospect.email_body_en,
            "email_short_subject_fr": notes_payload.get("email_short_subject_fr", ""),
            "email_short_fr": notes_payload.get("email_short_fr", ""),
            "email_short_subject_en": notes_payload.get("email_short_subject_en", ""),
            "email_short_en": notes_payload.get("email_short_en", ""),
            "follow_ups_fr": notes_payload.get("follow_ups_fr", {}),
            "follow_ups_en": notes_payload.get("follow_ups_en", {}),
            "estimated_price_min": prospect.estimated_price_min,
            "estimated_price_max": prospect.estimated_price_max,
            "mockup_url": prospect.mockup_url,
        }
        notes_payload.update(self.contact_strategy.generate_messages(lead_dict))
        prospect.notes = json.dumps(notes_payload)
        db.flush()
        return notes_payload

    def _prospect_needs_email_refresh(self, prospect: Prospect) -> bool:
        """Detect whether outreach content is missing or still carries the old sender identity."""
        required_fields = [
            prospect.email_subject_fr,
            prospect.email_html_fr,
            prospect.email_subject_en,
            prospect.email_html_en,
        ]
        if any(not field for field in required_fields):
            return True

        return contains_legacy_sender_identity(
            [
                prospect.email_body_fr,
                prospect.email_html_fr,
                prospect.email_body_en,
                prospect.email_html_en,
                prospect.notes,
            ]
        )

    def _should_send_prospect(self, prospect: Prospect, only_not_sent: bool, allow_resend: bool) -> bool:
        """Apply deduplication rules before sending."""
        status = (prospect.send_status or "NOT_SENT").upper()
        if only_not_sent:
            return status == "NOT_SENT"
        if not allow_resend and status == "SENT":
            return False
        return True

    def _select_outreach_channel(self, prospect: Prospect, notes_payload: dict) -> str:
        """Select the automatic outreach channel for a prospect."""
        if prospect.email:
            return "email"
        return "skipped"

    def _apply_outreach_result(
        self,
        db,
        prospect: Prospect,
        *,
        channel: str,
        success: bool,
        skipped: bool,
        simulated: bool,
        error: str,
    ) -> None:
        """Persist send outcomes for automatic email outreach."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        prospect.selected_outreach_channel = channel
        prospect.last_attempt_at = now
        prospect.send_attempts = int(prospect.send_attempts or 0) + 1

        if skipped:
            prospect.outreach_status = "SKIPPED"
            prospect.send_status = "SKIPPED"
            prospect.last_send_error = error
            db.flush()
            return

        if success and not simulated:
            if not prospect.first_sent_at:
                prospect.first_sent_at = now
            prospect.outreach_status = "SENT"
            prospect.send_status = "SENT"
            prospect.last_send_error = ""
            if prospect.status in {"NEW", "REVIEWED", "MAQUETTE_READY"}:
                prospect.status = "CONTACTED"
            db.flush()
            return

        if success and simulated:
            prospect.outreach_status = "NOT_SENT"
            if not prospect.send_status:
                prospect.send_status = "NOT_SENT"
            prospect.last_send_error = ""
            db.flush()
            return

        prospect.outreach_status = "FAILED"
        prospect.send_status = "FAILED"
        prospect.last_send_error = error
        db.flush()

    def _apply_send_result(self, db, prospect: Prospect, prepared, result) -> None:
        """Persist send status updates safely."""
        prospect.selected_outreach_channel = "email"
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        prospect.last_attempt_at = now
        prospect.send_attempts = int(prospect.send_attempts or 0) + 1

        if result.skipped:
            prospect.outreach_status = "SKIPPED"
            prospect.send_status = "SKIPPED"
            prospect.last_send_error = result.error
            return

        if result.success and not result.simulated and not prepared.is_test_mode:
            if not prospect.first_sent_at:
                prospect.first_sent_at = now
            prospect.outreach_status = "SENT"
            prospect.send_status = "SENT"
            prospect.last_send_error = ""
            if prospect.status in {"NEW", "REVIEWED", "MAQUETTE_READY"}:
                prospect.status = "CONTACTED"
            return

        if result.success and (result.simulated or prepared.is_test_mode):
            prospect.outreach_status = "NOT_SENT"
            if not prospect.send_status:
                prospect.send_status = "NOT_SENT"
            prospect.last_send_error = ""
            return

        prospect.outreach_status = "FAILED"
        prospect.send_status = "FAILED"
        prospect.last_send_error = result.error
        db.flush()

    def update_prospect_status(
        self,
        prospect_id: int,
        *,
        status: str | None = None,
        send_status: str | None = None,
        last_send_error: str | None = None,
        response_status: str | None = None,
        potential_deal_value: float | None = None,
        reply_notes: str | None = None,
    ) -> bool:
        """Update a prospect status, send status or business response tracking from the UI."""
        db = SessionLocal()
        try:
            prospect = db.query(Prospect).filter(Prospect.id == prospect_id).first()
            if not prospect:
                return False

            if status:
                prospect.status = status
            if send_status:
                prospect.send_status = send_status
                prospect.outreach_status = send_status
                if send_status == "SKIPPED" and not prospect.selected_outreach_channel:
                    prospect.selected_outreach_channel = "skipped"
            if last_send_error is not None:
                prospect.last_send_error = last_send_error
            if response_status:
                normalized_response = self._normalize_response_status(response_status)
                prospect.response_status = normalized_response
                if normalized_response in {"REPLIED", "INTERESTED", "WON", "LOST"}:
                    prospect.replied_at = datetime.now(timezone.utc).replace(tzinfo=None)
                if normalized_response == "INTERESTED" and prospect.status not in {"WON", "LOST"}:
                    prospect.status = "CONTACTED"
                elif normalized_response == "WON":
                    prospect.status = "WON"
                elif normalized_response == "LOST":
                    prospect.status = "LOST"
            if potential_deal_value is not None:
                prospect.potential_deal_value = potential_deal_value
            if reply_notes is not None:
                prospect.reply_notes = reply_notes
            if send_status in {"SKIPPED", "FAILED"}:
                prospect.last_attempt_at = datetime.now(timezone.utc).replace(tzinfo=None)

            db.commit()
            logger.info(
                f"Prospect status updated from UI: prospect_id={prospect_id}, status={prospect.status}, send_status={prospect.send_status}, response_status={prospect.response_status}"
            )
            return True
        except Exception as exc:
            db.rollback()
            logger.error(f"Prospect status update failed for {prospect_id}: {exc}")
            return False
        finally:
            db.close()

    def _normalize_response_status(self, response_status: str) -> str:
        """Normalize UI response tracking values."""
        normalized = (response_status or "NO_RESPONSE").strip().upper().replace(" ", "_")
        if normalized in {"NO_RESPONSE", "REPLIED", "INTERESTED", "WON", "LOST"}:
            return normalized
        return "NO_RESPONSE"
