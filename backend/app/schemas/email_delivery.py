from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EmailDeliveryResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: UUID

    queue_id: UUID
    lead_id: UUID

    email_account_id: UUID | None

    recipient_email: str
    sender_email: str | None

    provider: str | None
    provider_message_id: str | None

    subject: str
    body_text: str | None

    status: str

    sent_at: datetime | None
    delivered_at: datetime | None
    opened_at: datetime | None
    clicked_at: datetime | None
    bounced_at: datetime | None
    complained_at: datetime | None
    unsubscribed_at: datetime | None
    failed_at: datetime | None

    bounce_type: str | None
    bounce_reason: str | None

    failure_reason: str | None

    complaint_type: str | None

    metadata_json: dict

    created_at: datetime
    updated_at: datetime


class EmailDeliveryListResponse(BaseModel):
    items: list[EmailDeliveryResponse]
    total: int


class EmailDeliveryEvent(BaseModel):
    status: str

    provider_message_id: str | None = None

    bounce_type: str | None = None

    bounce_reason: str | None = None

    complaint_type: str | None = None

    failure_reason: str | None = None

    metadata: dict = {}