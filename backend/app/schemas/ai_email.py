from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EmailPersonalizationPoint(BaseModel):
    point: str
    source: str


class EmailEvidence(BaseModel):
    item: str
    source: str


class AIEmailGenerateRequest(BaseModel):
    email_type: str = Field(
        default="initial_outreach",
        max_length=50,
    )

    sender_name: str | None = Field(
        default=None,
        max_length=120,
    )

    sender_company: str | None = Field(
        default=None,
        max_length=150,
    )

    sender_service: str | None = Field(
        default=None,
        max_length=255,
    )

    call_to_action: str | None = Field(
        default=None,
        max_length=500,
    )

    tone: str = Field(
        default="professional",
        max_length=30,
    )

    length: str = Field(
        default="concise",
        max_length=30,
    )

    # Used internally when a scheduled follow-up is generated.  Keeping the
    # actual conversation in the prompt lets the model choose a new angle
    # instead of re-sending a saved template.
    prior_messages: list[dict] = Field(default_factory=list)
    follow_up_number: int | None = Field(default=None, ge=1, le=10)


class AIEmailGenerateData(BaseModel):
    subject: str
    body_text: str

    personalization_points: list[
        EmailPersonalizationPoint
    ] = Field(default_factory=list)

    source_evidence: list[
        EmailEvidence
    ] = Field(default_factory=list)

    call_to_action: str | None = None


class AIEmailDraftResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lead_id: UUID

    ai_analysis_id: UUID | None
    website_opportunity_id: UUID | None
    qualification_id: UUID | None

    provider: str
    model: str
    prompt_version: str

    email_type: str

    subject: str
    body_text: str

    personalization_points: list
    source_evidence: list

    call_to_action: str | None

    generation_context: dict

    status: str

    created_at: datetime
    updated_at: datetime


class AIEmailDraftListResponse(BaseModel):
    items: list[AIEmailDraftResponse]
    total: int


class AIEmailDraftUpdateRequest(BaseModel):
    subject: str | None = Field(
        default=None,
        min_length=1,
        max_length=500,
    )

    body_text: str | None = Field(
        default=None,
        min_length=1,
    )

    status: str | None = None
