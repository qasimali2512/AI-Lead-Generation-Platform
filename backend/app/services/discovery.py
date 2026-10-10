from __future__ import annotations

import logging
import re
import urllib.parse
from typing import Any
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.schemas.discovery import (
    BusinessDiscoveryRequest,
    BusinessDiscoveryResponse,
    BusinessDiscoveryResult,
)
from app.services.leads import save_discovery_results


logger = logging.getLogger(__name__)


# =========================================================
# External services
# =========================================================

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

# Tried in order — first one that responds successfully wins.
# Order reflects current reliability — most reliable first.
OVERPASS_URLS = [
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

USER_AGENT = (
    "AI-Lead-Generation-Platform/1.0 "
    "(business discovery service)"
)

NOMINATIM_TIMEOUT = 20.0
OVERPASS_TIMEOUT  = 20.0   # per attempt; GET on mail.ru responds in ~12s


# =========================================================
# Industry → OpenStreetMap tags
#
# Keys are normalised (lowercase, single-space).
# Each value is a list of OSM filter strings appended to
# the area query, e.g.  '["amenity"="restaurant"]'.
# =========================================================

INDUSTRY_TAGS: dict[str, list[str]] = {

    # ── Food & Drink ──────────────────────────────────────
    "restaurant": [
        '["amenity"="restaurant"]',
        '["amenity"="fast_food"]',
    ],
    "restaurants": [
        '["amenity"="restaurant"]',
        '["amenity"="fast_food"]',
    ],
    "fast food": [
        '["amenity"="fast_food"]',
    ],
    "cafe": [
        '["amenity"="cafe"]',
    ],
    "coffee shop": [
        '["amenity"="cafe"]',
    ],
    "coffee": [
        '["amenity"="cafe"]',
    ],
    "bakery": [
        '["shop"="bakery"]',
        '["amenity"="cafe"]',
    ],
    "bar": [
        '["amenity"="bar"]',
        '["amenity"="pub"]',
    ],
    "pub": [
        '["amenity"="pub"]',
        '["amenity"="bar"]',
    ],
    "pizza": [
        '["amenity"="restaurant"]["cuisine"="pizza"]',
        '["amenity"="fast_food"]["cuisine"="pizza"]',
    ],
    "food": [
        '["amenity"="restaurant"]',
        '["amenity"="fast_food"]',
        '["amenity"="cafe"]',
    ],
    "catering": [
        '["amenity"="restaurant"]',
        '["office"="company"]["name"]',
    ],

    # ── Health & Medical ──────────────────────────────────
    "dental clinic": [
        '["amenity"="dentist"]',
        '["amenity"="clinic"]',
    ],
    "dental clinics": [
        '["amenity"="dentist"]',
        '["amenity"="clinic"]',
    ],
    "dentist": [
        '["amenity"="dentist"]',
    ],
    "dentists": [
        '["amenity"="dentist"]',
    ],
    "dental": [
        '["amenity"="dentist"]',
    ],
    "clinic": [
        '["amenity"="clinic"]',
        '["amenity"="doctors"]',
    ],
    "clinics": [
        '["amenity"="clinic"]',
        '["amenity"="doctors"]',
    ],
    "medical clinic": [
        '["amenity"="clinic"]',
        '["amenity"="doctors"]',
    ],
    "doctor": [
        '["amenity"="doctors"]',
        '["amenity"="clinic"]',
    ],
    "doctors": [
        '["amenity"="doctors"]',
        '["amenity"="clinic"]',
    ],
    "hospital": [
        '["amenity"="hospital"]',
    ],
    "hospitals": [
        '["amenity"="hospital"]',
    ],
    "pharmacy": [
        '["amenity"="pharmacy"]',
    ],
    "pharmacies": [
        '["amenity"="pharmacy"]',
    ],
    "drug store": [
        '["amenity"="pharmacy"]',
    ],
    "optician": [
        '["shop"="optician"]',
    ],
    "optometrist": [
        '["shop"="optician"]',
    ],
    "eye care": [
        '["shop"="optician"]',
    ],
    "chiropractor": [
        '["amenity"="clinic"]',
        '["healthcare"="physiotherapist"]',
    ],
    "chiropractic": [
        '["amenity"="clinic"]',
        '["healthcare"="physiotherapist"]',
    ],
    "physiotherapy": [
        '["healthcare"="physiotherapist"]',
        '["amenity"="clinic"]',
    ],
    "physical therapy": [
        '["healthcare"="physiotherapist"]',
        '["amenity"="clinic"]',
    ],
    "veterinarian": [
        '["amenity"="veterinary"]',
    ],
    "veterinary": [
        '["amenity"="veterinary"]',
    ],
    "vet": [
        '["amenity"="veterinary"]',
    ],
    "mental health": [
        '["amenity"="clinic"]',
        '["healthcare"="psychotherapist"]',
    ],
    "therapist": [
        '["healthcare"="psychotherapist"]',
        '["amenity"="clinic"]',
    ],
    "healthcare": [
        '["amenity"="clinic"]',
        '["amenity"="doctors"]',
        '["amenity"="hospital"]',
    ],

    # ── Fitness & Wellness ────────────────────────────────
    "gym": [
        '["leisure"="fitness_centre"]',
        '["sport"="fitness"]',
    ],
    "fitness": [
        '["leisure"="fitness_centre"]',
        '["sport"="fitness"]',
    ],
    "fitness center": [
        '["leisure"="fitness_centre"]',
    ],
    "yoga": [
        '["leisure"="fitness_centre"]["sport"="yoga"]',
        '["leisure"="fitness_centre"]',
    ],
    "pilates": [
        '["leisure"="fitness_centre"]',
    ],
    "spa": [
        '["leisure"="spa"]',
        '["shop"="beauty"]',
    ],
    "wellness": [
        '["leisure"="spa"]',
        '["leisure"="fitness_centre"]',
        '["shop"="beauty"]',
    ],
    "massage": [
        '["leisure"="spa"]',
        '["shop"="massage"]',
    ],
    "swimming pool": [
        '["leisure"="swimming_pool"]',
        '["sport"="swimming"]',
    ],
    "sports": [
        '["leisure"="sports_centre"]',
        '["leisure"="fitness_centre"]',
    ],
    "martial arts": [
        '["leisure"="fitness_centre"]',
        '["sport"="martial_arts"]',
    ],
    "dance": [
        '["leisure"="fitness_centre"]["sport"="dance"]',
        '["leisure"="fitness_centre"]',
    ],

    # ── Beauty & Personal Care ────────────────────────────
    "salon": [
        '["shop"="hairdresser"]',
        '["shop"="beauty"]',
    ],
    "hair salon": [
        '["shop"="hairdresser"]',
    ],
    "beauty salon": [
        '["shop"="beauty"]',
        '["shop"="hairdresser"]',
    ],
    "barber": [
        '["shop"="hairdresser"]',
        '["shop"="barber"]',
    ],
    "barber shop": [
        '["shop"="barber"]',
        '["shop"="hairdresser"]',
    ],
    "nail salon": [
        '["shop"="beauty"]',
        '["shop"="nail_salon"]',
    ],
    "nails": [
        '["shop"="beauty"]',
        '["shop"="nail_salon"]',
    ],
    "tattoo": [
        '["shop"="tattoo"]',
    ],
    "beauty": [
        '["shop"="beauty"]',
        '["shop"="hairdresser"]',
        '["shop"="cosmetics"]',
    ],
    "cosmetics": [
        '["shop"="cosmetics"]',
        '["shop"="beauty"]',
    ],

    # ── Accommodation ─────────────────────────────────────
    "hotel": [
        '["tourism"="hotel"]',
        '["tourism"="motel"]',
    ],
    "hotels": [
        '["tourism"="hotel"]',
        '["tourism"="motel"]',
    ],
    "motel": [
        '["tourism"="motel"]',
    ],
    "guest house": [
        '["tourism"="guest_house"]',
    ],
    "hostel": [
        '["tourism"="hostel"]',
    ],
    "bed and breakfast": [
        '["tourism"="bed_and_breakfast"]',
    ],
    "resort": [
        '["tourism"="resort"]',
        '["tourism"="hotel"]',
    ],
    "airbnb": [
        '["tourism"="apartment"]',
        '["tourism"="guest_house"]',
    ],
    "accommodation": [
        '["tourism"="hotel"]',
        '["tourism"="motel"]',
        '["tourism"="guest_house"]',
        '["tourism"="hostel"]',
    ],

    # ── Professional Services ─────────────────────────────
    "law firm": [
        '["office"="lawyer"]',
    ],
    "lawyer": [
        '["office"="lawyer"]',
    ],
    "lawyers": [
        '["office"="lawyer"]',
    ],
    "attorney": [
        '["office"="lawyer"]',
    ],
    "legal": [
        '["office"="lawyer"]',
        '["office"="notary"]',
    ],
    "accounting": [
        '["office"="accountant"]',
    ],
    "accountant": [
        '["office"="accountant"]',
    ],
    "accountants": [
        '["office"="accountant"]',
    ],
    "tax": [
        '["office"="tax_advisor"]',
        '["office"="accountant"]',
    ],
    "tax advisor": [
        '["office"="tax_advisor"]',
    ],
    "cpa": [
        '["office"="accountant"]',
    ],
    "financial advisor": [
        '["office"="financial"]',
        '["office"="financial_services"]',
    ],
    "financial services": [
        '["office"="financial_services"]',
        '["office"="financial"]',
    ],
    "insurance": [
        '["office"="insurance"]',
    ],
    "architect": [
        '["office"="architect"]',
    ],
    "architecture": [
        '["office"="architect"]',
    ],
    "consulting": [
        '["office"="consulting"]',
        '["office"="company"]',
    ],
    "consultant": [
        '["office"="consulting"]',
        '["office"="company"]',
    ],
    "marketing": [
        '["office"="advertising_agency"]',
        '["office"="company"]',
    ],
    "advertising": [
        '["office"="advertising_agency"]',
    ],
    "notary": [
        '["office"="notary"]',
    ],
    "recruitment": [
        '["office"="employment_agency"]',
    ],
    "hr": [
        '["office"="employment_agency"]',
    ],
    "staffing": [
        '["office"="employment_agency"]',
    ],

    # ── Real Estate ───────────────────────────────────────
    "real estate": [
        '["office"="estate_agent"]',
    ],
    "real estate agency": [
        '["office"="estate_agent"]',
    ],
    "estate agent": [
        '["office"="estate_agent"]',
    ],
    "property management": [
        '["office"="estate_agent"]',
        '["office"="company"]',
    ],

    # ── Automotive ────────────────────────────────────────
    "auto repair": [
        '["shop"="car_repair"]',
    ],
    "car repair": [
        '["shop"="car_repair"]',
    ],
    "mechanic": [
        '["shop"="car_repair"]',
    ],
    "car wash": [
        '["amenity"="car_wash"]',
    ],
    "car dealer": [
        '["shop"="car"]',
    ],
    "auto parts": [
        '["shop"="car_parts"]',
    ],
    "tires": [
        '["shop"="tyres"]',
    ],
    "tyres": [
        '["shop"="tyres"]',
    ],
    "gas station": [
        '["amenity"="fuel"]',
    ],
    "petrol station": [
        '["amenity"="fuel"]',
    ],
    "fuel": [
        '["amenity"="fuel"]',
    ],
    "parking": [
        '["amenity"="parking"]',
    ],

    # ── Construction & Trades ─────────────────────────────
    "construction": [
        '["craft"="builder"]',
        '["office"="company"]',
    ],
    "contractor": [
        '["craft"="builder"]',
    ],
    "builder": [
        '["craft"="builder"]',
    ],
    "plumber": [
        '["craft"="plumber"]',
    ],
    "plumbing": [
        '["craft"="plumber"]',
    ],
    "electrician": [
        '["craft"="electrician"]',
    ],
    "electrical": [
        '["craft"="electrician"]',
    ],
    "hvac": [
        '["craft"="hvac"]',
        '["craft"="builder"]',
    ],
    "roofing": [
        '["craft"="roofer"]',
    ],
    "roofer": [
        '["craft"="roofer"]',
    ],
    "painting": [
        '["craft"="painter"]',
    ],
    "painter": [
        '["craft"="painter"]',
    ],
    "carpentry": [
        '["craft"="carpenter"]',
    ],
    "carpenter": [
        '["craft"="carpenter"]',
    ],
    "landscaping": [
        '["craft"="gardener"]',
        '["shop"="garden_centre"]',
    ],
    "landscaper": [
        '["craft"="gardener"]',
    ],
    "gardener": [
        '["craft"="gardener"]',
    ],
    "cleaning": [
        '["craft"="cleaning"]',
        '["office"="company"]',
    ],
    "pest control": [
        '["craft"="pest_control"]',
    ],
    "interior design": [
        '["office"="architect"]',
        '["shop"="interior_decoration"]',
    ],

    # ── Retail ────────────────────────────────────────────
    "supermarket": [
        '["shop"="supermarket"]',
    ],
    "grocery": [
        '["shop"="convenience"]',
        '["shop"="supermarket"]',
    ],
    "convenience store": [
        '["shop"="convenience"]',
    ],
    "clothing": [
        '["shop"="clothes"]',
    ],
    "clothes": [
        '["shop"="clothes"]',
    ],
    "fashion": [
        '["shop"="clothes"]',
        '["shop"="fashion_accessories"]',
    ],
    "shoes": [
        '["shop"="shoes"]',
    ],
    "footwear": [
        '["shop"="shoes"]',
    ],
    "furniture": [
        '["shop"="furniture"]',
    ],
    "electronics": [
        '["shop"="electronics"]',
    ],
    "computer": [
        '["shop"="computer"]',
    ],
    "mobile phone": [
        '["shop"="mobile_phone"]',
    ],
    "phone repair": [
        '["shop"="mobile_phone"]',
        '["shop"="electronics_repair"]',
    ],
    "hardware": [
        '["shop"="hardware"]',
        '["shop"="doityourself"]',
    ],
    "bookstore": [
        '["shop"="books"]',
    ],
    "books": [
        '["shop"="books"]',
    ],
    "toy store": [
        '["shop"="toys"]',
    ],
    "toys": [
        '["shop"="toys"]',
    ],
    "sports store": [
        '["shop"="sports"]',
    ],
    "jewellery": [
        '["shop"="jewelry"]',
    ],
    "jewelry": [
        '["shop"="jewelry"]',
    ],
    "florist": [
        '["shop"="florist"]',
    ],
    "flowers": [
        '["shop"="florist"]',
    ],
    "pet store": [
        '["shop"="pet"]',
    ],
    "pets": [
        '["shop"="pet"]',
        '["amenity"="veterinary"]',
    ],
    "gift shop": [
        '["shop"="gift"]',
    ],
    "pharmacy": [
        '["amenity"="pharmacy"]',
    ],
    "wine": [
        '["shop"="wine"]',
        '["shop"="alcohol"]',
    ],
    "alcohol": [
        '["shop"="alcohol"]',
    ],
    "optician": [
        '["shop"="optician"]',
    ],

    # ── Finance & Banking ─────────────────────────────────
    "bank": [
        '["amenity"="bank"]',
    ],
    "banks": [
        '["amenity"="bank"]',
    ],
    "atm": [
        '["amenity"="atm"]',
    ],
    "credit union": [
        '["amenity"="bank"]',
    ],
    "mortgage": [
        '["office"="financial"]',
    ],
    "money transfer": [
        '["amenity"="bureau_de_change"]',
    ],
    "bureau de change": [
        '["amenity"="bureau_de_change"]',
    ],

    # ── Education ─────────────────────────────────────────
    "school": [
        '["amenity"="school"]',
    ],
    "schools": [
        '["amenity"="school"]',
    ],
    "university": [
        '["amenity"="university"]',
    ],
    "college": [
        '["amenity"="college"]',
        '["amenity"="university"]',
    ],
    "kindergarten": [
        '["amenity"="kindergarten"]',
    ],
    "day care": [
        '["amenity"="childcare"]',
        '["amenity"="kindergarten"]',
    ],
    "nursery": [
        '["amenity"="kindergarten"]',
        '["amenity"="childcare"]',
    ],
    "tutoring": [
        '["amenity"="school"]',
        '["office"="educational_institution"]',
    ],
    "driving school": [
        '["amenity"="driving_school"]',
    ],
    "music school": [
        '["amenity"="music_school"]',
    ],
    "language school": [
        '["amenity"="language_school"]',
    ],

    # ── Technology & IT ───────────────────────────────────
    "it company": [
        '["office"="company"]',
        '["office"="it"]',
    ],
    "software": [
        '["office"="company"]',
        '["office"="it"]',
    ],
    "web design": [
        '["office"="company"]',
    ],
    "digital agency": [
        '["office"="advertising_agency"]',
        '["office"="company"]',
    ],
    "tech": [
        '["office"="company"]',
        '["office"="it"]',
    ],
    "computer repair": [
        '["shop"="computer"]',
        '["shop"="electronics_repair"]',
    ],

    # ── Logistics & Transport ─────────────────────────────
    "logistics": [
        '["office"="logistics"]',
        '["office"="company"]',
    ],
    "shipping": [
        '["amenity"="post_office"]',
        '["office"="logistics"]',
    ],
    "courier": [
        '["amenity"="post_office"]',
    ],
    "taxi": [
        '["amenity"="taxi"]',
    ],
    "car rental": [
        '["amenity"="car_rental"]',
    ],
    "trucking": [
        '["office"="logistics"]',
    ],
    "warehouse": [
        '["building"="warehouse"]',
        '["landuse"="industrial"]',
    ],
    "shipping company": [
        '["office"="logistics"]',
        '["office"="company"]',
    ],
    "freight forwarding": [
        '["office"="logistics"]',
    ],
    "freight forwarder": [
        '["office"="logistics"]',
    ],

    # Manufacturing & industrial businesses.  These are often mapped with
    # `industrial` or `man_made=works`, rather than shop/office tags.
    "manufacturer": [
        '["industrial"]["name"]',
        '["man_made"="works"]["name"]',
    ],
    "manufacturing": [
        '["industrial"]["name"]',
        '["man_made"="works"]["name"]',
    ],
    "steel manufacturer": [
        '["industrial"="steel"]["name"]',
        '["man_made"="works"]["name"]',
        '["craft"="blacksmith"]["name"]',
    ],
    "steel manufacturing": [
        '["industrial"="steel"]["name"]',
        '["man_made"="works"]["name"]',
    ],
    "steel": [
        '["industrial"="steel"]["name"]',
        '["man_made"="works"]["name"]',
    ],
    "metal fabricator": [
        '["industrial"="metal_processing"]["name"]',
        '["craft"="metal_construction"]["name"]',
        '["man_made"="works"]["name"]',
    ],
    "metal fabrication": [
        '["industrial"="metal_processing"]["name"]',
        '["craft"="metal_construction"]["name"]',
        '["man_made"="works"]["name"]',
    ],

    # ── Entertainment & Leisure ───────────────────────────
    "cinema": [
        '["amenity"="cinema"]',
    ],
    "movie theater": [
        '["amenity"="cinema"]',
    ],
    "theatre": [
        '["amenity"="theatre"]',
    ],
    "theater": [
        '["amenity"="theatre"]',
    ],
    "bowling": [
        '["leisure"="bowling_alley"]',
    ],
    "arcade": [
        '["leisure"="amusement_arcade"]',
    ],
    "museum": [
        '["tourism"="museum"]',
    ],
    "art gallery": [
        '["tourism"="gallery"]',
    ],
    "photography": [
        '["shop"="photo"]',
        '["office"="company"]',
    ],
    "event venue": [
        '["amenity"="events_venue"]',
        '["amenity"="community_centre"]',
    ],
    "catering hall": [
        '["amenity"="events_venue"]',
    ],
    "wedding": [
        '["amenity"="events_venue"]',
    ],
    "printing": [
        '["shop"="copyshop"]',
        '["craft"="printer"]',
    ],
    "laundry": [
        '["shop"="laundry"]',
        '["shop"="dry_cleaning"]',
    ],
    "dry cleaning": [
        '["shop"="dry_cleaning"]',
    ],
    "travel agency": [
        '["shop"="travel_agency"]',
    ],
    "travel": [
        '["shop"="travel_agency"]',
    ],
    "garden centre": [
        '["shop"="garden_centre"]',
    ],
    "nursery plant": [
        '["shop"="garden_centre"]',
    ],
    "post office": [
        '["amenity"="post_office"]',
    ],
    "storage": [
        '["shop"="storage_rental"]',
    ],
    "security": [
        '["office"="company"]',
    ],
}


# =========================================================
# Industry helpers
# =========================================================

def normalize_industry(industry: str) -> str:
    return re.sub(r"\s+", " ", industry.strip().lower())


def get_industry_tags(industry: str) -> list[str]:
    normalized = normalize_industry(industry)

    # 1. Exact match
    if normalized in INDUSTRY_TAGS:
        return INDUSTRY_TAGS[normalized]

    # 2. Partial substring match (longest key wins to be more specific)
    matches = [
        (key, tags)
        for key, tags in INDUSTRY_TAGS.items()
        if key in normalized or normalized in key
    ]
    if matches:
        # Pick the longest matching key for best specificity
        best_key, best_tags = max(matches, key=lambda x: len(x[0]))
        logger.info(
            "Industry %r matched via partial key %r",
            normalized,
            best_key,
        )
        return best_tags

    # 3. Word-level overlap — find keys sharing words
    input_words = set(normalized.split())
    word_matches = []
    for key, tags in INDUSTRY_TAGS.items():
        key_words = set(key.split())
        overlap = len(input_words & key_words)
        if overlap > 0:
            word_matches.append((overlap, len(key), key, tags))
    if word_matches:
        word_matches.sort(key=lambda x: (-x[0], -x[1]))
        best = word_matches[0]
        logger.info(
            "Industry %r matched via word overlap key %r",
            normalized,
            best[2],
        )
        return best[3]

    # 4. Last-resort broad fallback — search anything with a name in
    #    common categories; filters keep result count manageable
    logger.warning(
        "Industry %r has no tag mapping — using broad fallback",
        normalized,
    )
    return []


_SEARCH_STOP_WORDS = frozenset({
    "and", "business", "businesses", "company", "companies", "factory",
    "firm", "group", "industry", "industries", "manufacturer",
    "manufacturers", "manufacturing", "service", "services", "the",
})


def get_industry_search_terms(industry: str) -> list[str]:
    """Return safe, meaningful terms for an OSM name/industry keyword search.

    OSM does not have one universal tag for every industry.  A company may be
    tagged only by its name (for example, ``ABC Steel``), so the selected
    industry must also be searched as a keyword, not just looked up in the
    static tag map.
    """
    normalized = normalize_industry(industry)
    words = re.findall(r"[a-z0-9]+", normalized)
    meaningful_words = [word for word in words if word not in _SEARCH_STOP_WORDS]

    terms: list[str] = []
    # Keep a useful multi-word phrase, then its most descriptive individual
    # words.  Two terms prevents an overly broad/slow Overpass request.
    phrase = " ".join(meaningful_words)
    if len(meaningful_words) > 1:
        terms.append(phrase)
    terms.extend(meaningful_words)

    unique_terms: list[str] = []
    for term in terms:
        if len(term) >= 3 and term not in unique_terms:
            unique_terms.append(term)
        if len(unique_terms) == 2:
            break
    return unique_terms


def escape_overpass_regex(value: str) -> str:
    """Escape user input before placing it in an Overpass regular expression."""
    return re.sub(r'([\\\\.^$*+?{}\[\]|()])', r"\\\\\1", value)


# =========================================================
# Generic value helpers
# =========================================================

def clean_value(value: Any) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value if value else None


def normalize_website(value: str | None) -> str | None:
    value = clean_value(value)
    if not value:
        return None
    if value.startswith("www."):
        return f"https://{value}"
    if not value.startswith(("http://", "https://")):
        return f"https://{value}"
    return value


def get_coordinates(
    element: dict[str, Any],
) -> tuple[float | None, float | None]:
    if element.get("type") == "node":
        lat = element.get("lat")
        lon = element.get("lon")
    else:
        center = element.get("center") or {}
        lat = element.get("lat") or center.get("lat")
        lon = element.get("lon") or center.get("lon")
    try:
        return (
            float(lat) if lat is not None else None,
            float(lon) if lon is not None else None,
        )
    except (TypeError, ValueError):
        return None, None


def build_address(tags: dict[str, Any]) -> str | None:
    parts: list[str] = []
    for key in ("addr:housenumber", "addr:street",
                "addr:neighbourhood", "addr:suburb",
                "addr:postcode"):
        v = clean_value(tags.get(key))
        if v:
            parts.append(v)
    return ", ".join(parts) if parts else None


def get_website(tags: dict[str, Any]) -> str | None:
    return normalize_website(
        tags.get("website")
        or tags.get("contact:website")
        or tags.get("url")
    )


def get_phone(tags: dict[str, Any]) -> str | None:
    return clean_value(
        tags.get("phone")
        or tags.get("contact:phone")
        or tags.get("phone:mobile")
    )


def get_email(tags: dict[str, Any]) -> str | None:
    return clean_value(
        tags.get("email")
        or tags.get("contact:email")
    )


# =========================================================
# Nominatim geocoding
# =========================================================

async def geocode_city(
    country: str,
    state: str | None,
    city: str,
) -> dict[str, Any]:
    """
    Resolve city + country to coordinates via Nominatim.
    Works for ANY country in the world.
    """
    # Build multiple query variants so we try the most
    # specific first, then fall back to broader searches
    queries: list[str] = []

    if state:
        queries.append(f"{city}, {state}, {country}")
    queries.append(f"{city}, {country}")
    queries.append(city)   # bare city name as last resort

    headers = {"User-Agent": USER_AGENT}
    last_exc: Exception | None = None

    for query in queries:
        params = {
            "q": query,
            "format": "jsonv2",
            "limit": 1,
            "addressdetails": 1,
        }
        try:
            async with httpx.AsyncClient(
                timeout=NOMINATIM_TIMEOUT,
                headers=headers,
            ) as client:
                response = await client.get(NOMINATIM_URL, params=params)
                response.raise_for_status()
                results = response.json()

        except httpx.TimeoutException as exc:
            last_exc = exc
            logger.warning("Nominatim timeout for query=%r", query)
            continue

        except (httpx.HTTPStatusError, httpx.HTTPError) as exc:
            last_exc = exc
            logger.warning("Nominatim error for query=%r: %s", query, exc)
            continue

        except ValueError as exc:
            last_exc = exc
            logger.warning("Nominatim bad JSON for query=%r", query)
            continue

        if not results:
            logger.info("Nominatim no results for query=%r, trying next", query)
            continue

        result = results[0]

        try:
            latitude  = float(result["lat"])
            longitude = float(result["lon"])
        except (KeyError, TypeError, ValueError) as exc:
            last_exc = exc
            continue

        address = result.get("address") or {}

        return {
            "query":        query,
            "display_name": result.get("display_name"),
            "latitude":     latitude,
            "longitude":    longitude,
            "country":      address.get("country"),
            "state":        address.get("state"),
            "city": (
                address.get("city")
                or address.get("town")
                or address.get("municipality")
                or address.get("village")
                or address.get("county")
            ),
        }

    # All attempts failed
    if last_exc and isinstance(last_exc, httpx.TimeoutException):
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Location lookup timed out. Please try again.",
        ) from last_exc

    if last_exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Location service is temporarily unavailable.",
        ) from last_exc

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=(
            f"Location not found: {city}"
            + (f", {state}" if state else "")
            + f", {country}. "
            "Check spelling or try a larger nearby city."
        ),
    )


