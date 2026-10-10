from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LeadQualification(Base):
    __tablename__ = "lead_qualifications"

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

    website_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    business_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    opportunity_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    contact_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    total_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        index=True,
    )

    qualification_level: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="unqualified",
        index=True,
    )

    outreach_readiness: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="not_ready",
        index=True,
    )

    qualification_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    recommended_approach: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    qualification_factors: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    qualification_json: Mapped[dict] = mapped_column(
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