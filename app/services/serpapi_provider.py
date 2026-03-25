"""
SerpApi provider
"""
from __future__ import annotations

from typing import Any, Dict, List
from urllib.parse import urlparse

import requests

from app.core.config import settings
from app.core.search_config import should_skip_domain
from app.core.country_config import detect_country
from app.core.logging import logger
from app.services.provider_base import ProviderBase, SearchProviderResult


class SerpApiProvider(ProviderBase):
    """Provider using SerpApi."""

    def is_available(self) -> bool:
        return bool(settings.SERPAPI_KEY)

    async def search_leads(
        self,
        location: str,
        category: str,
        limit: int,
        search_queries: List[str] | None = None,
        max_candidates: int | None = None,
    ) -> SearchProviderResult:
        """Search using SerpApi across multiple queries."""
        result = SearchProviderResult(provider=self.__class__.__name__)
        if not self.is_available():
            result.notes = "provider_unavailable"
            return result

        queries = search_queries or [f"{category} {location}"]
        candidate_limit = max_candidates or max(limit * 2, limit)
        country = detect_country(location)
        seen_websites = set()

        for query in queries:
            if len(result.leads) >= candidate_limit:
                break

            try:
                response = requests.get(
                    "https://serpapi.com/search",
                    params={
                        "engine": "google",
                        "q": query,
                        "location": location,
                        "num": min(candidate_limit, 10),
                        "api_key": settings.SERPAPI_KEY,
                    },
                    timeout=settings.REQUEST_TIMEOUT,
                )
                response.raise_for_status()
                data = response.json()
                organic_results = data.get("organic_results", [])
                kept = 0
                result.raw_count += len(organic_results)

                for item in organic_results:
                    if len(result.leads) >= candidate_limit:
                        break

                    website = (item.get("link") or "").strip()
                    if not website:
                        continue

                    domain = urlparse(website).netloc.lower()
                    if website in seen_websites or should_skip_domain(domain):
                        continue

                    result.leads.append(
                        {
                            "business_name": item.get("title", "").strip(),
                            "category": category,
                            "location": location,
                            "country": country,
                            "website": website,
                            "address": item.get("address", location),
                            "source": "serpapi",
                        }
                    )
                    seen_websites.add(website)
                    kept += 1

                result.queries_attempted.append(
                    {"query": query, "raw_results": len(organic_results), "kept_candidates": kept}
                )
            except Exception as e:
                logger.warning(f"SerpApiProvider query failed for '{query}': {e}")
                result.queries_attempted.append(
                    {"query": query, "raw_results": 0, "kept_candidates": 0, "error": str(e)}
                )

        result.leads = result.leads[:candidate_limit]
        return result
