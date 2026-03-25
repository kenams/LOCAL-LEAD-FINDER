"""
Simple provider using public search results as a fallback.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List
from urllib.parse import parse_qs, unquote, urlparse

import requests
from bs4 import BeautifulSoup

from app.core.config import settings
from app.core.search_config import should_skip_domain
from app.core.logging import logger
from app.services.provider_base import ProviderBase, SearchProviderResult


class SimpleProvider(ProviderBase):
    """Fallback provider using DuckDuckGo HTML search results."""

    SEARCH_URL = "https://html.duckduckgo.com/html/"
    BING_SEARCH_URL = "https://www.bing.com/search"
    EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    PHONE_PATTERN = re.compile(r"(?:(?:\+|00)?(?:33|41|1|61)\s?(?:\(0\)\s?)?[\d\s().-]{7,16}|0\d(?:[\s().-]*\d){8,10})")

    def is_available(self) -> bool:
        return True

    async def search_leads(
        self,
        location: str,
        category: str,
        limit: int,
        search_queries: List[str] | None = None,
        max_candidates: int | None = None,
    ) -> SearchProviderResult:
        """Search leads from public HTML results with a deterministic fallback."""
        queries = search_queries or [f"{category} {location}"]
        candidate_limit = max_candidates or max(limit * 2, limit)
        provider_result = SearchProviderResult(provider=self.__class__.__name__)
        seen_websites = set()

        for query in queries:
            if len(provider_result.leads) >= candidate_limit:
                break

            try:
                query_result = self._search_query(query, location, category, candidate_limit, seen_websites)
                provider_result.raw_count += query_result["raw_results"]
                provider_result.leads.extend(query_result["leads"])
                provider_result.queries_attempted.append(
                    {
                        "query": query,
                        "engine": query_result["engine"],
                        "raw_results": query_result["raw_results"],
                        "kept_candidates": len(query_result["leads"]),
                    }
                )
            except Exception as e:
                logger.warning(f"SimpleProvider query failed for '{query}': {e}")
                provider_result.queries_attempted.append(
                    {"query": query, "raw_results": 0, "kept_candidates": 0, "error": str(e)}
                )

        if not provider_result.leads:
            provider_result.notes = "no_live_results"

        provider_result.leads = provider_result.leads[:candidate_limit]
        logger.info(
            f"SimpleProvider kept {len(provider_result.leads)} candidates for {location}/{category} across {len(provider_result.queries_attempted)} queries"
        )
        return provider_result

    def _search_query(
        self,
        query: str,
        location: str,
        category: str,
        candidate_limit: int,
        seen_websites: set[str],
    ) -> Dict[str, Any]:
        """Try multiple public search engines for a single query."""
        engines = [
            ("bing", self._search_bing),
            ("duckduckgo", self._search_duckduckgo),
        ]
        last_error = None

        for engine_name, engine_fn in engines:
            try:
                leads, raw_count = engine_fn(query, location, category, candidate_limit, seen_websites)
                if raw_count or leads:
                    return {"engine": engine_name, "raw_results": raw_count, "leads": leads}
            except Exception as e:
                last_error = e
                logger.warning(f"SimpleProvider {engine_name} failed for '{query}': {e}")

        if last_error:
            raise last_error
        return {"engine": "none", "raw_results": 0, "leads": []}

    def _search_bing(
        self,
        query: str,
        location: str,
        category: str,
        candidate_limit: int,
        seen_websites: set[str],
    ) -> tuple[List[Dict[str, Any]], int]:
        """Search Bing HTML results."""
        response = requests.get(
            self.BING_SEARCH_URL,
            params={"q": query, "count": min(candidate_limit, 20)},
            headers={"User-Agent": settings.USER_AGENT},
            timeout=settings.REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        return self._parse_bing_results(soup, location, category, candidate_limit, seen_websites)

    def _search_duckduckgo(
        self,
        query: str,
        location: str,
        category: str,
        candidate_limit: int,
        seen_websites: set[str],
    ) -> tuple[List[Dict[str, Any]], int]:
        """Search DuckDuckGo HTML results."""
        response = requests.post(
            self.SEARCH_URL,
            data={"q": query},
            headers={"User-Agent": settings.USER_AGENT},
            timeout=settings.REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        return self._parse_duckduckgo_results(soup, location, category, candidate_limit, seen_websites)

    def _parse_bing_results(
        self,
        soup: BeautifulSoup,
        location: str,
        category: str,
        candidate_limit: int,
        seen_websites: set[str],
    ) -> tuple[List[Dict[str, Any]], int]:
        """Parse Bing result cards."""
        leads: List[Dict[str, Any]] = []
        raw_count = 0

        for result in soup.select("li.b_algo"):
            link = result.select_one("h2 a")
            if not link:
                continue

            raw_count += 1
            website = self._normalize_website(link.get("href") or "")
            if not website or website in seen_websites:
                continue

            domain = urlparse(website).netloc.lower()
            if should_skip_domain(domain):
                continue

            title = link.get_text(" ", strip=True)
            snippet_node = result.select_one(".b_caption p")
            snippet = snippet_node.get_text(" ", strip=True) if snippet_node else ""
            if self._is_directory_result(title, snippet):
                continue
            leads.append(
                {
                    "business_name": self._clean_business_name(title, category, location),
                    "category": category,
                    "location": location,
                    "website": website,
                    "address": location,
                    "email": self._extract_email(snippet),
                    "phone": self._extract_phone(snippet),
                    "source": "bing_html",
                    "notes": snippet,
                }
            )
            seen_websites.add(website)

            if len(leads) >= candidate_limit:
                break

        return leads, raw_count

    def _parse_duckduckgo_results(
        self,
        soup: BeautifulSoup,
        location: str,
        category: str,
        candidate_limit: int,
        seen_websites: set[str],
    ) -> tuple[List[Dict[str, Any]], int]:
        """Parse DuckDuckGo HTML result cards."""
        leads: List[Dict[str, Any]] = []
        raw_count = 0

        for result in soup.select(".result"):
            link = result.select_one(".result__a")
            if not link:
                continue

            raw_count += 1
            website = self._normalize_website(link.get("href") or "")
            if not website or website in seen_websites:
                continue

            domain = urlparse(website).netloc.lower()
            if should_skip_domain(domain):
                continue

            title = link.get_text(" ", strip=True)
            snippet_node = result.select_one(".result__snippet")
            snippet = snippet_node.get_text(" ", strip=True) if snippet_node else ""
            if self._is_directory_result(title, snippet):
                continue

            leads.append(
                {
                    "business_name": self._clean_business_name(title, category, location),
                    "category": category,
                    "location": location,
                    "website": website,
                    "address": location,
                    "email": self._extract_email(snippet),
                    "phone": self._extract_phone(snippet),
                    "source": "duckduckgo_html",
                    "notes": snippet,
                }
            )
            seen_websites.add(website)

            if len(leads) >= candidate_limit:
                break

        return leads, raw_count

    def _clean_business_name(self, title: str, category: str, location: str) -> str:
        """Extract a readable business name from a search result title."""
        cleaned = title.split("|", 1)[0].split(" - ", 1)[0].strip()
        if cleaned and cleaned.lower() not in {"contact", "accueil", "home"}:
            return cleaned
        return f"{category.title()} {location}"

    def _normalize_website(self, href: str) -> str:
        """Extract the final target URL and keep only the site root."""
        href = href.strip()
        if not href:
            return ""

        parsed = urlparse(href)
        if "duckduckgo.com" in parsed.netloc:
            query = parse_qs(parsed.query)
            if "uddg" in query and query["uddg"]:
                href = unquote(query["uddg"][0])
                parsed = urlparse(href)

        if not parsed.scheme or not parsed.netloc:
            return ""

        return f"{parsed.scheme}://{parsed.netloc}/"

    def _extract_email(self, text: str) -> str | None:
        match = self.EMAIL_PATTERN.search(text or "")
        return match.group(0) if match else None

    def _extract_phone(self, text: str) -> str | None:
        match = self.PHONE_PATTERN.search(text or "")
        return match.group(0).strip(" .-") if match else None

    def _is_directory_result(self, title: str, snippet: str = "") -> bool:
        normalized = f"{title} {snippet}".lower()
        blocked_terms = [
            "yellow pages",
            "tripadvisor",
            "yelp",
            "list of",
            "directory",
            "top 10",
            "what does",
            "salary",
            "job description",
            "career",
            "training",
            "course",
            "wikipedia",
            "definition",
            "indeed",
            "ziprecruiter",
            "ccohs",
            "stack exchange",
            "stack overflow",
            "reddit",
            "transfermarkt",
            "forum",
        ]
        return any(term in normalized for term in blocked_terms)
