from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AIPriorityIssue(BaseModel):
    issue_code: str

    title: str

    severity: str

    evidence: str | None = None

    business_impact: str

    recommended_action: str


class AIAnalysisData(BaseModel):
    business_summary: str

    website_assessment: str

    opportunity_summary: str

    sales_angle: str

    personalization_points: list[str] = Field(
        default_factory=list
    )

    priority_issues: list[AIPriorityIssue] = Field(
        default_factory=list
    )


class AIAnalysisResponse(BaseModel):
    success: bool

    analysis_id: UUID

    lead_id: UUID

    scan_id: UUID

    provider: str

    model: str

    prompt_version: str

    business_summary: str | None = None

    website_assessment: str | None = None

    opportunity_summary: str | None = None

    sales_angle: str | None = None

    personalization_points: list[str] = Field(
        default_factory=list
    )

    priority_issues: list[AIPriorityIssue] = Field(
        default_factory=list
    )

    analysis_json: dict = Field(
        default_factory=dict
    )

    created_at: datetime

    model_config = {
        "from_attributes": True
    }


class AIAnalysisListResponse(BaseModel):
    success: bool

    total: int

    analyses: list[AIAnalysisResponse]