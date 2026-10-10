from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.reply import (
    EmailMessageResponse,
    EmailThreadResponse,
    ReplyIngestRequest,
    ReplyIngestResponse,
)
from app.services.reply_detection import (
    get_thread,
    ingest_reply,
    list_thread_messages,
    list_threads,
)
from app.utils.auth import get_current_user


router = APIRouter(
    prefix="/replies",
    tags=["Replies"],
)


# =========================================================
# Ingest incoming reply
# =========================================================

@router.post(
    "/ingest",
    response_model=ReplyIngestResponse,
)
def ingest_reply_event(
    payload: ReplyIngestRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = UUID(
        current_user["sub"]
    )

    try:
        result = ingest_reply(
            db=db,
            user_id=user_id,
            data=payload,
        )

        return result

    except ValueError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=str(exc),
        ) from exc


# =========================================================
# List reply threads
# =========================================================

@router.get(
    "/threads",
    response_model=list[EmailThreadResponse],
)
def get_reply_threads(
    status_filter: str | None = Query(
        default=None,
        alias="status",
    ),
    skip: int = Query(
        default=0,
        ge=0,
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
    ),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = UUID(
        current_user["sub"]
    )

    return list_threads(
        db=db,
        user_id=user_id,
        status=status_filter,
        skip=skip,
        limit=limit,
    )


# =========================================================
# Get single reply thread
# =========================================================

@router.get(
    "/threads/{thread_id}",
    response_model=EmailThreadResponse,
)
def get_reply_thread(
    thread_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = UUID(
        current_user["sub"]
    )

    thread = get_thread(
        db=db,
        user_id=user_id,
        thread_id=thread_id,
    )

    if not thread:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail="Email thread not found.",
        )

    return thread


# =========================================================
# Get messages inside a thread
# =========================================================

@router.get(
    "/threads/{thread_id}/messages",
    response_model=list[EmailMessageResponse],
)
def get_thread_messages(
    thread_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = UUID(
        current_user["sub"]
    )

    messages = list_thread_messages(
        db=db,
        user_id=user_id,
        thread_id=thread_id,
    )

    if messages is None:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail="Email thread not found.",
        )

    return messages