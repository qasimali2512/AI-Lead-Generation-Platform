from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.website_issue import (
    WebsiteIssueListResponse,
    WebsiteIssueResponse,
    WebsiteIssueStatusUpdateRequest,
)
from app.services.issue_engine import (
    analyze_and_save_scan,
    analyze_latest_scan,
)
from app.services.issues import (
    get_lead_issues,
    update_issue_status,
)
from app.utils.auth import get_current_user


router = APIRouter(
    prefix="/leads",
    tags=["Website Issues"],
)


# ---------------------------------------------------------
# Analyze latest scan
# ---------------------------------------------------------

@router.post(
    "/{lead_id}/issues/analyze",
    response_model=WebsiteIssueListResponse,
)
def analyze_latest(
    lead_id: UUID,
    current_user: dict = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    user_id = UUID(
        current_user["sub"]
    )

    try:
        _, issues = analyze_latest_scan(
            db=db,
            user_id=user_id,
            lead_id=lead_id,
        )

    except ValueError as exc:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    return WebsiteIssueListResponse(
        success=True,
        total=len(issues),
        issues=issues,
    )


# ---------------------------------------------------------
# Analyze specific scan
# ---------------------------------------------------------

@router.post(
    "/{lead_id}/scans/{scan_id}/issues/analyze",
    response_model=WebsiteIssueListResponse,
)
def analyze_scan(
    lead_id: UUID,
    scan_id: UUID,
    current_user: dict = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    user_id = UUID(
        current_user["sub"]
    )

    try:
        issues = analyze_and_save_scan(
            db=db,
            user_id=user_id,
            lead_id=lead_id,
            scan_id=scan_id,
        )

    except ValueError as exc:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    return WebsiteIssueListResponse(
        success=True,
        total=len(issues),
        issues=issues,
    )


# ---------------------------------------------------------
# Get lead issues
# ---------------------------------------------------------

@router.get(
    "/{lead_id}/issues",
    response_model=WebsiteIssueListResponse,
)
def list_lead_issues(
    lead_id: UUID,
    severity: str | None = Query(
        default=None,
    ),
    category: str | None = Query(
        default=None,
    ),
    issue_status: str | None = Query(
        default=None,
    ),
    current_user: dict = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    user_id = UUID(
        current_user["sub"]
    )

    issues = get_lead_issues(
        db=db,
        user_id=user_id,
        lead_id=lead_id,
        severity=severity,
        category=category,
        issue_status=issue_status,
    )

    return WebsiteIssueListResponse(
        success=True,
        total=len(issues),
        issues=issues,
    )


# ---------------------------------------------------------
# Update issue status
# ---------------------------------------------------------

@router.patch(
    "/issues/{issue_id}",
    response_model=WebsiteIssueResponse,
)
def update_issue(
    issue_id: UUID,
    payload: WebsiteIssueStatusUpdateRequest,
    current_user: dict = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    user_id = UUID(
        current_user["sub"]
    )

    return update_issue_status(
        db=db,
        user_id=user_id,
        issue_id=issue_id,
        new_status=payload.status,
    )