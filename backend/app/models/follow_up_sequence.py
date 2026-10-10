import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FollowUpSequence(Base):
    __tablename__ = "follow_up_sequences"

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

    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    initial_delivery_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="active",
        index=True,
    )

    current_step: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    max_steps: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
    )

    stop_on_reply: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    stop_on_bounce: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    stop_on_complaint: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    stop_on_unsubscribe: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    stop_reason: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    stopped_at: Mapped[datetime | None] = mapped_column(
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
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )