from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
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
from app.utils.auth import get_current_user


router = APIRouter(
    prefix="/leads",
    tags=["Leads"],
)


# ---------------------------------------------------------
# List leads
# ---------------------------------------------------------

@router.get(
    "",
    response_model=LeadListResponse,
)
def list_leads(
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=25,
        ge=1,
        le=100,
    ),
    industry: str | None = Query(
        default=None,
    ),
    city: str | None = Query(
        default=None,
    ),
    website_status: str | None = Query(
        default=None,
    ),
    lead_status: str | None = Query(
        default=None,
    ),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = UUID(current_user["sub"])

    leads, total = get_user_leads(
        db=db,
        user_id=user_id,
        page=page,
        page_size=page_size,
        industry=industry,
        city=city,
        website_status=website_status,
        lead_status=lead_status,
    )

    return LeadListResponse(
        success=True,
        total=total,
        page=page,
        page_size=page_size,
        leads=leads,
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