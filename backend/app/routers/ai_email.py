from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.ai_email import (
    AIEmailDraftListResponse,
    AIEmailDraftResponse,
    AIEmailDraftUpdateRequest,
    AIEmailGenerateRequest,
)
from app.services.ai_email import (
    delete_email_draft,
    generate_email_draft,
    get_email_draft,
    list_email_drafts,
    update_email_draft,
)
from app.utils.auth import get_current_user


router = APIRouter(
    prefix="/ai-email",
    tags=["AI Email Generator"],
)


@router.post(
    "/leads/{lead_id}/generate",
    response_model=AIEmailDraftResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_lead_email(
    lead_id: UUID,
    payload: AIEmailGenerateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = UUID(current_user["sub"])

    try:
        return await generate_email_draft(
            db=db,
            user_id=user_id,
            lead_id=lead_id,
            request=payload,
        )

    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI email generation failed: {exc}",
        ) from exc


@router.get(
    "/drafts",
    response_model=AIEmailDraftListResponse,
)
def get_all_email_drafts(
    lead_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = UUID(current_user["sub"])

    drafts = list_email_drafts(
        db=db,
        user_id=user_id,
        lead_id=lead_id,
    )

    return AIEmailDraftListResponse(
        items=drafts,
        total=len(drafts),
    )


@router.get(
    "/drafts/{draft_id}",
    response_model=AIEmailDraftResponse,
)
def get_single_email_draft(
    draft_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = UUID(current_user["sub"])

    draft = get_email_draft(
        db=db,
        user_id=user_id,
        draft_id=draft_id,
    )

    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email draft not found.",
        )

    return draft


@router.patch(
    "/drafts/{draft_id}",
    response_model=AIEmailDraftResponse,
)
def edit_email_draft(
    draft_id: UUID,
    payload: AIEmailDraftUpdateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = UUID(current_user["sub"])

    draft = get_email_draft(
        db=db,
        user_id=user_id,
        draft_id=draft_id,
    )

    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email draft not found.",
        )

    try:
        return update_email_draft(
            db=db,
            draft=draft,
            subject=payload.subject,
            body_text=payload.body_text,
            status=payload.status,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.delete(
    "/drafts/{draft_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_email_draft(
    draft_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = UUID(current_user["sub"])

    draft = get_email_draft(
        db=db,
        user_id=user_id,
        draft_id=draft_id,
    )

    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email draft not found.",
        )

    delete_email_draft(
        db=db,
        draft=draft,
    )

    return None