# =========================================================
# Overpass query builder
# =========================================================

def build_overpass_query(
    latitude: float,
    longitude: float,
    industry: str,
    radius: int = 15000,
    max_elements: int = 2000,
    include_tag_search: bool = True,
    include_keyword_search: bool = True,
) -> str:
    tags = get_industry_tags(industry)
    search_terms = get_industry_search_terms(industry)

    statements: list[str] = []
    if include_tag_search:
        for tag in dict.fromkeys(tags):
            for osm_type in ("node", "way", "relation"):
                statements.append(
                    f'{osm_type}(around:{radius},{latitude},{longitude}){tag};'
                )

    # Tag mappings cover common sectors, while this keyword search covers any
    # business type a user enters.  It is intentionally additive: a shipping
    # company can be found via office=logistics even if its name is "DHL", and
    # an unmapped company such as "ABC Steel" can be found via its name.
    for term in search_terms if include_keyword_search else []:
        escaped_term = escape_overpass_regex(term)
        for osm_type in ("node", "way", "relation"):
            statements.append(
                f'{osm_type}(around:{radius},{latitude},{longitude})'
                f'["name"~"{escaped_term}",i];'
            )
            statements.append(
                f'{osm_type}(around:{radius},{latitude},{longitude})'
                f'["industrial"~"{escaped_term}",i]["name"];'
            )
            statements.append(
                f'{osm_type}(around:{radius},{latitude},{longitude})'
                f'["product"~"{escaped_term}",i]["name"];'
            )

    joined = "\n".join(statements)

    return (
        f"[out:json][timeout:25][maxsize:32000000];\n"
        f"(\n{joined}\n);\n"
        f"out center tags {max_elements};\n"
    )


