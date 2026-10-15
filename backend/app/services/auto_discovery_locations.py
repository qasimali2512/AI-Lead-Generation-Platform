"""
Auto-discovery ke liye locations ki list.

Har country ki list (state, city) ki hoti hai.  build_location_sequence()
countries ko ek ke baad ek mix karta hai (US, UK, Canada, ...) taake country,
state aur city teeno khud badalte rahein.
"""
from __future__ import annotations

from itertools import zip_longest

LOCATIONS_BY_COUNTRY: dict[str, list[tuple[str | None, str]]] = {
    "United States": [
        ("New York", "New York"), ("California", "Los Angeles"),
        ("Illinois", "Chicago"), ("Texas", "Houston"),
        ("Arizona", "Phoenix"), ("Pennsylvania", "Philadelphia"),
        ("Texas", "San Antonio"), ("California", "San Diego"),
        ("Texas", "Dallas"), ("Texas", "Austin"),
        ("Florida", "Jacksonville"), ("California", "San Jose"),
        ("Ohio", "Columbus"), ("North Carolina", "Charlotte"),
        ("Indiana", "Indianapolis"), ("California", "San Francisco"),
        ("Washington", "Seattle"), ("Colorado", "Denver"),
        ("District of Columbia", "Washington"), ("Massachusetts", "Boston"),
        ("Tennessee", "Nashville"), ("Nevada", "Las Vegas"),
        ("Oregon", "Portland"), ("Michigan", "Detroit"),
        ("Tennessee", "Memphis"), ("Kentucky", "Louisville"),
        ("Maryland", "Baltimore"), ("Wisconsin", "Milwaukee"),
        ("New Mexico", "Albuquerque"), ("Arizona", "Tucson"),
        ("California", "Fresno"), ("California", "Sacramento"),
        ("Georgia", "Atlanta"), ("Florida", "Miami"),
        ("Florida", "Orlando"), ("Florida", "Tampa"),
        ("Minnesota", "Minneapolis"), ("Ohio", "Cleveland"),
        ("Louisiana", "New Orleans"), ("Pennsylvania", "Pittsburgh"),
        ("Ohio", "Cincinnati"), ("Missouri", "Kansas City"),
        ("Missouri", "St. Louis"), ("North Carolina", "Raleigh"),
        ("Utah", "Salt Lake City"), ("Oklahoma", "Oklahoma City"),
        ("Nebraska", "Omaha"), ("Hawaii", "Honolulu"),
        ("Virginia", "Richmond"), ("Connecticut", "Hartford"),
    ],
    "United Kingdom": [
        ("England", "London"), ("England", "Manchester"),
        ("England", "Birmingham"), ("England", "Leeds"),
        ("Scotland", "Glasgow"), ("England", "Liverpool"),
        ("Scotland", "Edinburgh"), ("England", "Bristol"),
        ("England", "Sheffield"), ("England", "Newcastle upon Tyne"),
        ("England", "Nottingham"), ("England", "Leicester"),
        ("Wales", "Cardiff"), ("Northern Ireland", "Belfast"),
        ("England", "Southampton"), ("England", "Brighton"),
        ("England", "Oxford"), ("England", "Cambridge"),
        ("Scotland", "Aberdeen"), ("England", "York"),
    ],
    "Canada": [
        ("Ontario", "Toronto"), ("Quebec", "Montreal"),
        ("British Columbia", "Vancouver"), ("Alberta", "Calgary"),
        ("Alberta", "Edmonton"), ("Ontario", "Ottawa"),
        ("Manitoba", "Winnipeg"), ("Quebec", "Quebec City"),
        ("Ontario", "Hamilton"), ("Nova Scotia", "Halifax"),
        ("British Columbia", "Victoria"), ("Saskatchewan", "Saskatoon"),
        ("Saskatchewan", "Regina"), ("Ontario", "Mississauga"),
    ],
    "Australia": [
        ("New South Wales", "Sydney"), ("Victoria", "Melbourne"),
        ("Queensland", "Brisbane"), ("Western Australia", "Perth"),
        ("South Australia", "Adelaide"), ("Queensland", "Gold Coast"),
        ("Australian Capital Territory", "Canberra"),
        ("New South Wales", "Newcastle"), ("Tasmania", "Hobart"),
        ("Northern Territory", "Darwin"),
    ],
    "United Arab Emirates": [
        ("Dubai", "Dubai"), ("Abu Dhabi", "Abu Dhabi"),
        ("Sharjah", "Sharjah"), ("Ajman", "Ajman"),
        ("Ras Al Khaimah", "Ras Al Khaimah"),
    ],
    "New Zealand": [
        ("Auckland", "Auckland"), ("Wellington", "Wellington"),
        ("Canterbury", "Christchurch"),
    ],
    "Ireland": [
        ("Leinster", "Dublin"), ("Munster", "Cork"), ("Connacht", "Galway"),
    ],
}


def available_countries() -> list[str]:
    return list(LOCATIONS_BY_COUNTRY)


def build_location_sequence(
    countries: list[str] | None = None,
) -> list[tuple[str, str | None, str]]:
    """Returns [(country, state, city), ...] mixed country-by-country.

    Empty/None ``countries`` means all countries.
    """
    selected = [
        c for c in LOCATIONS_BY_COUNTRY if not countries or c in countries
    ]
    columns = [
        [(c, state, city) for state, city in LOCATIONS_BY_COUNTRY[c]]
        for c in selected
    ]
    sequence: list[tuple[str, str | None, str]] = []
    for row in zip_longest(*columns):
        for item in row:
            if item is not None:
                sequence.append(item)
    return sequence