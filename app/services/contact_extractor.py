"""
Contact extraction service.
"""
from __future__ import annotations

import json
import re
from html import unescape
from typing import Any, Optional
from urllib.parse import unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from app.core.config import settings
from app.core.logging import logger


class ContactExtractor:
    """Extract business contacts and fallback outreach channels from websites."""

    EMAIL_PATTERN = re.compile(r"\b[a-z0-9][a-z0-9._%+\-]{0,63}@[a-z0-9.\-]+\.[a-z]{2,24}\b", re.IGNORECASE)
    PHONE_PATTERN = re.compile(r"(?:(?:\+|00)?(?:33|41|1|61)\s?(?:\(0\)\s?)?[\d\s()./-]{7,18}|0\d(?:[\s()./-]*\d){8,10})")
    DISCOVERY_PATHS = ["/contact", "/contact-us", "/about", "/about-us", "/mentions-legales", "/mentions-legales/", "/mentions-legales.html", "/mentions-legales.php", "/impressum", "/imprint", "/quote", "/request-a-quote", "/devis"]
    PAGE_KEYWORDS = {
        "contact": ["contact", "contact-us", "nous-contacter", "contactez-nous", "get-in-touch", "coordonnees", "devis", "quote", "request-a-quote"],
        "about": ["about", "about-us", "a-propos", "qui-sommes-nous", "company"],
        "legal": ["mentions-legales", "mentionslegales", "legal", "legal-notice", "impressum", "imprint"],
    }
    SECTION_KEYWORDS = ["contact", "footer", "about", "legal", "impressum", "mentions", "coordonnees"]
    FORM_KEYWORDS = ["contact", "contact us", "get in touch", "contactez-nous", "formulaire", "quote", "request a quote", "devis"]
    NAME_FIELD_HINTS = ["name", "nom", "fullname", "full-name", "first_name", "lastname", "prenom"]
    EMAIL_FIELD_HINTS = ["email", "e-mail", "courriel", "mail"]
    MESSAGE_FIELD_HINTS = ["message", "comment", "comments", "details", "description", "inquiry", "demande"]
    SOCIAL_HOSTS = {
        "instagram_url": ("instagram.com",),
        "facebook_url": ("facebook.com", "fb.com"),
        "linkedin_url": ("linkedin.com",),
        "whatsapp_url": ("wa.me", "api.whatsapp.com", "whatsapp.com"),
    }
    BAD_SOCIAL_TOKENS = ["share", "sharer", "intent", "privacy", "policy", "help", "login", "reel", "story", "explore"]
    BAD_LOCAL_PARTS = {"noreply", "no-reply", "donotreply", "do-not-reply", "example", "test", "fake", "placeholder"}
    BAD_DOMAINS = {"example.com", "example.org", "example.net", "domain.com", "yourdomain.com", "test.com", "invalid", "localhost"}
    LOCAL_PART_SCORES = {"contact": 30, "bonjour": 24, "hello": 24, "info": 22, "office": 18, "studio": 18, "salon": 18, "team": 14, "admin": 10, "support": 6}
    SOURCE_SCORES = {"mailto": 120, "structured_data": 90, "targeted_text": 70, "visible_text": 55, "raw_html": 45}
    PAGE_SCORES = {"homepage": 10, "contact": 32, "about": 18, "legal": 20, "other": 0}
    MAX_PAGES_TO_SCAN = 8

    async def extract_contacts(self, website: str) -> dict[str, Any]:
        """Extract email, phone, forms, socials and diagnostics from a website."""
        diagnostics: dict[str, Any] = {
            "pages_scanned": [],
            "emails_found": [],
            "selected_email": None,
            "selected_phone": None,
            "selected_channel": "unavailable",
            "contact_forms_found": [],
            "social_profiles_found": {},
            "email_unavailable_reason": "",
            "fallback_reason": "",
            "channels_found": {},
        }
        result: dict[str, Any] = {
            "email": None,
            "phone": None,
            "contact_page": None,
            "contact_form_url": None,
            "contact_form_detected": False,
            "instagram_url": None,
            "facebook_url": None,
            "linkedin_url": None,
            "whatsapp_url": None,
            "contact_extraction": diagnostics,
        }
        if not website:
            diagnostics["fallback_reason"] = "missing_website"
            diagnostics["email_unavailable_reason"] = "missing_website"
            return result

        normalized_website = self._normalize_website_url(website)
        page_candidates = [{"url": normalized_website, "page_type": "homepage", "source": "homepage"}]
        scanned_pages: list[dict[str, Any]] = []
        email_candidates: dict[str, dict[str, Any]] = {}
        phone_candidates: list[str] = []
        social_profiles: dict[str, str] = {}
        contact_form_urls: list[str] = []
        best_contact_page: Optional[str] = None

        try:
            with requests.Session() as session:
                homepage_scan = self._scan_page(session, normalized_website, "homepage", "homepage")
                scanned_pages.append(homepage_scan)
                self._merge_email_candidates(email_candidates, homepage_scan["email_candidates"])
                phone_candidates.extend(homepage_scan["phones"])
                self._merge_social_profiles(social_profiles, homepage_scan["social_profiles"])
                if homepage_scan["contact_form_detected"] and homepage_scan["contact_form_url"]:
                    contact_form_urls.append(homepage_scan["contact_form_url"])
                if homepage_scan["status"] == "ok" and homepage_scan["soup"] is not None:
                    page_candidates.extend(self._discover_pages(homepage_scan["soup"], homepage_scan["url"]))
                page_candidates = self._dedupe_page_candidates(page_candidates)

                for candidate in page_candidates[1:self.MAX_PAGES_TO_SCAN]:
                    page_scan = self._scan_page(session, candidate["url"], candidate["page_type"], candidate["source"])
                    scanned_pages.append(page_scan)
                    self._merge_email_candidates(email_candidates, page_scan["email_candidates"])
                    phone_candidates.extend(page_scan["phones"])
                    self._merge_social_profiles(social_profiles, page_scan["social_profiles"])
                    if page_scan["contact_form_detected"] and page_scan["contact_form_url"]:
                        contact_form_urls.append(page_scan["contact_form_url"])
                    if page_scan["status"] == "ok" and page_scan["page_type"] in {"contact", "about", "legal"} and not best_contact_page:
                        best_contact_page = page_scan["url"]

                selected_email = self._select_best_email(email_candidates)
                selected_phone = self._select_best_phone(phone_candidates)
                contact_form_url = self._select_best_contact_form(contact_form_urls, scanned_pages)
                recommended_channel = self._determine_recommended_channel(
                    email=selected_email,
                    phone=selected_phone,
                    contact_form_url=contact_form_url,
                    instagram_url=social_profiles.get("instagram_url"),
                    facebook_url=social_profiles.get("facebook_url"),
                )
                diagnostics["pages_scanned"] = [{
                    "url": page["url"],
                    "page_type": page["page_type"],
                    "source": page["source"],
                    "status": page["status"],
                    "emails_found": page["emails"],
                    "phones_found": page["phones"],
                    "contact_form_detected": page["contact_form_detected"],
                    "contact_form_signals": page["contact_form_signals"],
                    "social_profiles": page["social_profiles"],
                } for page in scanned_pages]
                diagnostics["emails_found"] = sorted(email_candidates.keys())
                diagnostics["selected_email"] = selected_email
                diagnostics["selected_phone"] = selected_phone
                diagnostics["fallback_reason"] = self._determine_fallback_reason(scanned_pages, email_candidates, selected_email)
                diagnostics["email_unavailable_reason"] = diagnostics["fallback_reason"] if not selected_email else ""
                diagnostics["selected_channel"] = recommended_channel
                diagnostics["contact_forms_found"] = self._dedupe_strings(contact_form_urls)
                diagnostics["social_profiles_found"] = social_profiles
                diagnostics["channels_found"] = {
                    "email": bool(selected_email),
                    "phone": bool(selected_phone),
                    "contact_form": bool(contact_form_url),
                    "instagram": bool(social_profiles.get("instagram_url")),
                    "facebook": bool(social_profiles.get("facebook_url")),
                    "linkedin": bool(social_profiles.get("linkedin_url")),
                    "whatsapp": bool(social_profiles.get("whatsapp_url")),
                }
                result.update({
                    "email": selected_email,
                    "phone": selected_phone,
                    "contact_page": best_contact_page or self._pick_first_contact_page(scanned_pages),
                    "contact_form_url": contact_form_url,
                    "contact_form_detected": bool(contact_form_url),
                    "instagram_url": social_profiles.get("instagram_url"),
                    "facebook_url": social_profiles.get("facebook_url"),
                    "linkedin_url": social_profiles.get("linkedin_url"),
                    "whatsapp_url": social_profiles.get("whatsapp_url"),
                })
                logger.info(
                    f"Contact extraction channels for {website}: email={bool(selected_email)} phone={bool(selected_phone)} "
                    f"contact_form={bool(contact_form_url)} instagram={bool(social_profiles.get('instagram_url'))} "
                    f"facebook={bool(social_profiles.get('facebook_url'))} selected={recommended_channel} "
                    f"email_reason={diagnostics['email_unavailable_reason'] or 'available'}"
                )
        except Exception as exc:
            diagnostics["fallback_reason"] = "unexpected_extraction_error"
            diagnostics["email_unavailable_reason"] = "unexpected_extraction_error"
            logger.warning(f"Contact extraction failed for {website}: {exc}")

        return result

    def _scan_page(self, session: requests.Session, url: str, page_type: str, source: str) -> dict[str, Any]:
        """Fetch and scan one page for contact data."""
        page_result: dict[str, Any] = {
            "url": url, "page_type": page_type, "source": source, "status": "error", "emails": [], "phones": [],
            "email_candidates": [], "contact_form_detected": False, "contact_form_url": None,
            "contact_form_signals": [], "social_profiles": {}, "soup": None,
        }
        try:
            response = session.get(url, headers={"User-Agent": settings.USER_AGENT}, timeout=settings.REQUEST_TIMEOUT)
            response.raise_for_status()
            page_result["url"] = response.url
            page_result["status"] = "ok"
            page_result["soup"] = BeautifulSoup(response.text, "html.parser")
            page_result["email_candidates"] = self._extract_email_candidates_from_page(page_result["soup"], response.text, response.url, page_type)
            page_result["emails"] = sorted({candidate["email"] for candidate in page_result["email_candidates"]})
            visible_text = page_result["soup"].get_text(" ", strip=True)
            page_result["phones"] = self._dedupe_strings(self._extract_tel_links(page_result["soup"]) + self._extract_phones(visible_text))
            form_data = self._extract_contact_form_data(page_result["soup"], response.url, page_type)
            page_result["contact_form_detected"] = form_data["detected"]
            page_result["contact_form_url"] = form_data["url"]
            page_result["contact_form_signals"] = form_data["signals"]
            page_result["social_profiles"] = self._extract_social_profiles(page_result["soup"], response.url)
        except Exception as exc:
            logger.warning(f"Could not access page {url}: {exc}")
        return page_result

    def _extract_email_candidates_from_page(self, soup: BeautifulSoup, raw_html: str, page_url: str, page_type: str) -> list[dict[str, Any]]:
        """Extract and score valid email candidates from one page."""
        candidates: dict[str, dict[str, Any]] = {}
        visible_text = soup.get_text(" ", strip=True)
        targeted_text = self._extract_targeted_text(soup)
        raw_text = unescape(raw_html or "")
        for email in self._extract_mailto_emails(soup):
            self._store_candidate(candidates, email, "mailto", page_url, page_type)
        for email in self._extract_structured_data_emails(soup):
            self._store_candidate(candidates, email, "structured_data", page_url, page_type)
        for email in self._extract_emails(visible_text):
            self._store_candidate(candidates, email, "visible_text", page_url, page_type)
        for email in self._extract_emails(targeted_text):
            self._store_candidate(candidates, email, "targeted_text", page_url, page_type)
        for email in self._extract_emails(raw_text):
            self._store_candidate(candidates, email, "raw_html", page_url, page_type)
        return list(candidates.values())

    def _store_candidate(self, candidates: dict[str, dict[str, Any]], email: str, source: str, page_url: str, page_type: str) -> None:
        """Normalize, validate and score one candidate email."""
        normalized = self._normalize_email(email)
        if not normalized or not self._is_valid_business_email(normalized):
            return
        score = self._score_email(normalized, source, page_type)
        existing = candidates.get(normalized)
        if existing:
            existing["score"] = max(existing["score"], score)
            if source not in existing["sources"]:
                existing["sources"].append(source)
            existing["occurrences"] += 1
            return
        candidates[normalized] = {
            "email": normalized,
            "score": score,
            "sources": [source],
            "page_url": page_url,
            "page_type": page_type,
            "occurrences": 1,
        }

    def _merge_email_candidates(self, merged: dict[str, dict[str, Any]], page_candidates: list[dict[str, Any]]) -> None:
        """Merge page-level email candidates into the global candidate pool."""
        for candidate in page_candidates:
            email = candidate["email"]
            existing = merged.get(email)
            if existing:
                existing["score"] = max(existing["score"], candidate["score"])
                existing["occurrences"] += candidate.get("occurrences", 1)
                existing["sources"] = sorted(set(existing["sources"] + candidate.get("sources", [])))
                continue
            merged[email] = {
                "email": email,
                "score": candidate["score"],
                "sources": list(candidate.get("sources", [])),
                "occurrences": candidate.get("occurrences", 1),
            }

    def _extract_emails(self, text: str) -> list[str]:
        """Extract email candidates from visible or raw text."""
        return list(dict.fromkeys(self.EMAIL_PATTERN.findall(self._normalize_text_for_email_scan(text))))

    def _extract_mailto_emails(self, soup: BeautifulSoup) -> list[str]:
        """Extract emails from mailto links."""
        emails: list[str] = []
        for link in soup.find_all("a", href=True):
            href = link["href"].strip()
            if href.lower().startswith("mailto:"):
                emails.extend(self._extract_emails(unquote(href.split(":", 1)[1]).split("?", 1)[0]))
        return emails

    def _extract_structured_data_emails(self, soup: BeautifulSoup) -> list[str]:
        """Extract emails from JSON-LD, microdata and meta content."""
        emails: list[str] = []
        for script in soup.find_all("script", attrs={"type": re.compile("ld\\+json", re.IGNORECASE)}):
            raw_json = script.string or script.get_text(" ", strip=True)
            if not raw_json:
                continue
            try:
                emails.extend(self._collect_emails_from_json(json.loads(raw_json)))
            except json.JSONDecodeError:
                emails.extend(self._extract_emails(raw_json))
        for tag in soup.find_all(attrs={"itemprop": re.compile("email", re.IGNORECASE)}):
            emails.extend(self._extract_emails(tag.get("content", "")))
            emails.extend(self._extract_emails(tag.get("href", "")))
            emails.extend(self._extract_emails(tag.get_text(" ", strip=True)))
        for tag in soup.find_all("meta", attrs={"content": True}):
            emails.extend(self._extract_emails(tag.get("content", "")))
        return list(dict.fromkeys(emails))

    def _collect_emails_from_json(self, payload: Any) -> list[str]:
        """Walk structured data recursively to recover email values."""
        found: list[str] = []
        if isinstance(payload, dict):
            for key, value in payload.items():
                if isinstance(value, str) and "email" in key.lower():
                    found.extend(self._extract_emails(value))
                found.extend(self._collect_emails_from_json(value))
        elif isinstance(payload, list):
            for item in payload:
                found.extend(self._collect_emails_from_json(item))
        elif isinstance(payload, str):
            found.extend(self._extract_emails(payload))
        return found

    def _extract_targeted_text(self, soup: BeautifulSoup) -> str:
        """Extract footer and contact-like blocks where business emails often appear."""
        snippets: list[str] = []
        for tag in soup.find_all(True):
            classes = " ".join(tag.get("class", []))
            identifier = " ".join([tag.get("id", ""), classes, tag.name]).lower()
            if any(keyword in identifier for keyword in self.SECTION_KEYWORDS):
                text = tag.get_text(" ", strip=True)
                if text:
                    snippets.append(text)
        return " ".join(snippets)

    def _extract_phones(self, text: str) -> list[str]:
        """Extract international phone numbers from text."""
        phones: list[str] = []
        for match in self.PHONE_PATTERN.findall(text or ""):
            normalized = re.sub(r"\s+", " ", match).strip(" .-/")
            if len(re.sub(r"\D", "", normalized)) >= 9 and normalized not in phones:
                phones.append(normalized)
        return phones

    def _extract_tel_links(self, soup: BeautifulSoup) -> list[str]:
        """Extract phone numbers from tel links."""
        phones: list[str] = []
        for link in soup.find_all("a", href=True):
            href = (link.get("href") or "").strip()
            if href.lower().startswith("tel:"):
                raw_number = unquote(href.split(":", 1)[1]).split("?", 1)[0]
                digits = re.sub(r"[^\d+]", "", raw_number)
                if digits and len(re.sub(r"\D", "", digits)) >= 9:
                    phones.append(digits)
        return phones

    def _extract_contact_form_data(self, soup: BeautifulSoup, page_url: str, page_type: str) -> dict[str, Any]:
        """Detect contact forms and contact-form-friendly pages."""
        signals: list[str] = []
        forms = soup.find_all("form")
        for form in forms:
            field_tokens: list[str] = []
            for field in form.find_all(["input", "textarea", "select"]):
                field_tokens.extend([field.get("name", ""), field.get("id", ""), field.get("placeholder", ""), field.get("type", ""), field.get("aria-label", "")])
            field_text = " ".join(field_tokens).lower()
            button_text = " ".join(button.get_text(" ", strip=True) for button in form.find_all(["button", "label"]))
            action_text = f"{form.get('action', '')} {button_text}".lower()
            has_name = any(hint in field_text for hint in self.NAME_FIELD_HINTS)
            has_email = any(hint in field_text for hint in self.EMAIL_FIELD_HINTS)
            has_message = any(hint in field_text for hint in self.MESSAGE_FIELD_HINTS) or bool(form.find("textarea"))
            has_contact_cta = any(keyword in action_text for keyword in self.FORM_KEYWORDS)
            if has_name:
                signals.append("name_field")
            if has_email:
                signals.append("email_field")
            if has_message:
                signals.append("message_field")
            if has_contact_cta:
                signals.append("contact_cta")
            if (has_name and has_message) or (has_email and has_message) or (has_name and has_email) or (page_type == "contact" and (has_name or has_email or has_message)):
                signals.append("html_form")
        link_text = " ".join(f"{link.get('href', '')} {link.get_text(' ', strip=True)}" for link in soup.find_all(["a", "button"])).lower()
        if any(keyword in link_text for keyword in self.FORM_KEYWORDS):
            signals.append("contact_keywords")
        detected = "html_form" in signals or ("contact_keywords" in signals and bool(forms))
        return {"detected": detected, "url": page_url if detected else None, "signals": self._dedupe_strings(signals)}

    def _extract_social_profiles(self, soup: BeautifulSoup, page_url: str) -> dict[str, str]:
        """Extract usable business social/contact profile links."""
        profiles: dict[str, str] = {}
        for link in soup.find_all("a", href=True):
            href = (link.get("href") or "").strip()
            if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
                continue
            full_url = urljoin(page_url, href)
            hostname = urlparse(full_url).netloc.lower()
            if not hostname:
                continue
            for field_name, host_patterns in self.SOCIAL_HOSTS.items():
                if any(pattern in hostname for pattern in host_patterns):
                    normalized_url = self._normalize_social_url(full_url)
                    if normalized_url and self._is_usable_social_profile(normalized_url, field_name):
                        profiles.setdefault(field_name, normalized_url)
        return profiles

    def _merge_social_profiles(self, merged: dict[str, str], page_profiles: dict[str, str]) -> None:
        """Merge extracted social URLs while keeping the first stable value."""
        for key, value in page_profiles.items():
            if value and key not in merged:
                merged[key] = value

    def _discover_pages(self, soup: BeautifulSoup, base_url: str) -> list[dict[str, str]]:
        """Discover internal contact-like pages from links and common paths."""
        pages: list[dict[str, str]] = []
        for link in soup.find_all("a", href=True):
            href = (link["href"] or "").strip()
            if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
                continue
            full_url = urljoin(base_url, href)
            if not self._is_same_domain(base_url, full_url):
                continue
            page_type = self._infer_page_type(f"{href} {link.get_text(' ', strip=True)}".lower())
            if page_type != "other":
                pages.append({"url": full_url, "page_type": page_type, "source": "discovered_link"})
        for path in self.DISCOVERY_PATHS:
            pages.append({"url": urljoin(base_url, path), "page_type": self._infer_page_type(path), "source": "common_path"})
        return pages

    def _dedupe_page_candidates(self, pages: list[dict[str, str]]) -> list[dict[str, str]]:
        """Deduplicate page candidates while preserving priority order."""
        deduped: list[dict[str, str]] = []
        seen: set[str] = set()
        for page in pages:
            normalized_url = self._normalize_candidate_url(page["url"])
            if normalized_url not in seen:
                seen.add(normalized_url)
                deduped.append({**page, "url": normalized_url})
        return deduped

    def _normalize_candidate_url(self, url: str) -> str:
        """Normalize URLs for candidate deduplication."""
        parsed = urlparse(url)
        path = parsed.path or "/"
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")
        return parsed._replace(path=path, fragment="", query="").geturl()

    def _normalize_social_url(self, url: str) -> Optional[str]:
        """Normalize social profile URLs while keeping useful WhatsApp parameters."""
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return None
        query = parsed.query if ("whatsapp" in parsed.netloc or "wa.me" in parsed.netloc) else ""
        path = parsed.path.rstrip("/") or "/"
        return parsed._replace(path=path, fragment="", query=query).geturl()

    def _is_usable_social_profile(self, url: str, field_name: str) -> bool:
        """Reject obvious share/login URLs and keep only outreach-usable profiles."""
        normalized = url.lower()
        if any(token in normalized for token in self.BAD_SOCIAL_TOKENS):
            return False
        if field_name == "linkedin_url":
            return any(segment in normalized for segment in ["/company/", "/in/", "/showcase/"])
        if field_name == "whatsapp_url":
            return "phone=" in normalized or "wa.me/" in normalized
        path_segments = [segment for segment in urlparse(url).path.split("/") if segment]
        return len(path_segments) >= 1

    def _normalize_text_for_email_scan(self, text: str) -> str:
        """Decode common obfuscations before applying regex extraction."""
        normalized = unescape(text or "")
        replacements = [
            (r"\s*\[\s*at\s*\]\s*", "@"),
            (r"\s*\(\s*at\s*\)\s*", "@"),
            (r"\s+at\s+", "@"),
            (r"\s*\[\s*dot\s*\]\s*", "."),
            (r"\s*\(\s*dot\s*\)\s*", "."),
            (r"\s+dot\s+", "."),
            (r"%40", "@"),
        ]
        for pattern, replacement in replacements:
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\s*@\s*", "@", normalized)
        normalized = re.sub(r"\s*\.\s*", ".", normalized)
        return normalized

    def _normalize_email(self, email: str) -> Optional[str]:
        """Normalize an email candidate into a clean canonical value."""
        if not email:
            return None
        normalized = self._normalize_text_for_email_scan(email).strip().strip(".,;:<>[](){}\"'")
        if normalized.lower().startswith("mailto:"):
            normalized = normalized.split(":", 1)[1]
        normalized = normalized.split("?", 1)[0].strip().lower()
        return normalized if self.EMAIL_PATTERN.fullmatch(normalized) else None

    def _is_valid_business_email(self, email: str) -> bool:
        """Reject no-reply addresses, placeholder domains and obvious fake emails."""
        local_part, _, domain = email.partition("@")
        if not local_part or not domain:
            return False
        clean_local = local_part.replace(".", "").replace("_", "").replace("-", "")
        if clean_local in {item.replace("-", "") for item in self.BAD_LOCAL_PARTS}:
            return False
        if domain in self.BAD_DOMAINS or domain.endswith(".example"):
            return False
        return not any(token in domain for token in ["example", "placeholder", "invalid"])

    def _score_email(self, email: str, source: str, page_type: str) -> int:
        """Score one candidate to prefer real business contact emails."""
        local_part = email.split("@", 1)[0]
        score = self.SOURCE_SCORES.get(source, 0) + self.PAGE_SCORES.get(page_type, 0)
        for prefix, bonus in self.LOCAL_PART_SCORES.items():
            if local_part.startswith(prefix):
                score += bonus
                break
        return score - 5 if "+" in local_part else score

    def _select_best_email(self, candidates: dict[str, dict[str, Any]]) -> Optional[str]:
        """Select the highest-confidence email from all candidates."""
        if not candidates:
            return None
        ranked = sorted(candidates.values(), key=lambda item: (item["score"], item.get("occurrences", 0), -len(item["email"])), reverse=True)
        return ranked[0]["email"]

    def _select_best_phone(self, phones: list[str]) -> Optional[str]:
        """Pick the first reasonable phone number found across scanned pages."""
        deduped = self._dedupe_strings(phones)
        return deduped[0] if deduped else None

    def _select_best_contact_form(self, urls: list[str], scanned_pages: list[dict[str, Any]]) -> Optional[str]:
        """Pick the first detected contact form page."""
        deduped = self._dedupe_strings(urls)
        if deduped:
            return deduped[0]
        for page in scanned_pages:
            if page["status"] == "ok" and page.get("contact_form_detected") and page.get("contact_form_url"):
                return page["contact_form_url"]
        return None

    def _pick_first_contact_page(self, scanned_pages: list[dict[str, Any]]) -> Optional[str]:
        """Return the first successfully scanned contact-like page."""
        for page in scanned_pages:
            if page["status"] == "ok" and page["page_type"] in {"contact", "about", "legal"}:
                return page["url"]
        return None

    def _determine_fallback_reason(self, scanned_pages: list[dict[str, Any]], email_candidates: dict[str, dict[str, Any]], selected_email: Optional[str]) -> str:
        """Explain why no email was selected."""
        if selected_email:
            return ""
        if not scanned_pages:
            return "no_pages_scanned"
        if not any(page["status"] == "ok" for page in scanned_pages):
            return "page_fetch_failed"
        if email_candidates:
            return "no_ranked_email_selected"
        return "no_email_found"

    def _determine_recommended_channel(self, *, email: Optional[str], phone: Optional[str], contact_form_url: Optional[str], instagram_url: Optional[str], facebook_url: Optional[str]) -> str:
        """Apply the outreach channel fallback priority."""
        if email:
            return "email"
        if phone:
            return "phone"
        if contact_form_url:
            return "contact_form"
        if instagram_url:
            return "instagram"
        if facebook_url:
            return "facebook"
        return "unavailable"

    def _infer_page_type(self, text: str) -> str:
        """Infer page type from a URL or anchor label."""
        normalized = (text or "").lower()
        if any(keyword in normalized for keyword in self.PAGE_KEYWORDS["contact"]):
            return "contact"
        if any(keyword in normalized for keyword in self.PAGE_KEYWORDS["legal"]):
            return "legal"
        if any(keyword in normalized for keyword in self.PAGE_KEYWORDS["about"]):
            return "about"
        return "other"

    def _is_same_domain(self, base_url: str, candidate_url: str) -> bool:
        """Limit scanning to internal pages."""
        return not urlparse(candidate_url).netloc.lower().lstrip("www.") or urlparse(base_url).netloc.lower().lstrip("www.") == urlparse(candidate_url).netloc.lower().lstrip("www.")

    def _normalize_website_url(self, website: str) -> str:
        """Ensure the target website has a scheme."""
        return website if website.startswith(("http://", "https://")) else f"https://{website}"

    def _dedupe_strings(self, values: list[str]) -> list[str]:
        """Deduplicate strings while preserving order."""
        seen: list[str] = []
        for value in values:
            cleaned = (value or "").strip()
            if cleaned and cleaned not in seen:
                seen.append(cleaned)
        return seen
