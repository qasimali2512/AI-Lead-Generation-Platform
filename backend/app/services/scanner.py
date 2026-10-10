from __future__ import annotations

import ipaddress
import socket
import time
from urllib.parse import urljoin, urlparse, urlunparse
from uuid import UUID

import httpx
from bs4 import BeautifulSoup
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.models.website_scan import WebsiteScan
from app.services.leads import get_user_lead


REQUEST_TIMEOUT = httpx.Timeout(
    connect=8.0,
    read=15.0,
    write=8.0,
    pool=8.0,
)

MAX_REDIRECTS = 5

MAX_HTML_BYTES = 5 * 1024 * 1024

USER_AGENT = (
    "AI-Lead-Generation-Platform/1.0 "
    "(website scanner)"
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
            "Website URL does not contain a hostname."
        )

    if parsed.username or parsed.password:
        raise ValueError(
            "URLs containing credentials are not allowed."
        )

    return urlunparse(
        parsed._replace(
            fragment=""
        )
    )


# ---------------------------------------------------------
# SSRF protection
# ---------------------------------------------------------

def is_blocked_ip(ip):
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

    seen = set()

    for address in addresses:

        ip_value = address[4][0]

        if ip_value in seen:
            continue

        seen.add(ip_value)

        try:
            ip = ipaddress.ip_address(
                ip_value
            )
        except ValueError as exc:
            raise ValueError(
                "Invalid resolved IP address."
            ) from exc

        if is_blocked_ip(ip):
            raise ValueError(
                "Website resolves to a private or local IP address."
            )


# ---------------------------------------------------------
# Safe HTTP response reader
# ---------------------------------------------------------

async def fetch_html(
    url: str,
) -> dict:

    normalized_url = normalize_url(
        url
    )

    parsed = urlparse(
        normalized_url
    )

    validate_hostname(
        parsed.hostname
    )

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
                (
                    time.perf_counter()
                    - started_at
                )
                * 1000
            )

            final_url = str(
                response.url
            )

            final_hostname = (
                urlparse(
                    final_url
                ).hostname
            )

            if final_hostname:
                validate_hostname(
                    final_hostname
                )

            content_type = (
                response.headers.get(
                    "content-type"
                )
            )

            content_length = len(
                response.content
            )

            if content_length > MAX_HTML_BYTES:
                raise ValueError(
                    "Website HTML response is too large to scan."
                )

            return {
                "response": response,
                "url": normalized_url,
                "final_url": final_url,
                "http_status": response.status_code,
                "response_time_ms": elapsed_ms,
                "content_type": content_type,
                "content": response.content,
            }

    except httpx.TooManyRedirects as exc:
        raise ValueError(
            "Website has too many redirects."
        ) from exc

    except httpx.TimeoutException as exc:
        raise ValueError(
            "Website request timed out."
        ) from exc

    except httpx.RequestError as exc:
        raise ValueError(
            "Website request failed."
        ) from exc


# ---------------------------------------------------------
# HTML extraction
# ---------------------------------------------------------

def extract_page_data(
    html: bytes,
    final_url: str,
) -> dict:

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    title_tag = soup.find(
        "title"
    )

    title = (
        title_tag.get_text(
            " ",
            strip=True,
        )
        if title_tag
        else None
    )

    description_tag = soup.find(
        "meta",
        attrs={
            "name": lambda value: (
                isinstance(value, str)
                and value.lower()
                == "description"
            )
        },
    )

    meta_description = None

    if description_tag:
        meta_description = (
            description_tag.get(
                "content"
            )
        )

        if meta_description:
            meta_description = (
                meta_description.strip()
            )

    h1_count = len(
        soup.find_all("h1")
    )

    h2_count = len(
        soup.find_all("h2")
    )

    images = soup.find_all(
        "img"
    )

    image_count = len(images)

    images_without_alt = 0

    for image in images:

        alt = image.get(
            "alt"
        )

        if (
            alt is None
            or not str(alt).strip()
        ):
            images_without_alt += 1

    parsed_final = urlparse(
        final_url
    )

    base_domain = (
        parsed_final.hostname
        or ""
    ).lower()

    internal_link_count = 0
    external_link_count = 0

    for link in soup.find_all(
        "a",
        href=True,
    ):

        href = str(
            link.get("href")
        ).strip()

        if not href:
            continue

        if href.startswith(
            (
                "#",
                "mailto:",
                "tel:",
                "javascript:",
            )
        ):
            continue

        absolute_url = urljoin(
            final_url,
            href,
        )

        parsed_link = urlparse(
            absolute_url
        )

        link_domain = (
            parsed_link.hostname
            or ""
        ).lower()

        if not link_domain:
            continue

        if (
            link_domain == base_domain
            or link_domain.endswith(
                f".{base_domain}"
            )
        ):
            internal_link_count += 1
        else:
            external_link_count += 1

    viewport = soup.find(
        "meta",
        attrs={
            "name": lambda value: (
                isinstance(value, str)
                and value.lower()
                == "viewport"
            )
        },
    )

    has_viewport = (
        viewport is not None
    )

    canonical = soup.find(
        "link",
        attrs={
            "rel": lambda value: (
                (
                    isinstance(value, list)
                    and any(
                        str(item).lower()
                        == "canonical"
                        for item in value
                    )
                )
                or (
                    isinstance(value, str)
                    and value.lower()
                    == "canonical"
                )
            )
        },
    )

    has_canonical = (
        canonical is not None
    )

    html_tag = soup.find(
        "html"
    )

    html_language = None

    if html_tag:
        language = html_tag.get(
            "lang"
        )

        if language:
            html_language = (
                str(language)
                .strip()
            )

    return {
        "title": title,
        "meta_description": meta_description,
        "h1_count": h1_count,
        "h2_count": h2_count,
        "image_count": image_count,
        "images_without_alt": images_without_alt,
        "internal_link_count": internal_link_count,
        "external_link_count": external_link_count,
        "has_viewport": has_viewport,
        "has_canonical": has_canonical,
        "html_language": html_language,
    }


