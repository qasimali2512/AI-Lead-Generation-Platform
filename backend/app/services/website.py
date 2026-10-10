from __future__ import annotations

import ipaddress
import socket
import time
from datetime import datetime, timezone
from urllib.parse import urlparse, urlunparse
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.services.leads import get_user_lead


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

REQUEST_TIMEOUT = httpx.Timeout(
    connect=8.0,
    read=12.0,
    write=8.0,
    pool=8.0,
)

MAX_REDIRECTS = 5

USER_AGENT = (
    "AI-Lead-Generation-Platform/1.0 "
    "(website detection service)"
)


# ---------------------------------------------------------
# URL helpers
# ---------------------------------------------------------

def normalize_url(url: str) -> str:
    value = url.strip()

    if not value:
        raise ValueError(
            "Website URL is empty."
        )

    if not value.startswith(
        ("http://", "https://")
    ):
        value = f"https://{value}"

    parsed = urlparse(value)

    if parsed.scheme not in {
        "http",
        "https",
    }:
        raise ValueError(
            "Only HTTP and HTTPS URLs are supported."
        )

    if not parsed.hostname:
        raise ValueError(
            "Website URL does not contain a valid hostname."
        )

    if parsed.username or parsed.password:
        raise ValueError(
            "URLs containing username or password are not allowed."
        )

    # Remove fragments because they are not sent to the server.
    normalized = parsed._replace(
        fragment=""
    )

    return urlunparse(normalized)


# ---------------------------------------------------------
# SSRF protection
# ---------------------------------------------------------

def is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return any(
        [
            ip.is_private,
            ip.is_loopback,
            ip.is_link_local,
            ip.is_multicast,
            ip.is_reserved,
            ip.is_unspecified,
        ]
    )


def validate_hostname(hostname: str) -> None:
    hostname = hostname.strip().lower()

    if not hostname:
        raise ValueError(
            "Website hostname is empty."
        )

    if hostname in {
        "localhost",
        "localhost.localdomain",
    }:
        raise ValueError(
            "Localhost URLs are not allowed."
        )

    try:
        direct_ip = ipaddress.ip_address(
            hostname
        )

        if is_blocked_ip(direct_ip):
            raise ValueError(
                "Private or local IP addresses are not allowed."
            )

        return

    except ValueError:
        # Not a literal IP address.
        pass

    try:
        addresses = socket.getaddrinfo(
            hostname,
            None,
            type=socket.SOCK_STREAM,
        )

    except socket.gaierror as exc:
        raise ValueError(
            "Website hostname could not be resolved."
        ) from exc

    resolved_ips: set[str] = set()

    for address in addresses:
        ip_value = address[4][0]

        if ip_value in resolved_ips:
            continue

        resolved_ips.add(ip_value)

        try:
            ip = ipaddress.ip_address(
                ip_value
            )
        except ValueError as exc:
            raise ValueError(
                "Website hostname resolved to an invalid IP address."
            ) from exc

        if is_blocked_ip(ip):
            raise ValueError(
                "Website hostname resolves to a private or local IP address."
            )


# ---------------------------------------------------------
# Website check
# ---------------------------------------------------------

