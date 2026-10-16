"""
Business ki website se email nikalna (contact page / mailto links).

Safety:
  * Private / local IP wali websites block hoti hain (SSRF protection).
  * Redirects har step par dobara check hote hain.
  * Page size aur waqt ki hadd hai.
"""
from __future__ import annotations

import asyncio
import ipaddress
import re
import socket
import time
import urllib.parse

import httpx
from bs4 import BeautifulSoup

from app.schemas.discovery import BusinessDiscoveryResult

PAGE_TIMEOUT = 8.0
PAGE_MAX_BYTES = 800_000
ENRICH_CHUNK = 24
ENRICH_CONCURRENCY = 8
PER_SITE_TIMEOUT = 30.0

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

EMAIL_RE = re.compile(
    r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}"
)
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


def valid_email(value: str) -> bool:
    value = value.lower()
    if len(value) > 254 or not EMAIL_RE.fullmatch(value):
        return False
    if value.endswith(BAD_EMAIL_SUFFIXES):
        return False
    return not any(part in value for part in BAD_EMAIL_PARTS)


def extract_emails(html: str, site_host: str) -> list[str]:
    found: list[str] = []

    soup = BeautifulSoup(html, "html.parser")
    for a in soup.select("a[href^='mailto:' i]"):
        href = urllib.parse.unquote(a.get("href", ""))[7:].split("?")[0]
        for part in re.split(r"[;,]", href):
            part = part.strip().lower()
            if part and valid_email(part) and part not in found:
                found.append(part)

    for match in EMAIL_RE.findall(soup.get_text(" ")):
        match = match.lower().strip(".")
        if valid_email(match) and match not in found:
            found.append(match)

    def same_domain(email: str) -> bool:
        domain = email.split("@", 1)[1]
        return bool(site_host) and (
            domain == site_host or domain.endswith("." + site_host)
        )

    found.sort(key=lambda e: 0 if same_domain(e) else 1)
    return found


async def find_email(client: httpx.AsyncClient, website: str) -> str | None:
    base = website if website.startswith(("http://", "https://")) else f"https://{website}"
    host = (urllib.parse.urlparse(base).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]

    for path in ("", "/contact", "/contact-us", "/about"):
        url = urllib.parse.urljoin(base, path) if path else base
        html = await _safe_get(client, url)
        if not html:
            continue
        emails = extract_emails(html, host)
        if emails:
            return emails[0]
    return None


async def enrich_emails(
    candidates: list[BusinessDiscoveryResult],
    seen_emails: set[str],
    target: int,
    deadline: float | None = None,
) -> list[BusinessDiscoveryResult]:
    """Websites se email nikalo jab tak `target` na mil jaye ya waqt khatam."""
    results: list[BusinessDiscoveryResult] = []
    semaphore = asyncio.Semaphore(ENRICH_CONCURRENCY)

    async with httpx.AsyncClient(
        timeout=PAGE_TIMEOUT,
        headers={"User-Agent": BROWSER_UA},
        follow_redirects=False,
    ) as client:

        async def work(business: BusinessDiscoveryResult):
            async with semaphore:
                email = await asyncio.wait_for(
                    find_email(client, business.website or ""),
                    timeout=PER_SITE_TIMEOUT,
                )
            return business, email

        for i in range(0, len(candidates), ENRICH_CHUNK):
            if deadline is not None and time.monotonic() > deadline - PER_SITE_TIMEOUT:
                break

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