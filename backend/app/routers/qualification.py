from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.lead_qualification import (
    LeadQualificationListResponse,
    LeadQualificationResponse,
)
from app.services.lead_qualification import (
    get_latest_qualification,
    list_qualifications,
    qualify_lead,
)
from app.utils.auth import get_current_user


router = APIRouter(
    prefix="/leads",
    tags=["Lead Qualification"],
)


def serialize_qualification(
    record,
) -> dict:

    return {
        "success": True,

        "qualification_id": record.id,

        "lead_id": record.lead_id,

        "website_score": (
            record.website_score
        ),

        "business_score": (
            record.business_score
        ),

        "opportunity_score": (
            record.opportunity_score
        ),

        "contact_score": (
            record.contact_score
        ),

        "total_score": (
            record.total_score
        ),

        "qualification_level": (
            record.qualification_level
        ),

        "outreach_readiness": (
            record.outreach_readiness
        ),

        "qualification_reason": (
            record.qualification_reason
        ),

        "recommended_approach": (
            record.recommended_approach
        ),

        "qualification_factors": (
            record.qualification_factors
        ),

        "qualification_json": (
            record.qualification_json
        ),

        "created_at": record.created_at,
    }


@router.post(
    "/{lead_id}/qualify",
    response_model=LeadQualificationResponse,
)
def qualify(
    lead_id: UUID,
    current_user: dict = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    user_id = UUID(
        current_user["sub"]
    )

    record = qualify_lead(
        db=db,
        lead_id=lead_id,
        user_id=user_id,
    )

    return serialize_qualification(
        record
    )


@router.get(
    "/{lead_id}/qualification",
    response_model=LeadQualificationResponse,
)
def get_qualification(
    lead_id: UUID,
    current_user: dict = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    user_id = UUID(
        current_user["sub"]
    )

    record = get_latest_qualification(
        db=db,
        lead_id=lead_id,
        user_id=user_id,
    )

    return serialize_qualification(
        record
    )


@router.get(
    "/qualifications",
    response_model=LeadQualificationListResponse,
)
def get_qualifications(
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=25,
        ge=1,
        le=100,
    ),
    current_user: dict = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    user_id = UUID(
        current_user["sub"]
    )

    total, records = list_qualifications(
        db=db,
        user_id=user_id,
        page=page,
        page_size=page_size,
    )

    return {
        "success": True,
        "total": total,
        "page": page,
        "page_size": page_size,
        "qualifications": [
            serialize_qualification(
                record
            )
            for record in records
        ],
    }