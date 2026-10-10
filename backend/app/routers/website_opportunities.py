from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.lead import Lead
from app.models.website_opportunity import WebsiteOpportunity
from app.schemas.website_opportunity import (
    WebsiteOpportunityListResponse,
    WebsiteOpportunityResponse,
    WebsiteOpportunityStatusUpdateRequest,
)
from app.services.website_opportunity import (
    create_opportunity,
    get_latest_opportunity,
    list_opportunities,
    update_opportunity_status,
)
from app.utils.auth import get_current_user


router = APIRouter(
    prefix="",
    tags=["Website Opportunities"],
)


# =========================================================
# Serialization helpers
# =========================================================

def _qualification_level(qualification_status: str) -> str:
    """Map qualification_status → display level for the frontend."""
    return {
        "qualified": "high",
        "pending": "medium",
        "unqualified": "low",
    }.get(qualification_status, "medium")


def serialize_opportunity(
    opportunity,
    email: str | None = None,
    phone: str | None = None,
) -> dict:

    return {
        "success": True,

        "opportunity_id": (
            opportunity.id
        ),

        "lead_id": (
            opportunity.lead_id
        ),

        "opportunity_type": (
            opportunity.opportunity_type
        ),

        "industry": (
            opportunity.industry
        ),

        "business_name": (
            opportunity.business_name
        ),

        "location_summary": (
            opportunity.location_summary
        ),

        "business_summary": (
            opportunity.business_summary
        ),

        "opportunity_summary": (
            opportunity.opportunity_summary
        ),

        "recommended_solution": (
            opportunity.recommended_solution
        ),

        "sales_angle": (
            opportunity.sales_angle
        ),

        "personalization_points": (
            opportunity.personalization_points
        ),

        "suggested_features": (
            opportunity.suggested_features
        ),

        "qualification_status": (
            opportunity.qualification_status
        ),

        "qualification_level": (
            _qualification_level(
                opportunity.qualification_status
            )
        ),

        "opportunity_status": (
            opportunity.opportunity_status
        ),

        "email": email,
        "phone": phone,

        "analysis_json": (
            opportunity.analysis_json
        ),

        "provider": (
            opportunity.provider
        ),

        "model": (
            opportunity.model
        ),

        "prompt_version": (
            opportunity.prompt_version
        ),

        "created_at": (
            opportunity.created_at
        ),
    }


def _lead_contacts(
    db: Session,
    lead_id: UUID,
) -> tuple[str | None, str | None]:
    """Return (email, phone) for a lead, or (None, None) if not found."""
    lead = db.scalar(
        select(Lead).where(Lead.id == lead_id)
    )
    if lead is None:
        return None, None
    return lead.email, lead.phone


# =========================================================
# Create website opportunity for a lead
# =========================================================

@router.post(
    "/leads/{lead_id}/website-opportunity",
    response_model=WebsiteOpportunityResponse,
)
async def create_website_opportunity(
    lead_id: UUID,
    current_user: dict = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    user_id = UUID(
        current_user["sub"]
    )

    opportunity = await create_opportunity(
        db=db,
        lead_id=lead_id,
        user_id=user_id,
    )

    email, phone = _lead_contacts(db, lead_id)

    return serialize_opportunity(
        opportunity,
        email=email,
        phone=phone,
    )


# =========================================================
# Get latest opportunity for a lead
# =========================================================

@router.get(
    "/leads/{lead_id}/website-opportunity",
    response_model=WebsiteOpportunityResponse,
)
def get_website_opportunity(
    lead_id: UUID,
    current_user: dict = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    user_id = UUID(
        current_user["sub"]
    )

    opportunity = get_latest_opportunity(
        db=db,
        lead_id=lead_id,
        user_id=user_id,
    )

    email, phone = _lead_contacts(db, lead_id)

    return serialize_opportunity(
        opportunity,
        email=email,
        phone=phone,
    )


# =========================================================
# List all website opportunities
#
# Frontend endpoint:
# GET /api/v1/website-opportunities?limit=100
# =========================================================

@router.get(
    "/website-opportunities",
    response_model=WebsiteOpportunityListResponse,
)
def get_website_opportunities(
    limit: int = Query(
        default=100,
        ge=1,
        le=100,
    ),
    page: int = Query(
        default=1,
        ge=1,
    ),
    current_user: dict = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    user_id = UUID(
        current_user["sub"]
    )

    total, enriched_rows = list_opportunities(
        db=db,
        user_id=user_id,
        page=page,
        page_size=limit,
    )

    return {
        "success": True,
        "total": total,
        "opportunities": [
            serialize_opportunity(
                row["opportunity"],
                email=row["email"],
                phone=row["phone"],
            )
            for row in enriched_rows
        ],
    }


# =========================================================
# Update opportunity status
# =========================================================

@router.patch(
    "/website-opportunities/{opportunity_id}",
    response_model=WebsiteOpportunityResponse,
)
def update_website_opportunity(
    opportunity_id: UUID,
    payload: WebsiteOpportunityStatusUpdateRequest,
    current_user: dict = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    user_id = UUID(
        current_user["sub"]
    )

    opportunity = update_opportunity_status(
        db=db,
        opportunity_id=opportunity_id,
        user_id=user_id,
        payload=payload,
    )

    email, phone = _lead_contacts(
        db, opportunity.lead_id
    )

    return serialize_opportunity(
        opportunity,
        email=email,
        phone=phone,
    )


# =========================================================
# Delete a website opportunity
# =========================================================

@router.delete(
    "/website-opportunities/{opportunity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_website_opportunity(
    opportunity_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Permanently delete a website opportunity."""
    user_id = UUID(current_user["sub"])

    opportunity = db.scalar(
        select(WebsiteOpportunity).where(
            WebsiteOpportunity.id == opportunity_id,
            WebsiteOpportunity.user_id == user_id,
        )
    )

    if opportunity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website opportunity not found.",
        )

    db.delete(opportunity)
    db.commit()
    return None


# =========================================================
# Bulk generate opportunities for all no-website leads
# =========================================================

@router.post(
    "/website-opportunities/bulk-generate",
    summary="Generate opportunities for all no-website leads that don't have one yet",
)
async def bulk_generate_opportunities(
    limit: int = Query(
        default=20,
        ge=1,
        le=50,
        description="Max leads to process in one request (1–50)",
    ),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Finds all leads with website_status='no_website' that don't have an
    opportunity yet, then generates AI opportunities for up to `limit` of them.

    Returns a summary: { queued, generated, skipped, failed, errors[] }
    """
    from app.models.lead import Lead
    from app.services.website_opportunity import (
        generate_opportunity,
        build_system_prompt,
        build_user_prompt,
        PROMPT_VERSION,
    )
    from app.config import settings as app_settings

    user_id = UUID(current_user["sub"])

    # 1. Get all lead IDs that already have an opportunity
    existing_lead_ids = set(
        row[0]
        for row in db.execute(
            select(WebsiteOpportunity.lead_id).where(
                WebsiteOpportunity.user_id == user_id
            )
        ).all()
    )

    # 2. Find no-website leads without an opportunity
    leads_to_process = list(
        db.scalars(
            select(Lead)
            .where(
                Lead.user_id == user_id,
                Lead.website_status == "no_website",
                Lead.id.notin_(existing_lead_ids),
            )
            .order_by(Lead.created_at.desc())
            .limit(limit)
        ).all()
    )

    queued = len(leads_to_process)
    generated = 0
    skipped = 0
    failed = 0
    errors: list[dict] = []

    for lead in leads_to_process:
        try:
            analysis = await generate_opportunity(lead)

            location_parts = [
                p for p in [lead.city, lead.state, lead.country] if p
            ]

            record = WebsiteOpportunity(
                user_id=user_id,
                lead_id=lead.id,
                opportunity_type="website_development",
                industry=lead.industry,
                business_name=lead.name,
                location_summary=", ".join(location_parts),
                business_summary=analysis["business_summary"],
                opportunity_summary=analysis["opportunity_summary"],
                recommended_solution=analysis["recommended_solution"],
                sales_angle=analysis["sales_angle"],
                personalization_points=analysis.get("personalization_points", []),
                suggested_features=analysis.get("suggested_features", []),
                qualification_status="pending",
                opportunity_status="open",
                analysis_json=analysis,
                provider="cloudflare",
                model=app_settings.cloudflare_ai_model,
                prompt_version=PROMPT_VERSION,
            )

            db.add(record)
            db.commit()
            generated += 1

        except HTTPException as exc:
            if exc.status_code == 409:
                skipped += 1
            else:
                failed += 1
                errors.append({
                    "lead_id": str(lead.id),
                    "business": lead.name,
                    "error": exc.detail,
                })

        except Exception as exc:
            failed += 1
            errors.append({
                "lead_id": str(lead.id),
                "business": lead.name,
                "error": str(exc)[:200],
            })

    return {
        "success": True,
        "queued": queued,
        "generated": generated,
        "skipped": skipped,
        "failed": failed,
        "errors": errors,
    }
