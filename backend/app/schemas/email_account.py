from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EmailAccountCreate(BaseModel):
    provider: str = Field(
        min_length=1,
        max_length=30,
    )

    email: str = Field(
        min_length=3,
        max_length=255,
    )

    display_name: str | None = Field(
        default=None,
        max_length=255,
    )

    provider_account_id: str | None = Field(
        default=None,
        max_length=255,
    )

    access_token: str | None = None

    refresh_token: str | None = None

    token_expires_at: datetime | None = None

    scopes: list[str] = Field(
        default_factory=list
    )

    provider_metadata: dict = Field(
        default_factory=dict
    )

    daily_send_limit: int = Field(
        default=50,
        ge=1,
        le=10000,
    )


class EmailAccountUpdate(BaseModel):
    display_name: str | None = Field(
        default=None,
        max_length=255,
    )

    daily_send_limit: int | None = Field(
        default=None,
        ge=1,
        le=10000,
    )


class EmailAccountStatusUpdate(BaseModel):
    status: str


class EmailAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider: str
    email: str
    display_name: str | None

    provider_account_id: str | None

    token_expires_at: datetime | None

    scopes: list[str]
    provider_metadata: dict

    daily_send_limit: int
    sent_today: int

    last_sent_at: datetime | None

    bounce_count: int
    complaint_count: int
    unsubscribe_count: int

    status: str

    last_error: str | None
    last_error_at: datetime | None

    created_at: datetime
    updated_at: datetime


class EmailAccountListResponse(BaseModel):
    items: list[EmailAccountResponse]
    total: int