from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EmailQueueCreate(BaseModel):
    draft_id: UUID

    email_account_id: UUID | None = None

    scheduled_at: datetime | None = None

    priority: int = Field(
        default=100,
        ge=1,
        le=1000,
    )

    queue_type: str = Field(
        default="initial",
        max_length=30,
    )


class EmailQueueStatusUpdate(BaseModel):
    status: str = Field(
        ...,
        min_length=1,
        max_length=30,
    )


class EmailQueueResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID

    user_id: UUID

    lead_id: UUID

    draft_id: UUID

    email_account_id: UUID | None

    recipient_email: str

    subject: str

    body_text: str

    queue_type: str

    status: str

    priority: int

    scheduled_at: datetime

    started_at: datetime | None

    sent_at: datetime | None

    attempt_count: int

    max_attempts: int

    last_attempt_at: datetime | None

    next_retry_at: datetime | None

    provider_message_id: str | None

    last_error: str | None

    last_error_at: datetime | None

    metadata_json: dict = Field(
        default_factory=dict,
        alias="metadata_json",
    )

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class EmailQueueListResponse(BaseModel):
    items: list[EmailQueueResponse]

    total: int