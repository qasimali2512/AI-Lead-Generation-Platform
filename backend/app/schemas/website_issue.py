from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class WebsiteIssueResponse(BaseModel):
    id: UUID

    user_id: UUID
    lead_id: UUID
    scan_id: UUID

    category: str
    issue_code: str

    title: str
    severity: str

    evidence: str | None = None
    recommendation: str | None = None

    current_value: str | None = None
    expected_value: str | None = None

    status: str

    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
    }


class WebsiteIssueListResponse(BaseModel):
    success: bool

    total: int

    issues: list[WebsiteIssueResponse]


class WebsiteIssueStatusUpdateRequest(BaseModel):
    status: str = Field(
        min_length=1,
        max_length=30,
    )