from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ReplyIngestRequest(BaseModel):
    email_account_id: UUID | None = None

    provider: str = Field(
        min_length=2,
        max_length=30,
    )

    provider_thread_id: str | None = None

    provider_message_id: str = Field(
        min_length=1,
        max_length=500,
    )

    internet_message_id: str | None = None

    in_reply_to: str | None = None

    references_header: str | None = None

    lead_id: UUID | None = None

    from_email: str = Field(
        min_length=3,
        max_length=255,
    )

    to_emails: list[str] = Field(
        default_factory=list,
    )

    cc_emails: list[str] = Field(
        default_factory=list,
    )

    subject: str | None = None

    body_text: str | None = None

    received_at: datetime | None = None

    metadata: dict = Field(
        default_factory=dict,
    )


class EmailThreadResponse(BaseModel):
    id: UUID
    lead_id: UUID
    email_account_id: UUID | None
    provider: str
    provider_thread_id: str | None
    subject: str | None
    status: str
    last_direction: str | None
    last_message_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
    }


class EmailMessageResponse(BaseModel):
    id: UUID
    thread_id: UUID
    lead_id: UUID
    email_account_id: UUID | None
    provider: str
    provider_message_id: str
    internet_message_id: str | None
    direction: str
    from_email: str
    to_emails: list
    cc_emails: list
    subject: str | None
    body_text: str | None
    received_at: datetime | None
    sent_at: datetime | None
    created_at: datetime

    model_config = {
        "from_attributes": True,
    }


class ReplyIngestResponse(BaseModel):
    message_id: UUID
    thread_id: UUID
    lead_id: UUID
    sequence_stopped: bool
    stopped_sequence_count: int
    duplicate: bool