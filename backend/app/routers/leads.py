from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.lead_qualification import LeadQualification
from app.schemas.leads import (
    LeadDeleteResponse,
    LeadListResponse,
    LeadResponse,
    LeadStatusUpdateRequest,
)
from app.services.leads import (
    delete_user_lead,
    get_user_lead,
    get_user_leads,
    update_user_lead,
)
from app.services.lead_qualification import calculate_qualification
from app.utils.auth import get_current_user


router = APIRouter(
    prefix="/leads",
    tags=["Leads"],
)


# ---------------------------------------------------------
# List leads  — all filters handled server-side
# ---------------------------------------------------------

@router.get(
    "",
    response_model=LeadListResponse,
)
def list_leads(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    # Date range
    days: int | None = Query(
        default=1,
        ge=1,
        description="Leads created within last N days. Pass nothing for all time.",
    ),
    # Text search
    search: str | None = Query(
        default=None,
        description="Search across name, city, industry, email.",
    ),
    # Presence filters
    has_website: str | None = Query(
        default=None,
        description="'yes' or 'no'",
    ),
    has_email: str | None = Query(
        default=None,
        description="'yes' or 'no'",
    ),
    # Qualification
    qualification: str | None = Query(
        default=None,
        description="'qualified', 'unqualified', or 'ready'",
    ),
    # Sort
    sort_by: str = Query(
        default="date",
        description="'date', 'name', or 'industry'",
    ),
    # Legacy filters kept for compatibility
    industry: str | None = Query(default=None),
    city: str | None = Query(default=None),
    website_status: str | None = Query(default=None),
    lead_status: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = UUID(current_user["sub"])

    leads, total = get_user_leads(
        db=db,
        user_id=user_id,
        page=page,
        page_size=page_size,
        days=days,
        search=search,
        has_website=has_website,
        has_email=has_email,
        qualification=qualification,
        sort_by=sort_by,
        industry=industry,
        city=city,
        website_status=website_status,
        lead_status=lead_status,
    )

    lead_ids = [lead.id for lead in leads]
    qualifications = {}
    if lead_ids:
        qualifications = {
            record.lead_id: record
            for record in db.scalars(
                select(LeadQualification).where(
                    LeadQualification.user_id == user_id,
                    LeadQualification.lead_id.in_(lead_ids),
                )
            ).all()
        }

    enriched_leads = []
    for lead in leads:
        record = qualifications.get(lead.id)
        item = LeadResponse.model_validate(lead)
        if record:
            item = item.model_copy(
                update={
                    "qualification_status": record.qualification_level,
                    "total_score": record.total_score,
                    "website_score": record.website_score,
                    "business_score": record.business_score,
                    "opportunity_score": record.opportunity_score,
                    "contact_score": record.contact_score,
                    "outreach_readiness": record.outreach_readiness,
                    "qualification_reason": record.qualification_reason,
                }
            )
        elif lead.qualification_status == "pending":
            data = calculate_qualification(
                lead=lead,
                scan=None,
                issues=[],
                opportunity=None,
            )
            item = item.model_copy(
                update={
                    "qualification_status": data["qualification_level"],
                    "total_score": data["total_score"],
                    "website_score": data["website_score"],
                    "business_score": data["business_score"],
                    "opportunity_score": data["opportunity_score"],
                    "contact_score": data["contact_score"],
                    "outreach_readiness": data["outreach_readiness"],
                    "qualification_reason": data["qualification_reason"],
                }
            )
        enriched_leads.append(item)

    return LeadListResponse(
        success=True,
        total=total,
        page=page,
        page_size=page_size,
        leads=enriched_leads,
    )


# ---------------------------------------------------------
# Get single lead
# ---------------------------------------------------------

@router.get(
    "/{lead_id}",
    response_model=LeadResponse,
)
def get_lead(
    lead_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = UUID(current_user["sub"])

    return get_user_lead(
        db=db,
        user_id=user_id,
        lead_id=lead_id,
    )


# ---------------------------------------------------------
# Update lead
# ---------------------------------------------------------

@router.patch(
    "/{lead_id}",
    response_model=LeadResponse,
)
def update_lead(
    lead_id: UUID,
    payload: LeadStatusUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = UUID(current_user["sub"])

    return update_user_lead(
        db=db,
        user_id=user_id,
        lead_id=lead_id,
        payload=payload,
    )


# ---------------------------------------------------------
# Delete lead
# ---------------------------------------------------------

@router.delete(
    "/{lead_id}",
    response_model=LeadDeleteResponse,
)
def delete_lead(
    lead_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = UUID(current_user["sub"])

    delete_user_lead(
        db=db,
        user_id=user_id,
        lead_id=lead_id,
    )

    return LeadDeleteResponse(
        success=True,
        message="Lead deleted successfully.",
    )