# ---------------------------------------------------------
# Robots and sitemap
# ---------------------------------------------------------

async def check_supporting_files(
    final_url: str,
) -> tuple[bool, bool]:

    parsed = urlparse(
        final_url
    )

    origin = urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            "",
            "",
            "",
            "",
        )
    )

    headers = {
        "User-Agent": USER_AGENT,
    }

    robots_found = False
    sitemap_found = False

    try:
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
            max_redirects=MAX_REDIRECTS,
            headers=headers,
        ) as client:

            robots_url = urljoin(
                f"{origin}/",
                "robots.txt",
            )

            try:
                robots_response = (
                    await client.get(
                        robots_url
                    )
                )

                robots_found = (
                    200
                    <= robots_response.status_code
                    < 300
                )
            except httpx.HTTPError:
                robots_found = False

            sitemap_url = urljoin(
                f"{origin}/",
                "sitemap.xml",
            )

            try:
                sitemap_response = (
                    await client.get(
                        sitemap_url
                    )
                )

                sitemap_found = (
                    200
                    <= sitemap_response.status_code
                    < 300
                )
            except httpx.HTTPError:
                sitemap_found = False

    except httpx.HTTPError:
        pass

    return (
        robots_found,
        sitemap_found,
    )


# ---------------------------------------------------------
# Existing scan lookup
# ---------------------------------------------------------

def get_latest_scan(
    db: Session,
    user_id: UUID,
    lead_id: UUID,
) -> WebsiteScan | None:

    return db.scalar(
        select(WebsiteScan)
        .where(
            WebsiteScan.user_id == user_id,
            WebsiteScan.lead_id == lead_id,
        )
        .order_by(
            WebsiteScan.scanned_at.desc()
        )
        .limit(1)
    )


# ---------------------------------------------------------
# Persist scan
# ---------------------------------------------------------

def save_scan(
    db: Session,
    scan_data: dict,
) -> WebsiteScan:

    scan = WebsiteScan(
        **scan_data
    )

    db.add(scan)

    try:
        db.commit()
        db.refresh(scan)

    except Exception:
        db.rollback()
        raise

    return scan


# ---------------------------------------------------------
# Main scanner
# ---------------------------------------------------------

async def scan_lead_website(
    db: Session,
    user_id: UUID,
    lead_id: UUID,
    force_rescan: bool = False,
) -> WebsiteScan:

    lead = get_user_lead(
        db=db,
        user_id=user_id,
        lead_id=lead_id,
    )

    if not lead.website:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "This lead does not have a website URL."
            ),
        )

    if not force_rescan:

        latest_scan = get_latest_scan(
            db=db,
            user_id=user_id,
            lead_id=lead_id,
        )

        if latest_scan:
            return latest_scan

    try:

        fetched = await fetch_html(
            lead.website
        )

        response = fetched[
            "response"
        ]

        final_url = fetched[
            "final_url"
        ]

        content = fetched[
            "content"
        ]

        content_type = (
            fetched[
                "content_type"
            ]
            or ""
        )

        # Only parse HTML-like responses.
        if (
            "html"
            not in content_type.lower()
        ):
            raise ValueError(
                "Website response is not HTML."
            )

        page_data = extract_page_data(
            html=content,
            final_url=final_url,
        )

        (
            robots_found,
            sitemap_found,
        ) = await check_supporting_files(
            final_url
        )

        scan_data = {
            "user_id": user_id,
            "lead_id": lead_id,

            "url": fetched["url"],
            "final_url": final_url,

            "http_status": fetched[
                "http_status"
            ],

            "response_time_ms": fetched[
                "response_time_ms"
            ],

            "page_size_bytes": len(
                content
            ),

            "content_type": content_type,

            "title": page_data[
                "title"
            ],

            "meta_description": page_data[
                "meta_description"
            ],

            "h1_count": page_data[
                "h1_count"
            ],

            "h2_count": page_data[
                "h2_count"
            ],

            "image_count": page_data[
                "image_count"
            ],

            "images_without_alt": page_data[
                "images_without_alt"
            ],

            "internal_link_count": page_data[
                "internal_link_count"
            ],

            "external_link_count": page_data[
                "external_link_count"
            ],

            "has_viewport": page_data[
                "has_viewport"
            ],

            "has_canonical": page_data[
                "has_canonical"
            ],

            "is_https": (
                urlparse(
                    final_url
                ).scheme.lower()
                == "https"
            ),

            "robots_txt_found": (
                robots_found
            ),

            "sitemap_found": (
                sitemap_found
            ),

            "html_language": page_data[
                "html_language"
            ],

            "scan_status": "completed",

            "error": None,
        }

    except Exception as exc:

        scan_data = {
            "user_id": user_id,
            "lead_id": lead_id,

            "url": lead.website,

            "final_url": None,

            "http_status": None,

            "response_time_ms": None,

            "page_size_bytes": None,

            "content_type": None,

            "title": None,

            "meta_description": None,

            "h1_count": 0,

            "h2_count": 0,

            "image_count": 0,

            "images_without_alt": 0,

            "internal_link_count": 0,

            "external_link_count": 0,

            "has_viewport": False,

            "has_canonical": False,

            "is_https": (
                lead.website
                .lower()
                .startswith("https://")
            ),

            "robots_txt_found": False,

            "sitemap_found": False,

            "html_language": None,

            "scan_status": "failed",

            "error": str(exc),
        }

    return save_scan(
        db=db,
        scan_data=scan_data,
    )