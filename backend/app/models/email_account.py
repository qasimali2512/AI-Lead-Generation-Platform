import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EmailAccount(Base):
    __tablename__ = "email_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    provider: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    display_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    provider_account_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    access_token_encrypted: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    refresh_token_encrypted: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    scopes: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    provider_metadata: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    daily_send_limit: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=50,
    )

    sent_today: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    last_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    bounce_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    complaint_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    unsubscribe_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="active",
    )

    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    last_error_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
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