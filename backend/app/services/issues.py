from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.website_issue import WebsiteIssue


VALID_ISSUE_STATUSES = {
    "open",
    "acknowledged",
    "resolved",
    "ignored",
}


def get_user_issue(
    db: Session,
    user_id: UUID,
    issue_id: UUID,
) -> WebsiteIssue:

    issue = db.scalar(
        select(WebsiteIssue).where(
            WebsiteIssue.id == issue_id,
            WebsiteIssue.user_id == user_id,
        )
    )

    if issue is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website issue not found.",
        )

    return issue


def get_lead_issues(
    db: Session,
    user_id: UUID,
    lead_id: UUID,
    severity: str | None = None,
    category: str | None = None,
    issue_status: str | None = None,
) -> list[WebsiteIssue]:

    filters = [
        WebsiteIssue.user_id == user_id,
        WebsiteIssue.lead_id == lead_id,
    ]

    if severity:
        filters.append(
            WebsiteIssue.severity
            == severity.strip().lower()
        )

    if category:
        filters.append(
            WebsiteIssue.category
            == category.strip().lower()
        )

    if issue_status:
        filters.append(
            WebsiteIssue.status
            == issue_status.strip().lower()
        )

    query = (
        select(WebsiteIssue)
        .where(*filters)
        .order_by(
            WebsiteIssue.created_at.desc()
        )
    )

    return list(
        db.scalars(query).all()
    )


def update_issue_status(
    db: Session,
    user_id: UUID,
    issue_id: UUID,
    new_status: str,
) -> WebsiteIssue:

    normalized_status = (
        new_status.strip().lower()
    )

    if normalized_status not in VALID_ISSUE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Invalid issue status. "
                "Allowed values: "
                + ", ".join(
                    sorted(
                        VALID_ISSUE_STATUSES
                    )
                )
            ),
        )

    issue = get_user_issue(
        db=db,
        user_id=user_id,
        issue_id=issue_id,
    )

    issue.status = normalized_status

    try:
        db.commit()
        db.refresh(issue)

    except Exception:
        db.rollback()
        raise

    return issue