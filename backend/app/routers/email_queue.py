from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.email_queue import (
    EmailQueueCreate,
    EmailQueueListResponse,
    EmailQueueResponse,
)
from app.services.email_queue import (
    cancel_queue_item,
    create_queue_item,
    get_queue_item,
    list_queue_items,
)
from app.utils.auth import get_current_user


router = APIRouter(
    prefix="/email-queue",
    tags=["Email Queue"],
)


@router.post(
    "",
    response_model=EmailQueueResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_to_queue(
    payload: EmailQueueCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Queue an approved AI email draft for sending."""
    from app.models.ai_email_draft import AIEmailDraft
    from sqlalchemy import select

    user_id = UUID(current_user["sub"])

    draft = db.scalar(
        select(AIEmailDraft).where(
            AIEmailDraft.id == payload.draft_id,
            AIEmailDraft.user_id == user_id,
        )
    )

    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI email draft not found.",
        )

    try:
        item = create_queue_item(
            db=db,
            user_id=user_id,
            draft=draft,
            email_account_id=payload.email_account_id,
            scheduled_at=payload.scheduled_at,
            priority=payload.priority,
            queue_type=payload.queue_type,
        )
        return item
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "",
    response_model=EmailQueueListResponse,
)
def get_queue(
    queue_status: str | None = None,
    limit: int = 100,
    days: int = 3,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List email queue items for the current user (default: last 3 days, newest first)."""
    user_id = UUID(current_user["sub"])

    items = list_queue_items(
        db=db,
        user_id=user_id,
        status=queue_status,
        limit=min(limit, 500),
        days=days if days > 0 else None,
    )

    return EmailQueueListResponse(
        items=items,
        total=len(items),
    )


@router.get(
    "/{queue_id}",
    response_model=EmailQueueResponse,
)
def get_single_queue_item(
    queue_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get a single email queue item by ID."""
    user_id = UUID(current_user["sub"])

    item = get_queue_item(
        db=db,
        user_id=user_id,
        queue_id=queue_id,
    )

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Queue item not found.",
        )

    return item


@router.post(
    "/{queue_id}/cancel",
    response_model=EmailQueueResponse,
)
def cancel_item(
    queue_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Cancel a pending or scheduled queue item."""
    user_id = UUID(current_user["sub"])

    item = get_queue_item(
        db=db,
        user_id=user_id,
        queue_id=queue_id,
    )

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Queue item not found.",
        )

    if item.status not in ("pending", "scheduled", "retry"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel a queue item with status '{item.status}'.",
        )

    return cancel_queue_item(db=db, queue_item=item)
