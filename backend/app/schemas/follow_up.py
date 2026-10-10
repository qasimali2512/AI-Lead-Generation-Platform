from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FollowUpStepCreate(BaseModel):
    # Optional for dynamic sequences.  Kept for API compatibility with
    # manually prepared legacy sequences.
    draft_id: UUID | None = None

    delay_hours: int = Field(
        default=72,
        ge=1,
        le=720,
    )


class FollowUpSequenceCreate(BaseModel):
    initial_delivery_id: UUID

    steps: list[FollowUpStepCreate] = Field(
        min_length=1,
        max_length=10,
    )

    stop_on_reply: bool = True

    stop_on_bounce: bool = True

    stop_on_complaint: bool = True

    stop_on_unsubscribe: bool = True


class FollowUpSequenceStatusUpdate(BaseModel):
    status: str


class FollowUpStepResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: UUID

    sequence_id: UUID

    draft_id: UUID | None

    queue_id: UUID | None

    step_number: int

    delay_hours: int

    scheduled_at: datetime

    status: str

    sent_at: datetime | None

    skipped_at: datetime | None

    skip_reason: str | None

    created_at: datetime
    updated_at: datetime


class FollowUpSequenceResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: UUID

    lead_id: UUID

    initial_delivery_id: UUID

    status: str

    current_step: int

    max_steps: int

    stop_on_reply: bool

    stop_on_bounce: bool
    stop_on_complaint: bool
    stop_on_unsubscribe: bool

    stop_reason: str | None

    started_at: datetime

    completed_at: datetime | None

    stopped_at: datetime | None

    metadata_json: dict

    created_at: datetime
    updated_at: datetime


class FollowUpSequenceListResponse(BaseModel):
    items: list[FollowUpSequenceResponse]
    total: int


class EmailSuppressionCreate(BaseModel):
    email: str = Field(
        min_length=3,
        max_length=255,
    )

    reason: str = Field(
        min_length=1,
        max_length=50,
    )

    notes: str | None = None


class EmailSuppressionResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: UUID

    email: str

    reason: str

    source_delivery_id: UUID | None

    notes: str | None

    created_at: datetime


class EmailSuppressionListResponse(BaseModel):
    items: list[EmailSuppressionResponse]
    total: int
