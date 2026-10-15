from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
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
    countries: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    location_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_run_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )