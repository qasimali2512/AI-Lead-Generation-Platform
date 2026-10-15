"""
Auto-discovery service.

Ek run = ek location (country/state/city):
  1. City ki poori boundary (area) mein businesses dhoondo -- koi radius nahi.
  2. Jo leads pehle se saved hain (source_id ya email) unhein nikaal do.
  3. "Email" / "Website" buttons ke hisaab se filter karo.
     Email chahiye aur OSM mein nahi hai to business ki website se email nikalo.
  4. Best leads ko score karke batch_size tak save karo.
  5. Agli location par chale jao.
"""
from __future__ import annotations

import asyncio
import ipaddress
import logging
import random
import re
import socket
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.auto_discovery import AutoDiscoverySettings
from app.models.lead import Lead
from app.schemas.discovery import BusinessDiscoveryResult
from app.services.auto_discovery_locations import build_location_sequence
from app.services.discovery import (
    NOMINATIM_URL,
    OVERPASS_URLS,
    USER_AGENT,
    build_overpass_query,
    clean_value,
    escape_overpass_regex,
    get_industry_search_terms,
    get_industry_tags,
    normalize_business,
    normalize_industry,
)
from app.services.leads import save_discovery_results

logger = logging.getLogger("ai-lead-auto-discovery")

MAX_RAW_ELEMENTS = 4000          # ek city se max itne OSM records
ENRICH_CANDIDATE_LIMIT = 400     # email dhoondne ke liye max websites
ENRICH_CHUNK = 24                # ek saath itni websites
PAGE_TIMEOUT = 8.0
PAGE_MAX_BYTES = 800_000
OVERPASS_TIMEOUT = 90.0          # per-attempt timeout (large area queries need more)
MAX_FAILURES_BEFORE_SKIP = 3

# Retry / backoff config for Overpass
_OVERPASS_RETRY_BASE = 2.0   # seconds — base for exponential backoff
_OVERPASS_RETRY_CAP  = 30.0  # seconds — max backoff per attempt
_OVERPASS_JITTER     = 2.0   # seconds — random jitter added on top

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


class LocationNotFound(Exception):
    pass


# =========================================================
# 1. Geocoding (osm_type/osm_id chahiye taake area ban sake)
# =========================================================

async def _geocode_area(
    country: str, state: str | None, city: str
) -> dict[str, Any]:
    queries: list[str] = []
    if state:
        queries.append(f"{city}, {state}, {country}")
    queries.append(f"{city}, {country}")

    last_error: Exception | None = None

    for query in queries:
        params = {"q": query, "format": "jsonv2", "limit": 5}
        try:
            async with httpx.AsyncClient(
                timeout=20.0, headers={"User-Agent": USER_AGENT}
            ) as client:
                response = await client.get(NOMINATIM_URL, params=params)
                response.raise_for_status()
                results = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            last_error = exc
            continue

        if not results:
            continue

        def pick() -> dict[str, Any]:
            for r in results:
                if r.get("osm_type") == "relation" and r.get("category") in (
                    "boundary", "place"
                ):
                    return r
            for r in results:
                if r.get("osm_type") == "relation":
                    return r
            return results[0]

        best = pick()
        osm_type = best.get("osm_type")
        osm_id = int(best["osm_id"])

        area_id: int | None = None
        if osm_type == "relation":
            area_id = 3_600_000_000 + osm_id
        elif osm_type == "way":
            area_id = 2_400_000_000 + osm_id

        return {
            "latitude": float(best["lat"]),
            "longitude": float(best["lon"]),
            "display_name": best.get("display_name"),
            "area_id": area_id,
        }

    if last_error:
        raise RuntimeError(f"Nominatim unavailable: {last_error}")
    raise LocationNotFound(f"{city}, {state or ''} {country}".strip())


# =========================================================
# 2. Overpass: poori city (area) -- radius nahi
# =========================================================

