from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class WebsiteOpportunityResponse(BaseModel):
    success: bool

    opportunity_id: UUID

    lead_id: UUID

    opportunity_type: str

    industry: str | None = None

    business_name: str

    location_summary: str | None = None

    business_summary: str | None = None

    opportunity_summary: str | None = None

    recommended_solution: str | None = None

    sales_angle: str | None = None

    personalization_points: list[str] = Field(
        default_factory=list
    )

    suggested_features: list[str] = Field(
        default_factory=list
    )

    qualification_status: str

    # Derived display field: "high" | "medium" | "low"
    qualification_level: str = "medium"

    opportunity_status: str

    # Enriched from the Lead row
    email: str | None = None
    phone: str | None = None

    analysis_json: dict = Field(
        default_factory=dict
    )

    provider: str

    model: str

    prompt_version: str

    created_at: datetime


class WebsiteOpportunityListResponse(BaseModel):
    success: bool

    total: int

    opportunities: list[WebsiteOpportunityResponse]


class WebsiteOpportunityStatusUpdateRequest(BaseModel):
    opportunity_status: str = Field(
        min_length=1,
        max_length=30,
    )

    qualification_status: str | None = Field(
        default=None,
        max_length=30,
    )