# =========================================================
# Business normalization
# =========================================================

def normalize_business(
    element: dict[str, Any],
    industry: str,
) -> BusinessDiscoveryResult | None:
    tags = element.get("tags") or {}

    name = clean_value(tags.get("name"))
    if not name:
        return None

    # Skip businesses with generic/blank names
    if name.lower() in {"yes", "no", "true", "false", "-"}:
        return None

    latitude, longitude = get_coordinates(element)

    website = get_website(tags)
    source_type = element.get("type")
    osm_id = element.get("id")

    return BusinessDiscoveryResult(
        source_id=f"osm:{source_type}:{osm_id}",
        source="openstreetmap",
        name=name,
        industry=industry,
        address=build_address(tags),
        city=clean_value(
            tags.get("addr:city")
            or tags.get("addr:town")
            or tags.get("addr:village")
        ),
        state=clean_value(tags.get("addr:state")),
        country=clean_value(tags.get("addr:country")),
        latitude=latitude,
        longitude=longitude,
        phone=get_phone(tags),
        email=get_email(tags),
        website=website,
        website_status="has_website" if website else "no_website",
        osm_type=source_type,
        osm_id=osm_id,
    )


# =========================================================
# Overpass HTTP request — POST first, GET fallback
# =========================================================

async def fetch_overpass_data(query: str) -> dict[str, Any]:
    post_headers = {
        "User-Agent": USER_AGENT,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    get_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, */*",
    }

    last_error: Exception | None = None

    for idx, endpoint in enumerate(OVERPASS_URLS, start=1):
        # GET first (currently more reliable), POST as fallback
        for method, hdrs in [("GET", get_headers), ("POST", post_headers)]:
            try:
                logger.info(
                    "Overpass %s %d/%d: %s",
                    method, idx, len(OVERPASS_URLS), endpoint,
                )

                async with httpx.AsyncClient(
                    timeout=OVERPASS_TIMEOUT,
                    headers=hdrs,
                ) as client:
                    if method == "POST":
                        response = await client.post(
                            endpoint,
                            data={"data": query},
                        )
                    else:
                        encoded = urllib.parse.urlencode({"data": query})
                        response = await client.get(f"{endpoint}?{encoded}")

                logger.info(
                    "Overpass %s %s → HTTP %s",
                    method, endpoint, response.status_code,
                )

                response.raise_for_status()
                data = response.json()

                if not isinstance(data, dict):
                    raise ValueError("Overpass returned unexpected response type.")

                return data

            except httpx.TimeoutException as exc:
                last_error = exc
                logger.warning("Overpass timeout: %s %s", method, endpoint)

            except httpx.HTTPStatusError as exc:
                last_error = exc
                logger.warning(
                    "Overpass HTTP %s: %s %s",
                    exc.response.status_code, method, endpoint,
                )

            except httpx.HTTPError as exc:
                last_error = exc
                logger.warning("Overpass connection error: %s %s — %s", method, endpoint, exc)

            except ValueError as exc:
                last_error = exc
                logger.warning("Overpass bad JSON: %s %s", method, endpoint)

            except Exception as exc:
                last_error = exc
                logger.exception("Overpass unexpected error: %s %s", method, endpoint)

    logger.error("All Overpass endpoints failed: %s", last_error)

    if isinstance(last_error, httpx.TimeoutException):
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=(
                "Business discovery timed out. "
                "Overpass servers are overloaded — please try again in a moment."
            ),
        ) from last_error

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=(
            "Business discovery services are temporarily unavailable. "
            "Please try again in a moment."
        ),
    ) from last_error


# =========================================================
# Main entry point
# =========================================================

async def discover_businesses(
    payload: BusinessDiscoveryRequest,
    db: Session,
    user_id: UUID,
) -> BusinessDiscoveryResponse:

    normalized_industry = normalize_industry(payload.industry)

    # Step 1: Geocode
    location = await geocode_city(
        country=payload.country,
        state=payload.state,
        city=payload.city,
    )

    # Step 2: Build Overpass query
    # A qualified-only search has to inspect more candidates before applying
    # its limit.  In particular, an email-only search must never stop after
    # the first N businesses and then return a mostly unqualified list.
    qualification_multiplier = 10 if "has_email" in payload.filters else 4
    raw_limit = min(payload.limit * qualification_multiplier, 5000)
    mapped_tags = get_industry_tags(normalized_industry)
    elements: list[Any] = []

    # Start with precise industry tags. This keeps large-city searches fast.
    if mapped_tags:
        query = build_overpass_query(
            latitude=location["latitude"],
            longitude=location["longitude"],
            industry=normalized_industry,
            radius=15000,
            max_elements=raw_limit,
            include_keyword_search=False,
        )
        data = await fetch_overpass_data(query)
        response_elements = data.get("elements") or []
        if isinstance(response_elements, list):
            elements = response_elements

    # There is no universal OSM tag for every business type. If the precise
    # search has no named result, retry using the typed industry as a keyword.
    has_named_business = any(
        isinstance(element, dict)
        and clean_value((element.get("tags") or {}).get("name"))
        for element in elements
    )
    if not has_named_business:
        query = build_overpass_query(
            latitude=location["latitude"],
            longitude=location["longitude"],
            industry=normalized_industry,
            radius=10000,
            max_elements=raw_limit,
            include_tag_search=False,
        )
        data = await fetch_overpass_data(query)
        response_elements = data.get("elements") or []
        elements = response_elements if isinstance(response_elements, list) else []

    # Step 4: Normalize + deduplicate
    businesses: list[BusinessDiscoveryResult] = []
    seen_ids:   set[str] = set()
    seen_names: set[str] = set()

    for element in elements:
        if not isinstance(element, dict):
            continue

        business = normalize_business(
            element=element,
            industry=normalized_industry,
        )
        if business is None:
            continue

        if business.source_id in seen_ids:
            continue

        dedup_key = (
            f"{business.name.lower().strip()}|"
            f"{(business.address or '').lower()}"
        )
        if dedup_key in seen_names:
            continue

        seen_ids.add(business.source_id)
        seen_names.add(dedup_key)
        businesses.append(business)

    candidates_scanned = len(businesses)

    if "has_website" in payload.filters:
        businesses = [business for business in businesses if business.website]

    if "has_email" in payload.filters:
        businesses = [business for business in businesses if business.email]

    # Step 5: Sort — email first, then phone, then rest
    # (most contactable leads surface at the top)
    businesses.sort(
        key=lambda b: (0 if b.email else 1 if b.phone else 2)
    )
    businesses = businesses[:payload.limit]

    # Step 6: Save
    save_discovery_results(
        db=db,
        user_id=user_id,
        businesses=businesses,
    )

    # Step 7: Return
    return BusinessDiscoveryResponse(
        success=True,
        total_found=len(businesses),
        location={
            "requested_country": payload.country,
            "requested_state":   payload.state,
            "requested_city":    payload.city,
            "resolved_name":     location["display_name"],
            "latitude":          location["latitude"],
            "longitude":         location["longitude"],
        },
        industry=normalized_industry,
        businesses=businesses,
        candidates_scanned=candidates_scanned,
        filters_applied=sorted(payload.filters),
    )
