from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.website import (
    WebsiteBulkCheckRequest,
    WebsiteBulkCheckResponse,
    WebsiteBulkCheckResult,
    WebsiteCheckResponse,
)
from app.services.website import (
    check_lead_website,
    check_multiple_lead_websites,
)
from app.utils.auth import get_current_user


router = APIRouter(
    prefix="/leads",
    tags=["Website Detection"],
)


# ---------------------------------------------------------
# Check one website
# ---------------------------------------------------------

@router.post(
    "/{lead_id}/website-check",
    response_model=WebsiteCheckResponse,
)
async def check_website(
    lead_id: UUID,
    current_user: dict = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    user_id = UUID(
        current_user["sub"]
    )

    result = await check_lead_website(
        db=db,
        user_id=user_id,
        lead_id=lead_id,
    )

    return WebsiteCheckResponse(
        success=True,
        lead_id=lead_id,
        website=result.get("website"),
        website_status=result[
            "website_status"
        ],
        final_url=result.get(
            "final_url"
        ),
        http_status=result.get(
            "http_status"
        ),
        response_time_ms=result.get(
            "response_time_ms"
        ),
        error=result.get(
            "error"
        ),
    )


# ---------------------------------------------------------
# Check multiple websites
# ---------------------------------------------------------

@router.post(
    "/website-check/batch",
    response_model=WebsiteBulkCheckResponse,
)
async def check_websites_batch(
    payload: WebsiteBulkCheckRequest,
    current_user: dict = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    user_id = UUID(
        current_user["sub"]
    )

    results = await check_multiple_lead_websites(
        db=db,
        user_id=user_id,
        lead_ids=payload.lead_ids,
    )

    response_results = [
        WebsiteBulkCheckResult(
            lead_id=result["lead_id"],
            website_status=result[
                "website_status"
            ],
            website=result.get(
                "website"
            ),
            final_url=result.get(
                "final_url"
            ),
            http_status=result.get(
                "http_status"
            ),
            response_time_ms=result.get(
                "response_time_ms"
            ),
            error=result.get(
                "error"
            ),
        )
        for result in results
    ]

    return WebsiteBulkCheckResponse(
        success=True,
        total_requested=len(
            payload.lead_ids
        ),
        total_processed=len(
            response_results
        ),
        results=response_results,
    )