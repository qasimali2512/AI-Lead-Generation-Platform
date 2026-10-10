from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AIAnalysis(Base):
    __tablename__ = "ai_analyses"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "auth.users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    lead_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "public.leads.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    scan_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "public.website_scans.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
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

    business_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    website_assessment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    opportunity_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    sales_angle: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    personalization_points: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    priority_issues: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    analysis_json: Mapped[dict] = mapped_column(
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