def _build_area_query(
    industry: str,
    area_id: int,
    include_tags: bool,
    include_keywords: bool,
) -> str:
    statements: list[str] = []

    if include_tags:
        for tag in dict.fromkeys(get_industry_tags(industry)):
            for osm_type in ("node", "way", "relation"):
                statements.append(f"{osm_type}(area.a){tag};")

    if include_keywords:
        for term in get_industry_search_terms(industry):
            escaped = escape_overpass_regex(term)
            for osm_type in ("node", "way", "relation"):
                statements.append(
                    f'{osm_type}(area.a)["name"~"{escaped}",i];'
                )
                statements.append(
                    f'{osm_type}(area.a)["industrial"~"{escaped}",i]["name"];'
                )

    joined = "\n".join(statements)
    return (
        "[out:json][timeout:60][maxsize:128000000];\n"
        f"area(id:{area_id})->.a;\n"
        f"(\n{joined}\n);\n"
        f"out center tags {MAX_RAW_ELEMENTS};\n"
    )


async def _fetch_overpass(query: str) -> dict[str, Any]:
    """
    Try every Overpass mirror in order.

    Per endpoint strategy:
      1. POST first  — avoids URL-length limits on large area queries
                       (the 500 errors in the logs are often caused by
                        a GET URL exceeding the server's limit)
      2. GET fallback — some mirrors reject POST; fall back gracefully

    Between endpoint switches we apply exponential back-off with jitter so
    we don't hammer already-overloaded servers.
    """
    post_headers = {
        "User-Agent": USER_AGENT,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json, */*",
    }
    get_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, */*",
    }

    last_error: Exception | None = None

    for attempt, endpoint in enumerate(OVERPASS_URLS):
        # Exponential back-off between endpoint attempts (not on the first one)
        if attempt > 0:
            delay = min(
                _OVERPASS_RETRY_BASE * (2 ** (attempt - 1)),
                _OVERPASS_RETRY_CAP,
            ) + random.uniform(0, _OVERPASS_JITTER)
            logger.info(
                "Overpass: waiting %.1fs before trying next mirror (#%d)",
                delay, attempt + 1,
            )
            await asyncio.sleep(delay)

        # Try POST first, then GET
        for method, hdrs in (("POST", post_headers), ("GET", get_headers)):
            try:
                logger.info(
                    "Overpass %s attempt %d/%d: %s",
                    method, attempt + 1, len(OVERPASS_URLS), endpoint,
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

                # 429 Rate-limited: honour Retry-After if present, then move on
                if response.status_code == 429:
                    retry_after = float(
                        response.headers.get("Retry-After", _OVERPASS_RETRY_CAP)
                    )
                    wait = min(retry_after, _OVERPASS_RETRY_CAP)
                    logger.warning(
                        "Overpass rate-limited on %s, waiting %.0fs",
                        endpoint, wait,
                    )
                    await asyncio.sleep(wait)
                    last_error = httpx.HTTPStatusError(
                        f"429 Too Many Requests",
                        request=response.request,
                        response=response,
                    )
                    break  # skip GET fallback for this endpoint

                response.raise_for_status()
                data = response.json()

                if not isinstance(data, dict):
                    raise ValueError("Overpass returned unexpected response type.")

                return data

            except httpx.TimeoutException as exc:
                last_error = exc
                logger.warning(
                    "Overpass timeout: %s %s (%.0fs)",
                    method, endpoint, OVERPASS_TIMEOUT,
                )
                # Timeout on POST is almost certainly a server issue;
                # no point trying GET on the same mirror.
                break

            except httpx.HTTPStatusError as exc:
                last_error = exc
                logger.warning(
                    "Overpass HTTP %s: %s %s",
                    exc.response.status_code, method, endpoint,
                )
                # 5xx on POST: try GET in case POST is not supported
                if exc.response.status_code >= 500 and method == "POST":
                    continue
                # Any other error: move to next mirror
                break

            except httpx.HTTPError as exc:
                last_error = exc
                logger.warning(
                    "Overpass connection error: %s %s — %s",
                    method, endpoint, exc,
                )
                break

            except ValueError as exc:
                last_error = exc
                logger.warning("Overpass bad JSON: %s %s", method, endpoint)
                break

    raise RuntimeError(f"All Overpass servers failed: {last_error}")


def _has_named(elements: list[Any]) -> bool:
    return any(
        isinstance(e, dict) and clean_value((e.get("tags") or {}).get("name"))
        for e in elements
    )


async def _fetch_city_elements(
    industry: str, geo: dict[str, Any], use_area: bool = True
) -> list[Any]:
    tags = get_industry_tags(industry)
    area_id = geo.get("area_id") if use_area else None

    def make(include_tags: bool, include_keywords: bool) -> str:
        if area_id:
            return _build_area_query(
                industry, area_id, include_tags, include_keywords
            )
        # Fallback: boundary nahi mili to bara circle (30 km)
        return build_overpass_query(
            latitude=geo["latitude"],
            longitude=geo["longitude"],
            industry=industry,
            radius=30000,
            max_elements=MAX_RAW_ELEMENTS,
            include_tag_search=include_tags,
            include_keyword_search=include_keywords,
        )

    elements: list[Any] = []

    if tags:
        data = await _fetch_overpass(make(True, False))
        raw = data.get("elements") or []
        elements = raw if isinstance(raw, list) else []

    if not _has_named(elements):
        data = await _fetch_overpass(make(False, True))
        raw = data.get("elements") or []
        elements = raw if isinstance(raw, list) else []

    if not elements and area_id:
        logger.info("Area query empty, retrying with wide circle.")
        return await _fetch_city_elements(industry, geo, use_area=False)

    return elements


# =========================================================
# 3. Website se email nikalna
# =========================================================

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")
BAD_EMAIL_SUFFIXES = (
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".css", ".js", ".ico",
)
BAD_EMAIL_PARTS = (
    "example.", "sentry", "wixpress", "yourdomain", "domain.com",
    "email.com", "noreply", "no-reply", "donotreply", "u003e", "@2x",
)


def _host_is_public(host: str) -> bool:
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return False
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0].split("%")[0])
        except ValueError:
            return False
        if not ip.is_global:
            return False
    return True


async def _safe_get(client: httpx.AsyncClient, url: str) -> str:
    """GET with SSRF protection (private IPs blocked, redirects checked)."""
    for _ in range(4):
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return ""
        if not await asyncio.to_thread(_host_is_public, parsed.hostname):
            return ""
        try:
            async with client.stream("GET", url) as resp:
                if resp.status_code in (301, 302, 303, 307, 308):
                    location = resp.headers.get("location")
                    if not location:
                        return ""
                    url = urllib.parse.urljoin(url, location)
                    continue
                if resp.status_code >= 400:
                    return ""
                ctype = resp.headers.get("content-type", "").lower()
                if ctype and "html" not in ctype and "text" not in ctype:
                    return ""
                buf = bytearray()
                async for chunk in resp.aiter_bytes():
                    buf.extend(chunk)
                    if len(buf) > PAGE_MAX_BYTES:
                        break
                return buf.decode(resp.encoding or "utf-8", errors="ignore")
        except (httpx.HTTPError, ValueError):
            return ""
    return ""


def _valid_email(value: str) -> bool:
    value = value.lower()
    if len(value) > 254 or not EMAIL_RE.fullmatch(value):
        return False
    if value.endswith(BAD_EMAIL_SUFFIXES):
        return False
    return not any(part in value for part in BAD_EMAIL_PARTS)


def _extract_emails(html: str, site_host: str) -> list[str]:
    found: list[str] = []

    soup = BeautifulSoup(html, "html.parser")
    for a in soup.select("a[href^='mailto:' i]"):
        href = urllib.parse.unquote(a.get("href", ""))[7:].split("?")[0]
        for part in re.split(r"[;,]", href):
            part = part.strip().lower()
            if part and _valid_email(part) and part not in found:
                found.append(part)

    text = soup.get_text(" ")
    for match in EMAIL_RE.findall(text):
        match = match.lower().strip(".")
        if _valid_email(match) and match not in found:
            found.append(match)

    def same_domain(email: str) -> bool:
        domain = email.split("@", 1)[1]
        return bool(site_host) and (
            domain == site_host or domain.endswith("." + site_host)
        )

    found.sort(key=lambda e: 0 if same_domain(e) else 1)
    return found


