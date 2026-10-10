from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Double,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Lead(Base):
    __tablename__ = "leads"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "source",
            "source_id",
            name="uq_leads_user_source",
        ),
        Index(
            "idx_leads_user_id",
            "user_id",
        ),
        Index(
            "idx_leads_industry",
            "user_id",
            "industry",
        ),
        Index(
            "idx_leads_city",
            "user_id",
            "city",
        ),
        Index(
            "idx_leads_website_status",
            "user_id",
            "website_status",
        ),
        Index(
            "idx_leads_status",
            "user_id",
            "lead_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="openstreetmap",
    )

    source_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    industry: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    address: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    state: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    country: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    latitude: Mapped[float | None] = mapped_column(
        Double,
        nullable=True,
    )

    longitude: Mapped[float | None] = mapped_column(
        Double,
        nullable=True,
    )

    phone: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    website: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    website_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="unknown",
    )

    website_final_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    website_http_status: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    website_response_time_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    website_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    website_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    osm_type: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    osm_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    lead_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="new",
    )

    qualification_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pending",
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )