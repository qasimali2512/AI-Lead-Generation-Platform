from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AutoDiscoverySettings(Base):
    __tablename__ = "auto_discovery_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, unique=True
    )

    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    batch_size: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    require_email: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    require_website: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    run_every_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)

    # "big" | "medium" | "small" | "mix"  (mix = 3 chhote : 1 bara)
    city_size: Mapped[str] = mapped_column(String(10), nullable=False, default="mix")
    # ISO country codes, e.g. ["US", "GB"].  Khali = poori duniya.
    countries: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # "mix" pattern mein ab kis number par hain
    mix_position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_run_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # =========================================================
    # Auto-Campaign Automation
    # =========================================================

    # Jab auto-discovery leads dhunde aur threshold se zyada opportunities
    # hon to khud campaign banao aur send shuru karo
    auto_campaign_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    auto_campaign_paused: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    # Minimum opportunity % threshold (0-100). Agar found leads mein
    # itni ya zyada % opportunities hain, campaign auto-create hoga.
    auto_campaign_opportunity_threshold: Mapped[float] = mapped_column(
        Float, nullable=False, default=30.0
    )

    # Per-day email limit for auto-created campaigns
    auto_campaign_daily_limit: Mapped[int] = mapped_column(
        Integer, nullable=False, default=50
    )

    # Email accounts to use for auto campaigns (list of UUID strings)
    auto_campaign_email_account_ids: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list
    )

    # Sending window for auto campaigns
    auto_campaign_start_time: Mapped[str] = mapped_column(
        String(5), nullable=False, default="09:00"
    )
    auto_campaign_end_time: Mapped[str] = mapped_column(
        String(5), nullable=False, default="17:00"
    )

    # Track when the last auto-campaign was created (to avoid duplicates per day)
    auto_campaign_last_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Total auto-campaigns created so far
    auto_campaigns_created: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class AutoDiscoveryVisitedCity(Base):
    """Kaun sa shehr kis industry ke liye ho chuka -- dobara na ho."""

    __tablename__ = "auto_discovery_visited_cities"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    industry_key: Mapped[str] = mapped_column(String(100), primary_key=True)
    geoname_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    visited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )