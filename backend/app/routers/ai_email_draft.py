import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AIEmailDraft(Base):
    __tablename__ = "ai_email_drafts"

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

    ai_analysis_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    website_opportunity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    qualification_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="cloudflare",
    )

    model: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    prompt_version: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="1.0",
    )

    email_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="initial_outreach",
    )

    subject: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    body_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    personalization_points: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    source_evidence: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    call_to_action: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    generation_context: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="draft",
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