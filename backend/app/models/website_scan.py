from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class WebsiteScan(Base):
    __tablename__ = "website_scans"

    __table_args__ = (
        Index(
            "idx_website_scans_user_id",
            "user_id",
        ),
        Index(
            "idx_website_scans_lead_id",
            "lead_id",
        ),
        Index(
            "idx_website_scans_status",
            "scan_status",
        ),
        Index(
            "idx_website_scans_scanned_at",
            "scanned_at",
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

    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    final_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    http_status: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    response_time_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    page_size_bytes: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    content_type: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    title: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    meta_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    h1_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    h2_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    image_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    images_without_alt: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    internal_link_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    external_link_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    has_viewport: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    has_canonical: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    is_https: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    robots_txt_found: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    sitemap_found: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    html_language: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    scan_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="completed",
    )

    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    scanned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
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