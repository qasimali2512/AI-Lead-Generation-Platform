from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security-related HTTP response headers.
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )

        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Prevents excessively large HTTP request bodies.

    Default limit: 10 MB.
    """

    def __init__(self, app, max_body_size: int = 10 * 1024 * 1024):
        super().__init__(app)
        self.max_body_size = max_body_size

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")

        if content_length:
            try:
                content_length_int = int(content_length)
            except ValueError:
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "message": "Invalid Content-Length header.",
                        "errors": [],
                    },
                )

            if content_length_int > self.max_body_size:
                return JSONResponse(
                    status_code=413,
                    content={
                        "success": False,
                        "message": "Request body is too large.",
                        "errors": [],
                    },
                )

        return await call_next(request)


class InMemoryRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Lightweight development rate limiter.

    This is intentionally process-local.

    Production AWS deployments should use Redis-backed
    distributed rate limiting.
    """

    def __init__(
        self,
        app,
        requests_per_window: int = 120,
        window_seconds: int = 60,
    ):
        super().__init__(app)

        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds

        self.requests: dict[str, deque[float]] = defaultdict(deque)

    def _get_client_key(self, request: Request) -> str:
        client = request.client

        if client is None:
            return "unknown"

        return client.host

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Do not rate-limit health checks.
        if path in {"/", "/health", "/api/health"}:
            return await call_next(request)

        client_key = self._get_client_key(request)

        now = time.monotonic()
        request_times = self.requests[client_key]

        while request_times:
            if now - request_times[0] <= self.window_seconds:
                break

            request_times.popleft()

        if len(request_times) >= self.requests_per_window:
            return JSONResponse(
                status_code=429,
                headers={
                    "Retry-After": str(self.window_seconds),
                },
                content={
                    "success": False,
                    "message": "Too many requests. Please try again later.",
                    "errors": [],
                },
            )

        request_times.append(now)

        return await call_next(request)