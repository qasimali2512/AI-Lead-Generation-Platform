"""
Poori city ki search (radius nahi) -- Discover Leads page aur Auto Discovery
dono yahi use karte hain.

1. find_city_area()      -> Nominatim se city ki boundary (OSM area id).
2. fetch_city_elements() -> Overpass se us boundary ke andar ke businesses.
                            Boundary na mile to 30 km ka circle.
3. filter_already_saved()-> jo leads pehle se saved hain unhein hatao.
"""
from __future__ import annotations

import asyncio
import logging
import math
import threading
import time
import urllib.parse
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.schemas.discovery import BusinessDiscoveryResult
from app.services.discovery import (
    NOMINATIM_URL,
    OVERPASS_URLS,
    USER_AGENT,
    build_overpass_query,
    clean_value,
    get_industry_search_terms,
    get_industry_tags,
    normalize_business,
)

logger = logging.getLogger("ai-lead-city-search")

MAX_RAW_ELEMENTS = 5000
FALLBACK_RADIUS_M = 30_000          # boundary na mile to
OVERPASS_SERVER_TIMEOUT = 60        # seconds, Overpass ke andar
OVERPASS_REQUEST_TIMEOUT = 75.0     # seconds, HTTP request
NOMINATIM_TIMEOUT = 20.0
MIN_OVERPASS_TIME_LEFT = 8.0        # itna waqt na ho to naya server try na karo

MAX_BOUNDARY_SPAN_DEG = 1.5         # is se bara = state/country, city nahi
MAX_BOUNDARY_DISTANCE_KM = 40.0     # GeoNames ke shehr se itna door nahi
BAD_ADDRESS_TYPES = {
    "country", "state", "region", "county", "state_district",
    "continent", "province",
}


class LocationNotFound(Exception):
    pass


class TransientSearchError(RuntimeError):
    """Network / server masla -- baad mein dobara try ho sakta hai."""


# ---------------------------------------------------------
# Nominatim (1 request/second ka usage policy)
# ---------------------------------------------------------

_nominatim_guard = threading.Lock()
_last_nominatim_call = 0.0


async def _nominatim_wait() -> None:
    global _last_nominatim_call
    with _nominatim_guard:
        now = time.monotonic()
        wait = max(0.0, _last_nominatim_call + 1.1 - now)
        _last_nominatim_call = now + wait
    if wait:
        await asyncio.sleep(wait)


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(a))


def _area_id(result: dict[str, Any]) -> int | None:
    try:
        osm_id = int(result["osm_id"])
    except (KeyError, TypeError, ValueError):
        return None
    osm_type = result.get("osm_type")
    if osm_type == "relation":
        return 3_600_000_000 + osm_id
    if osm_type == "way":
        return 2_400_000_000 + osm_id
    return None


def _boundary_ok(result: dict[str, Any], near: tuple[float, float] | None) -> bool:
    if _area_id(result) is None:
        return False
    if result.get("addresstype") in BAD_ADDRESS_TYPES:
        return False

    try:
        south, north, west, east = (float(v) for v in result["boundingbox"])
    except (KeyError, TypeError, ValueError):
        return False
    if (north - south) > MAX_BOUNDARY_SPAN_DEG or (east - west) > MAX_BOUNDARY_SPAN_DEG:
        return False

    if near is not None:
        try:
            lat, lon = float(result["lat"]), float(result["lon"])
        except (KeyError, TypeError, ValueError):
            return False
        if _distance_km(lat, lon, near[0], near[1]) > MAX_BOUNDARY_DISTANCE_KM:
            return False

    return True


def _to_location(result: dict[str, Any], with_area: bool) -> dict[str, Any]:
    address = result.get("address") or {}
    return {
        "display_name": result.get("display_name"),
        "latitude": float(result["lat"]),
        "longitude": float(result["lon"]),
        "area_id": _area_id(result) if with_area else None,
        "country": address.get("country"),
        "state": address.get("state"),
    }


async def find_city_area(
    queries: list[str],
    *,
    country_code: str | None = None,
    near: tuple[float, float] | None = None,
) -> dict[str, Any]:
    """
    City ki boundary (area id) dhoondo.

    * near=None  (Discover Leads page): city ka naam user ne likha hai.
      Kuch na mile -> LocationNotFound; server down -> TransientSearchError.
    * near=(lat, lon) (Auto Discovery): shehr GeoNames se aaya hai, is liye
      coordinates pehle se maloom hain.  Boundary na mile to hum usi point
      par 30 km circle wala fallback dete hain (kabhi error nahi).
    """
    last_error: Exception | None = None
    got_any_response = False
    first_result: dict[str, Any] | None = None

    for query in queries:
        params: dict[str, Any] = {
            "q": query,
            "format": "jsonv2",
            "limit": 8,
            "addressdetails": 1,
        }
        if country_code:
            params["countrycodes"] = country_code.lower()

        await _nominatim_wait()
        try:
            async with httpx.AsyncClient(
                timeout=NOMINATIM_TIMEOUT, headers={"User-Agent": USER_AGENT}
            ) as client:
                response = await client.get(NOMINATIM_URL, params=params)
                response.raise_for_status()
                results = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            last_error = exc
            logger.warning("Nominatim failed for %r: %s", query, exc)
            continue

        got_any_response = True
        if not isinstance(results, list) or not results:
            continue

        if first_result is None:
            first_result = results[0]

        candidates = [r for r in results if _boundary_ok(r, near)]
        if candidates:
            # boundary/place wale pehle, phir Nominatim ki apni tarteeb
            candidates.sort(
                key=lambda r: 0 if r.get("category") in ("boundary", "place") else 1
            )
            return _to_location(candidates[0], with_area=True)

    if near is not None:
        return {
            "display_name": None,
            "latitude": near[0],
            "longitude": near[1],
            "area_id": None,
            "country": None,
            "state": None,
        }

    if first_result is not None:
        try:
            return _to_location(first_result, with_area=False)
        except (KeyError, TypeError, ValueError):
            pass

    if not got_any_response and last_error is not None:
        raise TransientSearchError(f"Nominatim unavailable: {last_error}")

    raise LocationNotFound(queries[0] if queries else "")


# ---------------------------------------------------------
# Overpass
# ---------------------------------------------------------

async def _fetch_overpass(query: str, deadline: float | None) -> dict[str, Any]:
    last_error: Exception | None = None

    for endpoint in OVERPASS_URLS:
        timeout = OVERPASS_REQUEST_TIMEOUT
        if deadline is not None:
            remaining = deadline - time.monotonic()
            if remaining < MIN_OVERPASS_TIME_LEFT:
                last_error = TimeoutError("time budget finished")
                break
            timeout = min(timeout, remaining)

        try:
            encoded = urllib.parse.urlencode({"data": query})
            async with httpx.AsyncClient(
                timeout=timeout,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            ) as client:
                response = await client.get(f"{endpoint}?{encoded}")
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict):
                return data
            raise ValueError("unexpected Overpass response")
        except (httpx.HTTPError, ValueError) as exc:
            last_error = exc
            logger.warning("Overpass failed on %s: %s", endpoint, exc)

    raise TransientSearchError(f"Overpass unavailable: {last_error}")


def _has_named(elements: list[Any]) -> bool:
    return any(
        isinstance(e, dict) and clean_value((e.get("tags") or {}).get("name"))
        for e in elements
    )


async def fetch_city_elements(
    industry: str,
    location: dict[str, Any],
    *,
    max_elements: int = MAX_RAW_ELEMENTS,
    deadline: float | None = None,
) -> list[Any]:
    """Boundary (area_id) ke andar search.  Na ho to 30 km circle."""
    tags = get_industry_tags(industry)
    if not tags and not get_industry_search_terms(industry):
        return []

    async def run(area_id: int | None) -> list[Any]:
        def make(include_tags: bool, include_keywords: bool) -> str:
            return build_overpass_query(
                latitude=location["latitude"],
                longitude=location["longitude"],
                industry=industry,
                radius=FALLBACK_RADIUS_M,
                max_elements=max_elements,
                include_tag_search=include_tags,
                include_keyword_search=include_keywords,
                area_id=area_id,
                timeout=OVERPASS_SERVER_TIMEOUT,
            )

        elements: list[Any] = []

        if tags:
            data = await _fetch_overpass(make(True, False), deadline)
            raw = data.get("elements") or []
            elements = raw if isinstance(raw, list) else []

        # Har business type ka OSM tag nahi hota -- naam se dhoondo
        if not _has_named(elements) and get_industry_search_terms(industry):
            data = await _fetch_overpass(make(False, True), deadline)
            raw = data.get("elements") or []
            elements = raw if isinstance(raw, list) else []

        return elements

    area_id = location.get("area_id")
    elements = await run(area_id)

    if not elements and area_id:
        logger.info("Boundary search returned nothing; using %d m circle.", FALLBACK_RADIUS_M)
        elements = await run(None)

    return elements


# ---------------------------------------------------------
# Normalize / duplicates / score
# ---------------------------------------------------------

def normalize_elements(
    elements: list[Any],
    industry: str,
    *,
    city: str | None = None,
    state: str | None = None,
    country: str | None = None,
) -> list[BusinessDiscoveryResult]:
    businesses: list[BusinessDiscoveryResult] = []
    seen_ids: set[str] = set()
    seen_names: set[str] = set()

    for element in elements:
        if not isinstance(element, dict):
            continue

        business = normalize_business(element=element, industry=industry)
        if business is None or business.source_id in seen_ids:
            continue

        key = f"{business.name.lower().strip()}|{(business.address or '').lower()}"
        if key in seen_names:
            continue

        seen_ids.add(business.source_id)
        seen_names.add(key)
        businesses.append(
            business.model_copy(
                update={
                    "city": business.city or city,
                    "state": business.state or state,
                    "country": business.country or country,
                }
            )
        )

    return businesses


def load_existing_emails(db: Session, user_id: UUID) -> set[str]:
    rows = db.scalars(
        select(Lead.email).where(Lead.user_id == user_id, Lead.email.is_not(None))
    ).all()
    db.commit()  # transaction band -- aage lambay network kaam hain
    return {e.lower() for e in rows if e}


def filter_already_saved(
    db: Session,
    user_id: UUID,
    businesses: list[BusinessDiscoveryResult],
) -> tuple[list[BusinessDiscoveryResult], int]:
    """Jo businesses (source_id ya email se) pehle se leads mein hain unhein hatao."""
    if not businesses:
        return [], 0

    ids = [b.source_id for b in businesses]
    existing_ids: set[str] = set()
    for i in range(0, len(ids), 1000):
        rows = db.scalars(
            select(Lead.source_id).where(
                Lead.user_id == user_id,
                Lead.source_id.in_(ids[i : i + 1000]),
            )
        ).all()
        existing_ids.update(rows)

    existing_emails = load_existing_emails(db, user_id)

    fresh: list[BusinessDiscoveryResult] = []
    seen_emails: set[str] = set()
    skipped = 0
    for business in businesses:
        email = business.email.lower() if business.email else None
        if business.source_id in existing_ids or (
            email and (email in existing_emails or email in seen_emails)
        ):
            skipped += 1
            continue
        if email:
            seen_emails.add(email)
        fresh.append(business)

    return fresh, skipped


def score_business(b: BusinessDiscoveryResult) -> int:
    """Agency ke liye achi lead = email + phone + (website na ho)."""
    score = 0
    if b.email:
        score += 3
    if b.phone:
        score += 1
    score += 3 if not b.website else 1
    return score