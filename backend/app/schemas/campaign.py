from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)

    selected_lead_ids: list[UUID] = Field(
        min_length=1,
        max_length=1000,
    )

    email_account_ids: list[UUID] = Field(
        min_length=1,
        max_length=50,
    )

    daily_limit: int = Field(
        default=30,
        ge=1,
        le=10000,
    )

    start_time: str = Field(
        default="09:00",
        min_length=5,
        max_length=5,
    )

    end_time: str = Field(
        default="17:00",
        min_length=5,
        max_length=5,
    )

    delay_min_minutes: int = Field(
        default=5,
        ge=0,
        le=1440,
    )

    delay_max_minutes: int = Field(
        default=15,
        ge=0,
        le=1440,
    )

    business_days_only: bool = True

    # Optional — agar set ho to campaign future mein schedule hogi
    # Format: ISO-8601 datetime string, e.g. "2026-10-15T09:00:00"
    scheduled_start_at: datetime | None = Field(
        default=None,
        description=(
            "Optional future datetime to schedule the campaign start. "
            "If None the campaign starts immediately."
        ),
    )

    follow_ups: list[dict] = Field(
        default_factory=list,
    )


class CampaignResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: UUID
    name: str
    status: str
    selected_lead_count: int
    email_account_ids: list
    sending_settings: dict
    follow_up_settings: list
    metadata_json: dict
    last_error: str | None
    started_at: datetime | None
    paused_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CampaignListResponse(BaseModel):
    items: list[CampaignResponse]
    total: int


class CampaignLeadResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: UUID
    campaign_id: UUID
    lead_id: UUID
    email_account_id: UUID | None
    ai_email_draft_id: UUID | None
    email_queue_id: UUID | None
    status: str
    scheduled_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class CampaignDetailResponse(CampaignResponse):
    leads: list[CampaignLeadResponse]
