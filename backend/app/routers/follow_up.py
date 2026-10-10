from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.follow_up import (
    FollowUpSequenceCreate,
    FollowUpSequenceListResponse,
    FollowUpSequenceResponse,
    FollowUpSequenceStatusUpdate,
    FollowUpStepResponse,
)
from app.services.follow_up import (
    create_sequence,
    get_sequence,
    get_sequence_steps,
    list_sequences,
    pause_sequence,
    queue_ready_step,
    resume_sequence,
    stop_sequence,
)
from app.utils.auth import get_current_user


router = APIRouter(
    prefix="/follow-ups",
    tags=["Follow-ups"],
)


@router.post(
    "",
    response_model=FollowUpSequenceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_follow_up_sequence(
    payload: FollowUpSequenceCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = UUID(current_user["sub"])

    try:
        return create_sequence(
            db=db,
            user_id=user_id,
            payload=payload,
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


@router.get(
    "",
    response_model=FollowUpSequenceListResponse,
)
def get_follow_up_sequences(
    sequence_status: str | None = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = UUID(current_user["sub"])

    sequences = list_sequences(
        db=db,
        user_id=user_id,
        sequence_status=sequence_status,
    )

    return FollowUpSequenceListResponse(
        items=sequences,
        total=len(sequences),
    )


@router.get(
    "/{sequence_id}",
    response_model=FollowUpSequenceResponse,
)
def get_follow_up_sequence(
    sequence_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = UUID(current_user["sub"])

    sequence = get_sequence(
        db=db,
        user_id=user_id,
        sequence_id=sequence_id,
    )

    if not sequence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Follow-up sequence not found.",
        )

    return sequence


@router.get(
    "/{sequence_id}/steps",
    response_model=list[FollowUpStepResponse],
)
def get_follow_up_steps(
    sequence_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = UUID(current_user["sub"])

    sequence = get_sequence(
        db=db,
        user_id=user_id,
        sequence_id=sequence_id,
    )

    if not sequence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Follow-up sequence not found.",
        )

    return get_sequence_steps(
        db=db,
        user_id=user_id,
        sequence_id=sequence_id,
    )


@router.patch(
    "/{sequence_id}/status",
    response_model=FollowUpSequenceResponse,
)
def update_follow_up_status(
    sequence_id: UUID,
    payload: FollowUpSequenceStatusUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = UUID(current_user["sub"])

    sequence = get_sequence(
        db=db,
        user_id=user_id,
        sequence_id=sequence_id,
    )

    if not sequence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Follow-up sequence not found.",
        )

    requested_status = payload.status.strip().lower()

    try:

        if requested_status == "paused":
            return pause_sequence(
                db=db,
                sequence=sequence,
            )

        if requested_status == "active":
            return resume_sequence(
                db=db,
                sequence=sequence,
            )

        if requested_status in {
            "stopped",
            "cancelled",
        }:
            return stop_sequence(
                db=db,
                sequence=sequence,
                reason=requested_status,
            )

        raise ValueError(
            "Invalid follow-up sequence status."
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/steps/{step_id}/queue",
    response_model=FollowUpStepResponse,
)
def queue_follow_up_step(
    step_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = UUID(current_user["sub"])

    from sqlalchemy import select
    from app.models.follow_up_step import FollowUpStep

    step = db.scalar(
        select(FollowUpStep).where(
            FollowUpStep.id == step_id,
            FollowUpStep.user_id == user_id,
        )
    )

    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Follow-up step not found.",
        )

    try:
        return queue_ready_step(
            db=db,
            step=step,
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