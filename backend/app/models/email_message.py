from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EmailMessage(Base):
    __tablename__ = "email_messages"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
    )

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
    )

    thread_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
    )

    lead_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
    )

    email_account_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
    )

    provider: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    provider_message_id: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    internet_message_id: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    in_reply_to: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    references_header: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    direction: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    from_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    to_emails: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    cc_emails: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    subject: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    body_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    received_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )