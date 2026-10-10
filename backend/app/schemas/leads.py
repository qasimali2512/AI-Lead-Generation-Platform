from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class LeadResponse(BaseModel):
    id: UUID

    user_id: UUID

    source: str
    source_id: str

    name: str

    industry: str | None = None

    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None

    latitude: float | None = None
    longitude: float | None = None

    phone: str | None = None
    email: str | None = None
    website: str | None = None

    website_status: str

    osm_type: str | None = None
    osm_id: int | None = None

    lead_status: str
    qualification_status: str

    notes: str | None = None

    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
    }


class LeadListResponse(BaseModel):
    success: bool
    total: int
    page: int
    page_size: int
    leads: list[LeadResponse]


class LeadStatusUpdateRequest(BaseModel):
    lead_status: str = Field(
        min_length=1,
        max_length=30,
    )

    notes: str | None = Field(
        default=None,
        max_length=5000,
    )


class LeadDeleteResponse(BaseModel):
    success: bool
    message: str