"""
Search planning and localization helpers.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from app.core.config import settings
from app.core.country_config import detect_country, normalize_location, resolve_email_language


LOCATION_ALIASES: Dict[str, List[str]] = {
    "geneva": ["Geneva", "Geneve", "Geneve Suisse", "Geneva Switzerland"],
    "zurich": ["Zurich", "Zuerich", "Zurich Switzerland"],
    "lausanne": ["Lausanne", "Lausanne Suisse"],
    "new york": ["New York", "New York City", "NYC", "Manhattan", "Brooklyn", "Queens"],
    "los angeles": ["Los Angeles", "LA", "West Hollywood", "Santa Monica"],
    "miami": ["Miami", "Miami Beach", "Downtown Miami"],
    "dallas": ["Dallas", "Dallas TX", "Downtown Dallas"],
    "sydney": ["Sydney", "Sydney CBD", "Inner West Sydney"],
    "melbourne": ["Melbourne", "Melbourne CBD", "Inner Melbourne"],
    "brisbane": ["Brisbane", "Brisbane CBD"],
    "toulouse": ["Toulouse", "Centre Toulouse", "Toulouse centre"],
    "montpellier": ["Montpellier", "Centre Montpellier"],
    "marseille": ["Marseille", "Centre Marseille"],
    "paris": ["Paris", "Paris centre"],
}

GENERIC_FR_TERMS = ["site officiel", "contact", "entreprise locale", "artisan", "independant"]
GENERIC_EN_TERMS = ["official website", "contact", "local business", "independent", "small business"]

CATEGORY_TERMS: Dict[str, Dict[str, List[str]]] = {
    "plombier": {
        "fr": ["plombier", "entreprise plomberie", "depannage plomberie", "service plomberie", "artisan plombier"],
        "en": ["plumber", "plumbing company", "emergency plumber", "plumbing service", "local plumber"],
    },
    "coiffeur": {
        "fr": ["coiffeur", "salon de coiffure", "coiffure", "coiffeuse", "salon beaute"],
        "en": ["hair salon", "hairdresser", "hairstylist", "beauty salon", "independent salon"],
    },
    "salon de coiffure": {
        "fr": ["salon de coiffure", "coiffeur", "coiffure", "salon beaute"],
        "en": ["hair salon", "hairdresser", "beauty salon", "hairstylist"],
    },
    "institut de beaute": {
        "fr": ["institut de beaute", "salon beaute", "esthetique", "beaute", "spa beaute"],
        "en": ["beauty salon", "beauty studio", "beauty clinic", "skin care studio", "beauty institute"],
    },
    "spa": {
        "fr": ["spa", "centre bien etre", "institut de beaute", "massage spa", "centre wellness"],
        "en": ["spa", "wellness center", "beauty spa", "massage spa", "wellness studio"],
    },
    "restaurant": {
        "fr": ["restaurant", "bistrot", "brasserie", "restaurant local", "petit restaurant"],
        "en": ["restaurant", "local restaurant", "bistro", "brasserie", "independent restaurant"],
    },
    "dentiste": {
        "fr": ["dentiste", "cabinet dentaire", "chirurgien dentiste"],
        "en": ["dentist", "dental clinic", "family dentist", "cosmetic dentist"],
    },
    "electricien": {
        "fr": ["electricien", "entreprise electricite", "artisan electricien", "depannage electrique"],
        "en": ["electrician", "electrical contractor", "emergency electrician", "electrical service"],
    },
}

OSM_CATEGORY_TAGS: Dict[str, List[Dict[str, str]]] = {
    "plombier": [{"key": "craft", "value": "plumber"}],
    "coiffeur": [{"key": "shop", "value": "hairdresser"}],
    "salon de coiffure": [{"key": "shop", "value": "hairdresser"}],
    "institut de beaute": [{"key": "shop", "value": "beauty"}],
    "spa": [{"key": "leisure", "value": "spa"}, {"key": "amenity", "value": "spa"}],
    "restaurant": [{"key": "amenity", "value": "restaurant"}],
    "dentiste": [{"key": "amenity", "value": "dentist"}],
    "electricien": [{"key": "craft", "value": "electrician"}],
}

DIRECTORY_DOMAINS = {
    "bing.com",
    "duckduckgo.com",
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "yelp.com",
    "tripadvisor.com",
    "yellowpages.com",
    "pagesjaunes.fr",
    "mapquest.com",
    "angi.com",
    "trustpilot.com",
    "manta.com",
    "superpages.com",
}

COUNTRY_SEARCH_CONTEXT: Dict[str, Dict[str, str]] = {
    "FR": {"country_code": "fr", "bcp47": "fr-FR"},
    "CH": {"country_code": "ch", "bcp47": "fr-CH"},
    "US": {"country_code": "us", "bcp47": "en-US"},
    "AU": {"country_code": "au", "bcp47": "en-AU"},
    "GB": {"country_code": "gb", "bcp47": "en-GB"},
}


@dataclass
class SearchPlan:
    location: str
    normalized_location: str
    country: str
    language: str
    location_aliases: List[str]
    category_terms: List[str]
    queries: List[str]
    contact_queries: List[str]
    broadened_queries: List[str]
    generic_queries: List[str]
    osm_tags: List[Dict[str, str]]
    geocoder_country_code: str
    market_language_tag: str


def canonicalize_category(category: str) -> str:
    """Map variant labels to a canonical category key."""
    normalized = normalize_location(category)
    if "plomb" in normalized or "plumber" in normalized or "plumbing" in normalized:
        return "plombier"
    if "beaut" in normalized or "beaute" in normalized or "institut" in normalized:
        return "institut de beaute"
    if "coiff" in normalized or "hair" in normalized or "hairstyl" in normalized or "hairdresser" in normalized:
        return "coiffeur"
    if normalized == "salon de coiffure":
        return "salon de coiffure"
    if "salon" in normalized:
        return "coiffeur"
    if "spa" in normalized or "wellness" in normalized:
        return "spa"
    if "dent" in normalized:
        return "dentiste"
    if "elect" in normalized or "elec" in normalized:
        return "electricien"
    if "rest" in normalized or "bistro" in normalized or "brasserie" in normalized:
        return "restaurant"
    return normalized or category


def get_location_aliases(location: str) -> List[str]:
    """Return preferred aliases for a city."""
    normalized = normalize_location(location)
    aliases = LOCATION_ALIASES.get(normalized, [location])
    unique_aliases: List[str] = []
    for alias in [location] + aliases:
        if alias and alias not in unique_aliases:
            unique_aliases.append(alias)
    return unique_aliases


def get_category_terms(category: str, country: str, language: str) -> List[str]:
    """Return translated search terms for the category."""
    canonical = canonicalize_category(category)
    category_mapping = CATEGORY_TERMS.get(canonical)
    if category_mapping:
        if country == "CH":
            terms = _interleave_terms(category_mapping.get("fr", []), category_mapping.get("en", []))
        else:
            terms = category_mapping.get(language, []) or category_mapping.get("en", [])
        if terms:
            unique_terms: List[str] = []
            for term in terms:
                if term and term not in unique_terms:
                    unique_terms.append(term)
            return unique_terms
    return [category] if language == "fr" else [category]


def get_osm_tags(category: str) -> List[Dict[str, str]]:
    """Return OSM tags for a category."""
    return OSM_CATEGORY_TAGS.get(canonicalize_category(category), [])


def get_country_search_context(country: str, language: str) -> Dict[str, str]:
    """Return country-aware search context."""
    context = COUNTRY_SEARCH_CONTEXT.get(country, COUNTRY_SEARCH_CONTEXT["FR"]).copy()
    if country == "CH" and language == "en":
        context["bcp47"] = "en-CH"
    return context


def build_search_plan(location: str, category: str, fallback_language: str = "fr") -> SearchPlan:
    """Build a location and category aware search plan."""
    country = detect_country(location)
    language = resolve_email_language(location, country, fallback_language)
    location_aliases = get_location_aliases(location)
    category_terms = get_category_terms(category, country, language)
    country_context = get_country_search_context(country, language)

    queries = _build_queries(location_aliases, category_terms, language, settings.SEARCH_QUERIES_PER_COMBO)
    contact_queries = _build_contact_queries(location_aliases, category_terms, language)
    broadened_queries = _build_broadened_queries(location_aliases, category_terms, language)
    generic_queries = _build_generic_queries(location_aliases, language)

    return SearchPlan(
        location=location,
        normalized_location=normalize_location(location),
        country=country,
        language=language,
        location_aliases=location_aliases,
        category_terms=category_terms,
        queries=queries,
        contact_queries=contact_queries,
        broadened_queries=broadened_queries,
        generic_queries=generic_queries,
        osm_tags=get_osm_tags(category),
        geocoder_country_code=country_context["country_code"],
        market_language_tag=country_context["bcp47"],
    )


def should_skip_domain(domain: str) -> bool:
    """Filter obvious directory or social domains."""
    normalized = (domain or "").lower()
    return any(normalized.endswith(blocked) for blocked in DIRECTORY_DOMAINS)


def _build_queries(location_aliases: List[str], category_terms: List[str], language: str, max_queries: int) -> List[str]:
    query_patterns = [
        "{term} {location}",
        "{prefix_1} {term} {location}",
        "{term} {location} {suffix_1}",
        "{term} {location} {suffix_2}",
        "{prefix_2} {term} {location}",
    ]

    if language == "fr":
        replacements = {
            "prefix_1": "artisan",
            "prefix_2": "entreprise",
            "suffix_1": "site officiel",
            "suffix_2": "contact",
        }
    else:
        replacements = {
            "prefix_1": "local",
            "prefix_2": "independent",
            "suffix_1": "official website",
            "suffix_2": "contact",
        }

    queries: List[str] = []
    for location in location_aliases:
        for pattern in query_patterns:
            for term in category_terms:
                query = pattern.format(term=term, location=location, **replacements).strip()
                if query not in queries:
                    queries.append(query)
                if len(queries) >= max_queries:
                    return queries
    return queries


def _build_broadened_queries(location_aliases: List[str], category_terms: List[str], language: str) -> List[str]:
    generic_terms = GENERIC_FR_TERMS if language == "fr" else GENERIC_EN_TERMS
    queries: List[str] = []
    base_location = location_aliases[0]
    for term in category_terms[:3]:
        queries.append(f"{term} {base_location}")
        for generic in generic_terms[:3]:
            queries.append(f"{term} {base_location} {generic}")
    unique_queries: List[str] = []
    for query in queries:
        if query not in unique_queries:
            unique_queries.append(query)
    return unique_queries


def _build_contact_queries(location_aliases: List[str], category_terms: List[str], language: str) -> List[str]:
    """Build queries that bias search engines toward contact-rich business websites."""
    base_location = location_aliases[0]
    contact_terms = ["contact", "email", "telephone"] if language == "fr" else ["contact", "email", "phone"]
    website_terms = ["site officiel", "nous contacter"] if language == "fr" else ["official website", "contact us"]

    queries: List[str] = []
    for term in category_terms[:4]:
        queries.append(f"{term} {base_location} {contact_terms[0]}")
        queries.append(f"{term} {base_location} {contact_terms[1]}")
        queries.append(f"{term} {base_location} {contact_terms[2]}")
        queries.append(f"{term} {base_location} {website_terms[0]}")
        queries.append(f"{term} {base_location} {website_terms[1]}")

    unique_queries: List[str] = []
    for query in queries:
        if query not in unique_queries:
            unique_queries.append(query)
    return unique_queries


def _build_generic_queries(location_aliases: List[str], language: str) -> List[str]:
    base_location = location_aliases[0]
    if language == "fr":
        candidates = [
            f"entreprise {base_location} site web",
            f"commerce local {base_location} site officiel",
            f"business {base_location} website",
            f"{base_location} site officiel",
        ]
    else:
        candidates = [
            f"business {base_location} website",
            f"local business {base_location} official website",
            f"company {base_location} contact",
            f"{base_location} official website",
        ]

    queries: List[str] = []
    for query in candidates:
        if query not in queries:
            queries.append(query)
    return queries


def _interleave_terms(primary_terms: List[str], secondary_terms: List[str]) -> List[str]:
    """Alternate between local and fallback terms to keep early queries diverse."""
    interleaved: List[str] = []
    max_length = max(len(primary_terms), len(secondary_terms))
    for index in range(max_length):
        if index < len(primary_terms):
            interleaved.append(primary_terms[index])
        if index < len(secondary_terms):
            interleaved.append(secondary_terms[index])
    return interleaved
