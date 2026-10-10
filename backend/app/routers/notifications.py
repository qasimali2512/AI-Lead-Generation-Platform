from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.notification import (
    CreateNotificationRequest,
    NotificationActionResponse,
    NotificationListResponse,
    NotificationResponse,
)
from app.services.notification import (
    create_notification,
    delete_notification,
    list_notifications,
    mark_all_notifications_read,
    mark_notification_read,
)
from app.utils.auth import get_current_user


router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)


@router.get(
    "",
    response_model=NotificationListResponse,
)
def get_notifications(
    unread_only: bool = Query(
        default=False,
    ),
    skip: int = Query(
        default=0,
        ge=0,
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return list_notifications(
        db=db,
        user_id=current_user["sub"],
        skip=skip,
        limit=limit,
        unread_only=unread_only,
    )


@router.post(
    "",
    response_model=NotificationResponse,
)
def create_notification_route(
    payload: CreateNotificationRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return create_notification(
        db=db,
        user_id=current_user["sub"],
        title=payload.title,
        message=payload.message,
        notification_type=payload.notification_type,
        action_url=payload.action_url,
    )


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
)
def mark_read(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return mark_notification_read(
        db=db,
        user_id=current_user["sub"],
        notification_id=notification_id,
    )


@router.post(
    "/read-all",
    response_model=NotificationActionResponse,
)
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return mark_all_notifications_read(
        db=db,
        user_id=current_user["sub"],
    )


@router.delete(
    "/{notification_id}",
    response_model=NotificationActionResponse,
)
def delete(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return delete_notification(
        db=db,
        user_id=current_user["sub"],
        notification_id=notification_id,
    )