"""
OpenStreetMap provider using Nominatim + Overpass as a resilient discovery fallback.
"""
from __future__ import annotations

from typing import Any, Dict, List
from urllib.parse import urlparse

import requests

from app.core.config import settings
from app.core.country_config import detect_country
from app.core.logging import logger
from app.core.search_config import get_osm_tags, should_skip_domain
from app.services.provider_base import ProviderBase, SearchProviderResult


class OSMProvider(ProviderBase):
    """Fallback provider using OpenStreetMap business data."""

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
        """Search business candidates from OSM tags near a geocoded city center."""
        result = SearchProviderResult(provider=self.__class__.__name__)
        candidate_limit = max_candidates or max(limit * 2, limit)
        country = detect_country(location)
        search_tags = get_osm_tags(category)
        search_queries = search_queries or [f"{category} {location}"]
        seen_keys: set[str] = set()

        geocode = self._geocode_location(location, country)
        if not geocode:
            result.notes = "location_not_geocoded"
            return result

        radius = self._get_search_radius(country, limit)

        for tag in search_tags:
            if len(result.leads) >= candidate_limit:
                break

            tag_result = self._query_overpass(
                geocode=geocode,
                tag_key=tag["key"],
                tag_value=tag["value"],
                location=location,
                category=category,
                country=country,
                radius=radius,
                candidate_limit=candidate_limit,
                seen_keys=seen_keys,
            )
            result.raw_count += tag_result["raw_results"]
            result.leads.extend(tag_result["leads"])
            result.queries_attempted.append(
                {
                    "query": f'{tag["key"]}={tag["value"]}',
                    "radius_m": radius,
                    "raw_results": tag_result["raw_results"],
                    "kept_candidates": len(tag_result["leads"]),
                    "endpoint": tag_result["endpoint"],
                    "notes": tag_result["notes"],
                }
            )

        if len(result.leads) < limit:
            fallback_result = self._query_nominatim_text(
                queries=search_queries,
                location=location,
                category=category,
                country=country,
                candidate_limit=candidate_limit,
                seen_keys=seen_keys,
            )
            result.raw_count += fallback_result["raw_results"]
            result.leads.extend(fallback_result["leads"])
            result.queries_attempted.extend(fallback_result["queries_attempted"])
            if fallback_result["used_fallback"]:
                result.fallback_triggered = True
                result.notes = fallback_result["notes"] or result.notes

        result.leads = self._rank_leads(result.leads)[:candidate_limit]
        if not result.leads and not result.notes:
            result.notes = "no_osm_results" if search_tags else "no_osm_mapping"
        return result

    def _geocode_location(self, location: str, country: str) -> Dict[str, Any] | None:
        """Geocode a location to latitude/longitude."""
        country_code = country.lower() if country else ""
        response = requests.get(
            settings.OSM_NOMINATIM_URL,
            params={
                "q": location,
                "format": "jsonv2",
                "limit": 1,
                "countrycodes": country_code or None,
            },
            headers={"User-Agent": settings.USER_AGENT},
            timeout=settings.REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        return payload[0] if payload else None

    def _query_overpass(
        self,
        geocode: Dict[str, Any],
        tag_key: str,
        tag_value: str,
        location: str,
        category: str,
        country: str,
        radius: int,
        candidate_limit: int,
        seen_keys: set[str],
    ) -> Dict[str, Any]:
        """Query the configured Overpass endpoints until one succeeds."""
        query = self._build_overpass_query(tag_key, tag_value, geocode["lat"], geocode["lon"], radius, candidate_limit)
        errors: List[str] = []

        for endpoint in settings.OSM_OVERPASS_URLS:
            try:
                response = requests.post(
                    endpoint,
                    data=query.encode("utf-8"),
                    headers={
                        "User-Agent": settings.USER_AGENT,
                        "Content-Type": "text/plain; charset=utf-8",
                    },
                    timeout=max(settings.REQUEST_TIMEOUT, 45),
                )
                if not response.ok:
                    errors.append(f"{endpoint} ({response.status_code})")
                    continue

                payload = response.json()
                leads = self._parse_elements(
                    payload.get("elements", []),
                    location=location,
                    category=category,
                    country=country,
                    seen_keys=seen_keys,
                )
                return {
                    "endpoint": endpoint,
                    "raw_results": len(payload.get("elements", [])),
                    "leads": leads,
                    "notes": "",
                }
            except Exception as exc:
                errors.append(f"{endpoint} ({exc})")

        logger.warning(
            f"OSMProvider could not query Overpass for {location}/{category} with {tag_key}={tag_value}: {errors}"
        )
        return {"endpoint": "", "raw_results": 0, "leads": [], "notes": "; ".join(errors[:2])}

    def _query_nominatim_text(
        self,
        queries: List[str],
        location: str,
        category: str,
        country: str,
        candidate_limit: int,
        seen_keys: set[str],
    ) -> Dict[str, Any]:
        """Fallback to Nominatim text search when Overpass is empty or unavailable."""
        raw_results = 0
        leads: List[Dict[str, Any]] = []
        diagnostics: List[Dict[str, Any]] = []
        notes = ""

        for query in queries[: min(len(queries), 6)]:
            if len(leads) >= candidate_limit:
                break

            try:
                response = requests.get(
                    settings.OSM_NOMINATIM_URL,
                    params={
                        "q": query,
                        "format": "jsonv2",
                        "limit": min(max(candidate_limit, 10), 10),
                        "countrycodes": country.lower() or None,
                        "addressdetails": 1,
                        "namedetails": 1,
                        "extratags": 1,
                        "dedupe": 1,
                    },
                    headers={"User-Agent": settings.USER_AGENT},
                    timeout=settings.REQUEST_TIMEOUT,
                )
                if not response.ok:
                    diagnostics.append(
                        {
                            "query": query,
                            "engine": "nominatim_text",
                            "raw_results": 0,
                            "kept_candidates": 0,
                            "status_code": response.status_code,
                        }
                    )
                    notes = notes or f"nominatim_{response.status_code}"
                    continue

                payload = response.json()
                query_leads = self._parse_nominatim_results(
                    payload,
                    location=location,
                    category=category,
                    country=country,
                    seen_keys=seen_keys,
                )
                raw_results += len(payload)
                leads.extend(query_leads)
                diagnostics.append(
                    {
                        "query": query,
                        "engine": "nominatim_text",
                        "raw_results": len(payload),
                        "kept_candidates": len(query_leads),
                    }
                )
            except Exception as exc:
                diagnostics.append(
                    {
                        "query": query,
                        "engine": "nominatim_text",
                        "raw_results": 0,
                        "kept_candidates": 0,
                        "error": str(exc),
                    }
                )
                notes = notes or "nominatim_error"

        return {
            "raw_results": raw_results,
            "leads": leads,
            "queries_attempted": diagnostics,
            "used_fallback": bool(raw_results or leads or diagnostics),
            "notes": notes or ("nominatim_text_fallback" if leads else ""),
        }

    def _build_overpass_query(
        self,
        tag_key: str,
        tag_value: str,
        lat: str,
        lon: str,
        radius: int,
        candidate_limit: int,
    ) -> str:
        """Build a compact Overpass query."""
        return (
            f'[out:json][timeout:20];'
            f'(node["{tag_key}"="{tag_value}"](around:{radius},{lat},{lon});'
            f'way["{tag_key}"="{tag_value}"](around:{radius},{lat},{lon});'
            f'relation["{tag_key}"="{tag_value}"](around:{radius},{lat},{lon}););'
            f"out center tags {max(candidate_limit, 10)};"
        )

    def _parse_elements(
        self,
        elements: List[Dict[str, Any]],
        location: str,
        category: str,
        country: str,
        seen_keys: set[str],
    ) -> List[Dict[str, Any]]:
        """Convert OSM elements to lead dictionaries."""
        leads: List[Dict[str, Any]] = []

        for element in elements:
            tags = element.get("tags", {})
            business_name = (tags.get("name") or "").strip()
            if not business_name:
                continue

            website = self._normalize_website(
                tags.get("website") or tags.get("contact:website") or tags.get("url") or ""
            )
            phone = tags.get("phone") or tags.get("contact:phone")
            email = tags.get("email") or tags.get("contact:email")

            key = website or f"{business_name.lower()}::{phone or ''}::{location.lower()}"
            if key in seen_keys:
                continue

            if website:
                domain = urlparse(website).netloc.lower()
                if should_skip_domain(domain):
                    continue

            seen_keys.add(key)
            leads.append(
                {
                    "business_name": business_name,
                    "category": category,
                    "location": location,
                    "country": country,
                    "website": website,
                    "address": self._build_address(tags, location),
                    "phone": phone,
                    "email": email,
                    "source": "osm_overpass",
                    "notes": self._build_notes(tags),
                }
            )

        return leads

    def _parse_nominatim_results(
        self,
        payload: List[Dict[str, Any]],
        location: str,
        category: str,
        country: str,
        seen_keys: set[str],
    ) -> List[Dict[str, Any]]:
        """Convert Nominatim text-search payloads into lead dictionaries."""
        leads: List[Dict[str, Any]] = []

        for item in payload:
            business_name = (
                item.get("namedetails", {}).get("name")
                or item.get("name")
                or (item.get("display_name") or "").split(",", 1)[0].strip()
            )
            if not business_name:
                continue

            item_class = (item.get("class") or "").lower()
            if item_class and item_class not in {"shop", "amenity", "craft", "office", "tourism", "leisure"}:
                continue

            extratags = item.get("extratags") or {}
            website = self._normalize_website(
                extratags.get("website") or extratags.get("contact:website") or extratags.get("url") or ""
            )
            phone = extratags.get("phone") or extratags.get("contact:phone")
            email = extratags.get("email") or extratags.get("contact:email")

            key = website or f"{business_name.lower()}::{phone or ''}::{location.lower()}"
            if key in seen_keys:
                continue

            if website:
                domain = urlparse(website).netloc.lower()
                if should_skip_domain(domain):
                    continue

            seen_keys.add(key)
            leads.append(
                {
                    "business_name": business_name,
                    "category": category,
                    "location": location,
                    "country": country,
                    "website": website,
                    "address": self._build_nominatim_address(item, location),
                    "phone": phone,
                    "email": email,
                    "source": "osm_nominatim",
                    "notes": self._build_nominatim_notes(item),
                }
            )

        return leads

    def _rank_leads(self, leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank OSM leads to favor websites and direct contact information."""
        return sorted(
            leads,
            key=lambda lead: (
                1 if lead.get("website") else 0,
                1 if lead.get("email") else 0,
                1 if lead.get("phone") else 0,
                len(lead.get("business_name", "")),
            ),
            reverse=True,
        )

    def _normalize_website(self, website: str) -> str:
        """Normalize a website URL."""
        normalized = (website or "").strip()
        if not normalized:
            return ""
        if not normalized.startswith(("http://", "https://")):
            normalized = f"https://{normalized.lstrip('/')}"
        parsed = urlparse(normalized)
        if not parsed.scheme or not parsed.netloc:
            return ""
        return f"{parsed.scheme}://{parsed.netloc}/"

    def _build_address(self, tags: Dict[str, Any], fallback_location: str) -> str:
        """Build a compact address string from OSM tags."""
        street_parts = [
            tags.get("addr:housenumber"),
            tags.get("addr:street"),
        ]
        city_parts = [
            tags.get("addr:postcode"),
            tags.get("addr:city") or fallback_location,
        ]
        parts = [" ".join(part for part in street_parts if part), " ".join(part for part in city_parts if part)]
        address = ", ".join(part for part in parts if part).strip(", ")
        return address or fallback_location

    def _build_notes(self, tags: Dict[str, Any]) -> str:
        """Extract a short note string for debugging."""
        note_parts = []
        for key in ["brand", "operator", "description", "opening_hours"]:
            value = tags.get(key)
            if value:
                note_parts.append(f"{key}={value}")
        return " | ".join(note_parts)

    def _build_nominatim_address(self, item: Dict[str, Any], fallback_location: str) -> str:
        """Build a compact address string from Nominatim payloads."""
        address = item.get("address") or {}
        street_parts = [address.get("house_number"), address.get("road")]
        city_parts = [address.get("postcode"), address.get("city") or address.get("town") or fallback_location]
        parts = [" ".join(part for part in street_parts if part), " ".join(part for part in city_parts if part)]
        compact = ", ".join(part for part in parts if part).strip(", ")
        return compact or (item.get("display_name") or fallback_location)

    def _build_nominatim_notes(self, item: Dict[str, Any]) -> str:
        """Extract a short note string for debugging from Nominatim payloads."""
        note_parts = []
        if item.get("class") and item.get("type"):
            note_parts.append(f'{item["class"]}:{item["type"]}')
        extratags = item.get("extratags") or {}
        for key in ["brand", "operator", "description", "opening_hours"]:
            value = extratags.get(key)
            if value:
                note_parts.append(f"{key}={value}")
        return " | ".join(note_parts)

    def _get_search_radius(self, country: str, limit: int) -> int:
        """Return a pragmatic search radius by market."""
        base_radius = {"US": 12000, "AU": 12000, "CH": 9000, "FR": 9000, "GB": 10000}.get(country, 9000)
        adjusted_radius = base_radius + min(limit, 20) * 150
        return min(adjusted_radius, 15000)
