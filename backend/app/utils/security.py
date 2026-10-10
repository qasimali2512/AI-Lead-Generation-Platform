from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


def is_private_or_unsafe_host(hostname: str) -> bool:
    """
    Returns True when a hostname resolves to a private,
    loopback, link-local, multicast, reserved, or otherwise
    unsafe IP address.
    """

    if not hostname:
        return True

    hostname = hostname.strip().lower().rstrip(".")

    blocked_hostnames = {
        "localhost",
        "localhost.localdomain",
        "ip6-localhost",
        "ip6-loopback",
        "ip6-allnodes",
        "ip6-allrouters",
    }

    if hostname in blocked_hostnames:
        return True

    try:
        ip = ipaddress.ip_address(hostname)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        )
    except ValueError:
        pass

    try:
        addresses = socket.getaddrinfo(
            hostname,
            None,
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror:
        return True

    for address in addresses:
        ip_text = address[4][0]

        try:
            ip = ipaddress.ip_address(ip_text)
        except ValueError:
            return True

        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return True

    return False


def validate_external_url(url: str) -> bool:
    """
    Validates a URL before the application makes an outbound
    HTTP request.

    Only HTTP and HTTPS are allowed.
    """

    if not url:
        return False

    try:
        parsed = urlparse(url)
    except ValueError:
        return False

    if parsed.scheme not in {"http", "https"}:
        return False

    if not parsed.hostname:
        return False

    return not is_private_or_unsafe_host(parsed.hostname)


def sanitize_log_value(value: object, max_length: int = 500) -> str:
    """
    Prevent sensitive or excessively large values from
    accidentally appearing in logs.
    """

    if value is None:
        return ""

    text = str(value)

    sensitive_headers = (
        "authorization",
        "bearer ",
        "access_token",
        "refresh_token",
        "api_key",
        "password",
        "secret",
    )

    lowered = text.lower()

    if any(item in lowered for item in sensitive_headers):
        return "[REDACTED]"

    return text[:max_length]


def mask_email(email: str | None) -> str | None:
    """
    Masks an email address for logs.
    """

    if not email:
        return None

    email = email.strip()

    if "@" not in email:
        return "***"

    local, domain = email.split("@", 1)

    if len(local) <= 2:
        masked_local = "*" * len(local)
    else:
        masked_local = f"{local[0]}***{local[-1]}"

    return f"{masked_local}@{domain}"