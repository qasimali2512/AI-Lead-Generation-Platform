from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.notification import Notification


ALLOWED_NOTIFICATION_TYPES = {
    "info",
    "success",
    "warning",
    "error",
    "lead",
    "website",
    "email",
    "reply",
    "campaign",
    "system",
}


def create_notification(
    db: Session,
    user_id: UUID,
    title: str,
    message: str,
    notification_type: str = "info",
    action_url: str | None = None,
):
    notification_type = notification_type.lower().strip()

    if notification_type not in ALLOWED_NOTIFICATION_TYPES:
        notification_type = "info"

    notification = Notification(
        user_id=user_id,
        title=title.strip(),
        message=message.strip(),
        notification_type=notification_type,
        action_url=action_url,
        is_read=False,
    )

    db.add(notification)
    db.commit()
    db.refresh(notification)

    return notification


def list_notifications(
    db: Session,
    user_id: UUID,
    skip: int = 0,
    limit: int = 20,
    unread_only: bool = False,
):
    query = db.query(Notification).filter(
        Notification.user_id == user_id
    )

    if unread_only:
        query = query.filter(
            Notification.is_read.is_(False)
        )

    total = query.count()

    unread_count = (
        db.query(func.count(Notification.id))
        .filter(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
        .scalar()
        or 0
    )

    items = (
        query.order_by(
            Notification.created_at.desc()
        )
        .offset(skip)
        .limit(limit)
        .all()
    )

    return {
        "items": items,
        "total": total,
        "unread_count": unread_count,
        "skip": skip,
        "limit": limit,
    }


def mark_notification_read(
    db: Session,
    user_id: UUID,
    notification_id: UUID,
):
    notification = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
        .first()
    )

    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )

    if not notification.is_read:
        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(notification)

    return notification


def mark_all_notifications_read(
    db: Session,
    user_id: UUID,
):
    now = datetime.now(timezone.utc)

    updated = (
        db.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
        .update(
            {
                Notification.is_read: True,
                Notification.read_at: now,
            },
            synchronize_session=False,
        )
    )

    db.commit()

    return {
        "success": True,
        "message": "All notifications marked as read.",
        "updated_count": updated,
    }


def delete_notification(
    db: Session,
    user_id: UUID,
    notification_id: UUID,
):
    notification = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
        .first()
    )

    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )

    db.delete(notification)
    db.commit()

    return {
        "success": True,
        "message": "Notification deleted.",
    }