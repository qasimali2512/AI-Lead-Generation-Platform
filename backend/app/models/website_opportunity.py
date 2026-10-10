from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class WebsiteOpportunity(Base):
    __tablename__ = "website_opportunities"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        # FK to auth.users is enforced at DB level only.
        # SQLAlchemy cannot resolve cross-schema Supabase auth tables,
        # so we intentionally omit the ForeignKey declaration here.
        nullable=False,
        index=True,
    )

    lead_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        # FK to public.leads.id enforced at DB level only.
        # SQLAlchemy schema resolution for cross-schema FK is skipped.
        nullable=False,
        index=True,
    )

    opportunity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="website_development",
    )

    industry: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    business_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    location_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    business_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    opportunity_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    recommended_solution: Mapped[str | None] = mapped_column(
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

    suggested_features: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    qualification_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pending",
    )

    opportunity_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="open",
    )

    analysis_json: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
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

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )