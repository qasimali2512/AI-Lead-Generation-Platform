from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class QualificationFactor(BaseModel):
    name: str

    points: int

    reason: str


class LeadQualificationResponse(BaseModel):
    success: bool

    qualification_id: UUID

    lead_id: UUID

    website_score: int

    business_score: int

    opportunity_score: int

    contact_score: int

    total_score: int

    qualification_level: str

    outreach_readiness: str

    qualification_reason: str | None = None

    recommended_approach: str | None = None

    qualification_factors: list[QualificationFactor] = Field(
        default_factory=list
    )

    qualification_json: dict = Field(
        default_factory=dict
    )

    created_at: datetime


class LeadQualificationListResponse(BaseModel):
    success: bool

    total: int

    page: int

    page_size: int

    qualifications: list[LeadQualificationResponse]


class LeadQualificationRefreshRequest(BaseModel):
    force: bool = False