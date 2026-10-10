from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class NotificationResponse(BaseModel):
    id: UUID
    title: str
    message: str
    notification_type: str
    is_read: bool
    action_url: str | None = None
    created_at: datetime
    read_at: datetime | None = None

    model_config = {
        "from_attributes": True,
    }


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    unread_count: int
    skip: int
    limit: int


class CreateNotificationRequest(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=200,
    )

    message: str = Field(
        min_length=1,
        max_length=5000,
    )

    notification_type: str = Field(
        default="info",
        max_length=50,
    )

    action_url: str | None = Field(
        default=None,
        max_length=500,
    )


class NotificationActionResponse(BaseModel):
    success: bool
    message: str