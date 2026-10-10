from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class WebsiteCheckResponse(BaseModel):
    success: bool

    lead_id: UUID

    website: str | None = None

    website_status: str

    final_url: str | None = None

    http_status: int | None = None

    response_time_ms: int | None = None

    checked_at: datetime | None = None

    error: str | None = None


class WebsiteBulkCheckRequest(BaseModel):
    lead_ids: list[UUID] = Field(
        min_length=1,
        max_length=25,
    )


class WebsiteBulkCheckResult(BaseModel):
    lead_id: UUID
    website_status: str
    website: str | None = None
    final_url: str | None = None
    http_status: int | None = None
    response_time_ms: int | None = None
    error: str | None = None


class WebsiteBulkCheckResponse(BaseModel):
    success: bool
    total_requested: int
    total_processed: int
    results: list[WebsiteBulkCheckResult]