from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.email_delivery import (
    EmailDeliveryEvent,
    EmailDeliveryListResponse,
    EmailDeliveryResponse,
)
from app.services.email_delivery import (
    create_delivery_from_queue,
    get_delivery,
    get_delivery_by_queue,
    list_deliveries,
    record_bounce,
    record_complaint,
    record_unsubscribe,
    update_delivery_event,
)
from app.utils.auth import get_current_user


router = APIRouter(
    prefix="/email-deliveries",
    tags=["Email Delivery"],
)


@router.post(
    "/from-queue/{queue_id}",
    response_model=EmailDeliveryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_delivery(
    queue_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = UUID(current_user["sub"])

    try:
        return create_delivery_from_queue(
            db=db,
            user_id=user_id,
            queue_id=queue_id,
        )

    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "",
    response_model=EmailDeliveryListResponse,
)
def get_deliveries(
    delivery_status: str | None = None,
    lead_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = UUID(current_user["sub"])

    deliveries = list_deliveries(
        db=db,
        user_id=user_id,
        delivery_status=delivery_status,
        lead_id=lead_id,
    )

    return EmailDeliveryListResponse(
        items=deliveries,
        total=len(deliveries),
    )


@router.get(
    "/{delivery_id}",
    response_model=EmailDeliveryResponse,
)
def get_single_delivery(
    delivery_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = UUID(current_user["sub"])

    delivery = get_delivery(
        db=db,
        user_id=user_id,
        delivery_id=delivery_id,
    )

    if not delivery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery record not found.",
        )

    return delivery


@router.get(
    "/queue/{queue_id}",
    response_model=EmailDeliveryResponse,
)
def get_queue_delivery(
    queue_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = UUID(current_user["sub"])

    delivery = get_delivery_by_queue(
        db=db,
        user_id=user_id,
        queue_id=queue_id,
    )

    if not delivery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery record not found.",
        )

    return delivery


@router.patch(
    "/{delivery_id}/event",
    response_model=EmailDeliveryResponse,
)
def update_delivery(
    delivery_id: UUID,
    payload: EmailDeliveryEvent,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = UUID(current_user["sub"])

    delivery = get_delivery(
        db=db,
        user_id=user_id,
        delivery_id=delivery_id,
    )

    if not delivery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery record not found.",
        )

    try:
        return update_delivery_event(
            db=db,
            delivery=delivery,
            event=payload,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/{delivery_id}/bounce",
    response_model=EmailDeliveryResponse,
)
def bounce_delivery(
    delivery_id: UUID,
    bounce_type: str,
    reason: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = UUID(current_user["sub"])

    delivery = get_delivery(
        db=db,
        user_id=user_id,
        delivery_id=delivery_id,
    )

    if not delivery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery record not found.",
        )

    return record_bounce(
        db=db,
        delivery=delivery,
        bounce_type=bounce_type,
        reason=reason,
    )


@router.post(
    "/{delivery_id}/complaint",
    response_model=EmailDeliveryResponse,
)
def complaint_delivery(
    delivery_id: UUID,
    complaint_type: str | None = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = UUID(current_user["sub"])

    delivery = get_delivery(
        db=db,
        user_id=user_id,
        delivery_id=delivery_id,
    )

    if not delivery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery record not found.",
        )

    return record_complaint(
        db=db,
        delivery=delivery,
        complaint_type=complaint_type,
    )


@router.post(
    "/{delivery_id}/unsubscribe",
    response_model=EmailDeliveryResponse,
)
def unsubscribe_delivery(
    delivery_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = UUID(current_user["sub"])

    delivery = get_delivery(
        db=db,
        user_id=user_id,
        delivery_id=delivery_id,
    )

    if not delivery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery record not found.",
        )

    return record_unsubscribe(
        db=db,
        delivery=delivery,
    )