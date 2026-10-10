from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.website_scan import WebsiteScan
from app.schemas.website_scan import (
    WebsiteScanListResponse,
    WebsiteScanRequest,
    WebsiteScanResponse,
)
from app.services.scanner import (
    get_latest_scan,
    scan_lead_website,
)
from app.utils.auth import get_current_user


router = APIRouter(
    prefix="/leads",
    tags=["Website Scanner"],
)


# ---------------------------------------------------------
# Scan website
# ---------------------------------------------------------

@router.post(
    "/{lead_id}/scan",
    response_model=WebsiteScanResponse,
)
async def scan_website(
    lead_id: UUID,
    payload: WebsiteScanRequest,
    current_user: dict = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    user_id = UUID(
        current_user["sub"]
    )

    scan = await scan_lead_website(
        db=db,
        user_id=user_id,
        lead_id=lead_id,
        force_rescan=payload.force_rescan,
    )

    return WebsiteScanResponse.model_validate(
        {
            "success": True,
            **scan.__dict__,
        }
    )


# ---------------------------------------------------------
# Get latest scan
# ---------------------------------------------------------

@router.get(
    "/{lead_id}/scan",
    response_model=WebsiteScanResponse,
)
def latest_scan(
    lead_id: UUID,
    current_user: dict = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    user_id = UUID(
        current_user["sub"]
    )

    scan = get_latest_scan(
        db=db,
        user_id=user_id,
        lead_id=lead_id,
    )

    if scan is None:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404,
            detail="No website scan found.",
        )

    return WebsiteScanResponse.model_validate(
        {
            "success": True,
            **scan.__dict__,
        }
    )


# ---------------------------------------------------------
# Scan history
# ---------------------------------------------------------

@router.get(
    "/{lead_id}/scans",
    response_model=WebsiteScanListResponse,
)
def scan_history(
    lead_id: UUID,
    limit: int = Query(
        default=10,
        ge=1,
        le=50,
    ),
    current_user: dict = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    user_id = UUID(
        current_user["sub"]
    )

    query = (
        select(WebsiteScan)
        .where(
            WebsiteScan.user_id == user_id,
            WebsiteScan.lead_id == lead_id,
        )
        .order_by(
            WebsiteScan.scanned_at.desc()
        )
        .limit(limit)
    )

    scans = list(
        db.scalars(query).all()
    )

    results = [
        WebsiteScanResponse.model_validate(
            {
                "success": True,
                **scan.__dict__,
            }
        )
        for scan in scans
    ]

    return WebsiteScanListResponse(
        success=True,
        total=len(results),
        scans=results,
    )