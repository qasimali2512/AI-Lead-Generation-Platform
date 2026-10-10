from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class BrandSettings(Base):
    __tablename__ = "brand_settings"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        unique=True,
        index=True,
    )

    agency_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        default="SoftPeak Technologies",
    )

    website: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    logo_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    primary_color: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="#1f6b4f",
    )

    secondary_color: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="#c49a4a",
    )

    sender_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    sender_role: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    phone: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    address: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    booking_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    unsubscribe_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )