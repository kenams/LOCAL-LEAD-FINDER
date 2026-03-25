"""
Tests for search configuration and query planning.
"""
from app.core.search_config import (
    build_search_plan,
    canonicalize_category,
    get_location_aliases,
    get_osm_tags,
    should_skip_domain,
)


def test_location_aliases():
    aliases = get_location_aliases("New York")
    assert "New York" in aliases
    assert "NYC" in aliases
    assert "Brooklyn" in aliases


def test_category_canonicalization():
    assert canonicalize_category("plumber") == "plombier"
    assert canonicalize_category("hair salon") == "coiffeur"
    assert canonicalize_category("beauty salon") == "institut de beaute"


def test_build_search_plan_us():
    plan = build_search_plan("New York", "plumber", "fr")
    assert plan.country == "US"
    assert plan.language == "en"
    assert any("plumber" in query.lower() for query in plan.queries)
    assert any("nyc" in alias.lower() for alias in plan.location_aliases)


def test_build_search_plan_ch():
    plan = build_search_plan("Geneva", "beauty salon", "en")
    assert plan.country == "CH"
    assert plan.language == "fr"
    assert any("institut" in term.lower() or "beaute" in term.lower() for term in plan.category_terms)
    assert any("beauty salon" in term.lower() for term in plan.category_terms)
    assert plan.geocoder_country_code == "ch"
    assert plan.osm_tags
    assert plan.generic_queries


def test_build_search_plan_ch_hair_includes_english_fallbacks():
    plan = build_search_plan("Geneva", "coiffeur", "fr")
    lowered_terms = [term.lower() for term in plan.category_terms]
    assert "coiffeur" in lowered_terms
    assert "hair salon" in lowered_terms
    assert "hairdresser" in lowered_terms
    lowered_queries = [query.lower() for query in plan.queries]
    assert any("hair salon geneva" in query or "hairdresser geneva" in query for query in lowered_queries)
    assert any("hair salon geneva" in query for query in [query.lower() for query in plan.broadened_queries])


def test_osm_tags_for_core_categories():
    assert get_osm_tags("plumber") == [{"key": "craft", "value": "plumber"}]
    assert get_osm_tags("hair salon") == [{"key": "shop", "value": "hairdresser"}]


def test_skip_directory_domains():
    assert should_skip_domain("www.yelp.com")
    assert should_skip_domain("pagesjaunes.fr")
    assert not should_skip_domain("my-local-salon.com")