async def _find_email(client: httpx.AsyncClient, website: str) -> str | None:
    base = website if website.startswith(("http://", "https://")) else f"https://{website}"
    host = (urllib.parse.urlparse(base).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]

    for path in ("", "/contact", "/contact-us", "/about"):
        url = urllib.parse.urljoin(base, path) if path else base
        html = await _safe_get(client, url)
        if not html:
            continue
        emails = _extract_emails(html, host)
        if emails:
            return emails[0]
    return None


async def _enrich_emails(
    candidates: list[BusinessDiscoveryResult],
    seen_emails: set[str],
    target: int,
) -> list[BusinessDiscoveryResult]:
    """Website wali leads se email nikalo jab tak `target` na mil jaye."""
    results: list[BusinessDiscoveryResult] = []
    semaphore = asyncio.Semaphore(8)

    async with httpx.AsyncClient(
        timeout=PAGE_TIMEOUT,
        headers={"User-Agent": BROWSER_UA},
        follow_redirects=False,
    ) as client:

        async def work(b: BusinessDiscoveryResult):
            async with semaphore:
                email = await asyncio.wait_for(
                    _find_email(client, b.website or ""), timeout=30
                )
            return b, email

        for i in range(0, len(candidates), ENRICH_CHUNK):
            chunk = candidates[i : i + ENRICH_CHUNK]
            outcomes = await asyncio.gather(
                *(work(b) for b in chunk), return_exceptions=True
            )
            for outcome in outcomes:
                if isinstance(outcome, BaseException):
                    continue
                business, email = outcome
                if email and email.lower() not in seen_emails:
                    seen_emails.add(email.lower())
                    results.append(business.model_copy(update={"email": email}))
            if len(results) >= target:
                break

    return results


# =========================================================
# 4. Duplicate filter + scoring
# =========================================================

def _existing_keys(
    db: Session, user_id: UUID, businesses: list[BusinessDiscoveryResult]
) -> tuple[set[str], set[str]]:
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

    existing_emails = {
        e.lower()
        for e in db.scalars(
            select(Lead.email).where(
                Lead.user_id == user_id, Lead.email.is_not(None)
            )
        ).all()
        if e
    }
    return existing_ids, existing_emails


def _score(b: BusinessDiscoveryResult) -> int:
    """Agency ke liye achi lead = email + phone + (website na ho)."""
    score = 0
    if b.email:
        score += 3
    if b.phone:
        score += 1
    score += 3 if not b.website else 1
    return score


# =========================================================
# 5. Ek location ka run
# =========================================================

async def _discover_one_location(
    db: Session,
    cfg: AutoDiscoverySettings,
    country: str,
    state: str | None,
    city: str,
) -> int:
    industry = normalize_industry(cfg.industry or "")

    geo = await _geocode_area(country, state, city)
    elements = await _fetch_city_elements(industry, geo)

    # normalize + in-run dedupe
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

    # Pehle se saved leads hata do (limit lagne se PEHLE)
    existing_ids, existing_emails = _existing_keys(db, cfg.user_id, businesses)
    fresh = [b for b in businesses if b.source_id not in existing_ids]
    seen_emails = set(existing_emails)

    # "Website" button
    if cfg.require_website:
        fresh = [b for b in fresh if b.website]

    # "Email" button
    if cfg.require_email:
        with_email: list[BusinessDiscoveryResult] = []
        need_lookup: list[BusinessDiscoveryResult] = []
        for b in fresh:
            if b.email:
                if b.email.lower() in seen_emails:
                    continue
                seen_emails.add(b.email.lower())
                with_email.append(b)
            elif b.website:
                need_lookup.append(b)

        if len(with_email) < cfg.batch_size and need_lookup:
            enriched = await _enrich_emails(
                need_lookup[:ENRICH_CANDIDATE_LIMIT],
                seen_emails,
                target=cfg.batch_size - len(with_email),
            )
            with_email.extend(enriched)
        fresh = with_email
    else:
        unique: list[BusinessDiscoveryResult] = []
        for b in fresh:
            if b.email:
                if b.email.lower() in seen_emails:
                    continue
                seen_emails.add(b.email.lower())
            unique.append(b)
        fresh = unique

    fresh.sort(key=_score, reverse=True)
    selected = fresh[: cfg.batch_size]

    if not selected:
        return 0

    result = save_discovery_results(
        db=db, user_id=cfg.user_id, businesses=selected
    )
    return int(result["created"])


