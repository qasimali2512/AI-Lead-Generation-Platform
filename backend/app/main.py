from __future__ import annotations

import logging
import os
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers.campaigns import router as campaigns_router
from app.routers import settings as settings_router
from app.middleware.error_handlers import register_error_handlers
from app.middleware.security import (
    InMemoryRateLimitMiddleware,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
from app.routers import (
    ai_analysis,
    ai_email,
    analytics,
    api_info,
    auth,
    discovery,
    email_accounts,
    email_delivery,
    email_queue,
    follow_up,
    notifications,
    health,
    issues,
    leads,
    qualification,
    replies,
    scanner,
    users,
    website,
    website_opportunities,
)


logger = logging.getLogger("ai-lead-api")


def _scheduler_loop(stop_event: threading.Event) -> None:
    """
    Background loop: har SCHEDULER_INTERVAL_SECONDS baad due emails
    (scheduled/pending) khud send karta hai. Alag command chalane ki
    zarurat nahi.
    """
    from app.workers.scheduler_runner import SchedulerRunner

    runner = SchedulerRunner()

    logger.info(
        "Auto scheduler started (interval=%ss).",
        settings.scheduler_interval_seconds,
    )

    while not stop_event.is_set():
        try:
            runner.run_once()
        except Exception:
            logger.exception("Auto scheduler cycle crashed.")

        stop_event.wait(settings.scheduler_interval_seconds)

    logger.info("Auto scheduler stopped.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_event = threading.Event()
    thread = None

    # .env mein RUN_SCHEDULER=false kar dein to auto scheduler band ho jaye
    # (jab alag se scheduler_runner chalana ho).
    if os.getenv("RUN_SCHEDULER", "true").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }:
        thread = threading.Thread(
            target=_scheduler_loop,
            args=(stop_event,),
            name="auto-scheduler",
            daemon=True,
        )
        thread.start()

    try:
        yield
    finally:
        stop_event.set()

        if thread:
            thread.join(timeout=5)


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "AI-powered lead generation, website analysis, "
        "qualification, and outreach automation platform."
    ),
    lifespan=lifespan,
)


# ------------------------------------------------------------------
# Error handling
# ------------------------------------------------------------------

register_error_handlers(app)


# ------------------------------------------------------------------
# Security middleware
# ------------------------------------------------------------------

app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    RequestSizeLimitMiddleware,
    max_body_size=10 * 1024 * 1024,
)

app.add_middleware(
    InMemoryRateLimitMiddleware,
    requests_per_window=120,
    window_seconds=60,
)


# ------------------------------------------------------------------
# CORS
# ------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With",
        "Cache-Control",
    ],
    # SSE ke liye browser ko yeh headers expose karne chahiye
    expose_headers=[
        "Content-Type",
        "Cache-Control",
        "X-Accel-Buffering",
    ],
)


# ------------------------------------------------------------------
# Root
# ------------------------------------------------------------------

@app.get("/")
def root():
    return {
        "success": True,
        "message": "AI Lead Generation & Outreach Platform API",
        "version": settings.app_version,
        "environment": settings.environment,
        "api_prefix": settings.api_prefix,
        "status": "running",
    }


# ------------------------------------------------------------------
# Routers
# ------------------------------------------------------------------

app.include_router(
    health.router,
    prefix=settings.api_prefix,
)

app.include_router(
    auth.router,
    prefix=settings.api_prefix,
)

app.include_router(
    users.router,
    prefix=settings.api_prefix,
)

app.include_router(
    discovery.router,
    prefix=settings.api_prefix,
)

app.include_router(
    leads.router,
    prefix=settings.api_prefix,
)

app.include_router(
    website.router,
    prefix=settings.api_prefix,
)

app.include_router(
    scanner.router,
    prefix=settings.api_prefix,
)

app.include_router(
    issues.router,
    prefix=settings.api_prefix,
)

app.include_router(
    ai_analysis.router,
    prefix=settings.api_prefix,
)
app.include_router(
    campaigns_router,
    prefix=settings.api_prefix,
)

app.include_router(
    website_opportunities.router,
    prefix=settings.api_prefix,
)
app.include_router(
    settings_router.router,
    prefix=settings.api_prefix,
)

app.include_router(
    qualification.router,
    prefix=settings.api_prefix,
)

app.include_router(
    email_accounts.router,
    prefix=settings.api_prefix,
)
app.include_router(
    notifications.router,
    prefix=settings.api_prefix,
)
app.include_router(
    ai_email.router,
    prefix=settings.api_prefix,
)

app.include_router(
    email_queue.router,
    prefix=settings.api_prefix,
)

app.include_router(
    email_delivery.router,
    prefix=settings.api_prefix,
)

app.include_router(
    follow_up.router,
    prefix=settings.api_prefix,
)

app.include_router(
    replies.router,
    prefix=settings.api_prefix,
)

app.include_router(
    analytics.router,
    prefix=settings.api_prefix,
)

# api_info already contains /api prefix.
app.include_router(api_info.router)