async def check_website_url(
    website: str,
) -> dict:

    try:
        normalized_url = normalize_url(
            website
        )

        parsed = urlparse(
            normalized_url
        )

        hostname = parsed.hostname

        if not hostname:
            raise ValueError(
                "Website hostname is missing."
            )

        validate_hostname(
            hostname
        )

    except ValueError as exc:
        return {
            "website": website,
            "website_status": "invalid",
            "final_url": None,
            "http_status": None,
            "response_time_ms": None,
            "error": str(exc),
        }

    started_at = time.perf_counter()

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,*/*;q=0.8"
        ),
    }

    try:
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
            max_redirects=MAX_REDIRECTS,
            headers=headers,
        ) as client:

            response = await client.get(
                normalized_url
            )

        elapsed_ms = int(
            (time.perf_counter() - started_at)
            * 1000
        )

        final_url = str(
            response.url
        )

        final_hostname = (
            urlparse(final_url).hostname
        )

        if final_hostname:
            try:
                validate_hostname(
                    final_hostname
                )
            except ValueError as exc:
                return {
                    "website": normalized_url,
                    "website_status": "invalid",
                    "final_url": None,
                    "http_status": response.status_code,
                    "response_time_ms": elapsed_ms,
                    "error": (
                        "Redirected to a blocked or "
                        f"unsafe hostname: {exc}"
                    ),
                }

        if 200 <= response.status_code < 400:
            return {
                "website": normalized_url,
                "website_status": "has_website",
                "final_url": final_url,
                "http_status": response.status_code,
                "response_time_ms": elapsed_ms,
                "error": None,
            }

        return {
            "website": normalized_url,
            "website_status": "unreachable",
            "final_url": final_url,
            "http_status": response.status_code,
            "response_time_ms": elapsed_ms,
            "error": (
                f"Website returned HTTP "
                f"{response.status_code}."
            ),
        }

    except httpx.TooManyRedirects:
        elapsed_ms = int(
            (time.perf_counter() - started_at)
            * 1000
        )

        return {
            "website": normalized_url,
            "website_status": "unreachable",
            "final_url": None,
            "http_status": None,
            "response_time_ms": elapsed_ms,
            "error": "Too many redirects.",
        }

    except httpx.TimeoutException:
        elapsed_ms = int(
            (time.perf_counter() - started_at)
            * 1000
        )

        return {
            "website": normalized_url,
            "website_status": "unreachable",
            "final_url": None,
            "http_status": None,
            "response_time_ms": elapsed_ms,
            "error": "Website request timed out.",
        }

    except httpx.RequestError as exc:
        elapsed_ms = int(
            (time.perf_counter() - started_at)
            * 1000
        )

        return {
            "website": normalized_url,
            "website_status": "unreachable",
            "final_url": None,
            "http_status": None,
            "response_time_ms": elapsed_ms,
            "error": (
                f"Website request failed: "
                f"{type(exc).__name__}."
            ),
        }

    except Exception as exc:
        elapsed_ms = int(
            (time.perf_counter() - started_at)
            * 1000
        )

        return {
            "website": normalized_url,
            "website_status": "unreachable",
            "final_url": None,
            "http_status": None,
            "response_time_ms": elapsed_ms,
            "error": (
                f"Unexpected website error: "
                f"{type(exc).__name__}."
            ),
        }


# ---------------------------------------------------------
# Persist website result
# ---------------------------------------------------------

def persist_website_result(
    db: Session,
    lead: Lead,
    result: dict,
) -> Lead:

    lead.website_status = result[
        "website_status"
    ]

    if result.get("website"):
        lead.website = result[
            "website"
        ]

    lead.website_final_url = result.get(
        "final_url"
    )

    lead.website_http_status = result.get(
        "http_status"
    )

    lead.website_response_time_ms = result.get(
        "response_time_ms"
    )

    lead.website_error = result.get(
        "error"
    )

    lead.website_checked_at = (
        datetime.now(timezone.utc)
    )

    try:
        db.commit()
        db.refresh(lead)

    except Exception:
        db.rollback()
        raise

    return lead


# ---------------------------------------------------------
# Check one lead
# ---------------------------------------------------------

async def check_lead_website(
    db: Session,
    user_id: UUID,
    lead_id: UUID,
) -> dict:

    lead = get_user_lead(
        db=db,
        user_id=user_id,
        lead_id=lead_id,
    )

    # No website URL stored.
    if not lead.website:

        result = {
            "website": None,
            "website_status": "no_website",
            "final_url": None,
            "http_status": None,
            "response_time_ms": None,
            "error": (
                "No website URL is available "
                "for this lead."
            ),
        }

        persist_website_result(
            db=db,
            lead=lead,
            result=result,
        )

        return result

    result = await check_website_url(
        lead.website
    )

    persist_website_result(
        db=db,
        lead=lead,
        result=result,
    )

    return result


# ---------------------------------------------------------
# Check multiple leads
# ---------------------------------------------------------

async def check_multiple_lead_websites(
    db: Session,
    user_id: UUID,
    lead_ids: list[UUID],
) -> list[dict]:

    results: list[dict] = []

    for lead_id in lead_ids:

        try:
            result = await check_lead_website(
                db=db,
                user_id=user_id,
                lead_id=lead_id,
            )

            results.append(
                {
                    "lead_id": lead_id,
                    **result,
                }
            )

        except HTTPException as exc:

            results.append(
                {
                    "lead_id": lead_id,
                    "website": None,
                    "website_status": "error",
                    "final_url": None,
                    "http_status": None,
                    "response_time_ms": None,
                    "error": exc.detail,
                }
            )

    return results