async def run_for_settings(db: Session, cfg: AutoDiscoverySettings) -> dict:
    """Ek location process karo aur cursor aage barhao."""
    sequence = build_location_sequence(cfg.countries)
    if not sequence or not cfg.industry:
        return {"skipped": True}

    index = cfg.location_index % len(sequence)
    country, state, city = sequence[index]
    label = ", ".join(p for p in (city, state, country) if p)

    logger.info("Auto-discovery user=%s industry=%r -> %s", cfg.user_id, cfg.industry, label)

    advance = True
    found = 0
    error: str | None = None

    try:
        found = await _discover_one_location(db, cfg, country, state, city)
        cfg.consecutive_failures = 0
    except LocationNotFound:
        error = f"Location not found: {label}"
        cfg.consecutive_failures = 0
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.warning("Auto-discovery failed for %s: %s", label, exc)
        error = f"{label}: {str(exc)[:300]}"
        cfg.consecutive_failures += 1
        if cfg.consecutive_failures < MAX_FAILURES_BEFORE_SKIP:
            advance = False   # isi city ko dobara try karo
        else:
            cfg.consecutive_failures = 0

    # cfg rollback ke baad dobara attach hona chahiye
    cfg = db.merge(cfg)
    if advance:
        cfg.location_index = (index + 1) % len(sequence)
    cfg.last_location = label
    cfg.last_run_found = found
    cfg.total_found = (cfg.total_found or 0) + found
    cfg.last_error = error
    cfg.last_run_at = datetime.now(timezone.utc)
    db.commit()

    logger.info("Auto-discovery %s: %d new leads", label, found)
    return {"location": label, "found": found, "error": error}


# =========================================================
# 6. Scheduler / API ke liye helpers
# =========================================================

def _claim(db: Session, cfg: AutoDiscoverySettings) -> bool:
    """Atomic claim -- do instances ek hi user ko ek saath run na karein."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=cfg.run_every_minutes)
    result = db.execute(
        update(AutoDiscoverySettings)
        .where(
            AutoDiscoverySettings.id == cfg.id,
            or_(
                AutoDiscoverySettings.last_run_at.is_(None),
                AutoDiscoverySettings.last_run_at <= cutoff,
            ),
        )
        .values(last_run_at=now)
    )
    db.commit()
    return (result.rowcount or 0) == 1


async def run_due_users(db: Session) -> int:
    due = list(
        db.scalars(
            select(AutoDiscoverySettings).where(
                AutoDiscoverySettings.enabled.is_(True),
                AutoDiscoverySettings.industry.is_not(None),
            )
        ).all()
    )
    now = datetime.now(timezone.utc)
    ran = 0
    for cfg in due:
        if cfg.last_run_at and cfg.last_run_at + timedelta(
            minutes=cfg.run_every_minutes
        ) > now:
            continue
        if not _claim(db, cfg):
            continue
        db.refresh(cfg)
        await run_for_settings(db, cfg)
        ran += 1
    return ran


async def run_now_background(user_id: UUID) -> None:
    """'Run now' button ke liye (background task)."""
    db = SessionLocal()
    try:
        cfg = db.scalar(
            select(AutoDiscoverySettings).where(
                AutoDiscoverySettings.user_id == user_id
            )
        )
        if cfg is None or not cfg.industry:
            return
        await run_for_settings(db, cfg)
    except Exception:  # noqa: BLE001
        logger.exception("Run-now auto-discovery failed.")
    finally:
        db.close()