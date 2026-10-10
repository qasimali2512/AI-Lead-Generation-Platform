from app.services.discovery import (
    build_overpass_query,
    escape_overpass_regex,
    get_industry_search_terms,
)


def test_steel_manufacturer_uses_industrial_and_keyword_searches():
    query = build_overpass_query(31.5204, 74.3587, "steel manufacturer")

    assert '["industrial"="steel"]["name"]' in query
    assert '["man_made"="works"]["name"]' in query
    assert '["name"~"steel",i]' in query
    assert '["industrial"~"steel",i]["name"]' in query


def test_precise_search_can_skip_expensive_keyword_clauses():
    query = build_overpass_query(
        40.7128,
        -74.0060,
        "steel manufacturers",
        include_keyword_search=False,
    )

    assert '["industrial"="steel"]["name"]' in query
    assert '["name"~"steel",i]' not in query


def test_unmapped_industry_is_searched_by_its_meaningful_keyword():
    query = build_overpass_query(31.5204, 74.3587, "solar panel installer")

    assert get_industry_search_terms("solar panel installer") == [
        "solar panel installer",
        "solar",
    ]
    assert '["name"~"solar",i]' in query
    assert '["product"~"solar",i]["name"]' in query


def test_keyword_search_escapes_overpass_regex_characters():
    # Two backslashes are required in the Overpass string literal so its regex
    # engine receives one literal escape character.
    assert escape_overpass_regex("steel+(alloy)") == "steel\\\\+\\\\(alloy\\\\)"
