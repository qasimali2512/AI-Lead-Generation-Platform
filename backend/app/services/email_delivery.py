from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.email_account import EmailAccount
from app.models.email_delivery import EmailDelivery
from app.models.email_queue import EmailQueue
from app.schemas.email_delivery import EmailDeliveryEvent


ALLOWED_STATUSES = {
    "queued",
    "sending",
    "sent",
    "delivered",
    "opened",
    "clicked",
    "bounced",
    "complained",
    "unsubscribed",
    "failed",
}


def get_delivery(
    db: Session,
    user_id: UUID,
    delivery_id: UUID,
) -> EmailDelivery | None:

    return db.scalar(
        select(EmailDelivery).where(
            EmailDelivery.id == delivery_id,
            EmailDelivery.user_id == user_id,
        )
    )


def get_delivery_by_queue(
    db: Session,
    user_id: UUID,
    queue_id: UUID,
) -> EmailDelivery | None:

    return db.scalar(
        select(EmailDelivery).where(
            EmailDelivery.queue_id == queue_id,
            EmailDelivery.user_id == user_id,
        )
    )


def list_deliveries(
    db: Session,
    user_id: UUID,
    delivery_status: str | None = None,
    lead_id: UUID | None = None,
) -> list[EmailDelivery]:

    statement = select(EmailDelivery).where(
        EmailDelivery.user_id == user_id
    )

    if delivery_status:
        statement = statement.where(
            EmailDelivery.status == delivery_status
        )

    if lead_id:
        statement = statement.where(
            EmailDelivery.lead_id == lead_id
        )

    statement = statement.order_by(
        EmailDelivery.created_at.desc()
    )

    return list(
        db.scalars(statement).all()
    )


def create_delivery_from_queue(
    db: Session,
    user_id: UUID,
    queue_id: UUID,
) -> EmailDelivery:

    queue_item = db.scalar(
        select(EmailQueue).where(
            EmailQueue.id == queue_id,
            EmailQueue.user_id == user_id,
        )
    )

    if not queue_item:
        raise LookupError(
            "Queue item not found."
        )

    existing = get_delivery_by_queue(
        db=db,
        user_id=user_id,
        queue_id=queue_id,
    )

    if existing:
        return existing

    sender_email = None
    provider = None
    account_id = queue_item.email_account_id

    if account_id:
        account = db.scalar(
            select(EmailAccount).where(
                EmailAccount.id == account_id,
                EmailAccount.user_id == user_id,
            )
        )

        if account:
            sender_email = account.email
            provider = account.provider

    delivery = EmailDelivery(
        user_id=user_id,
        queue_id=queue_item.id,
        lead_id=queue_item.lead_id,
        email_account_id=account_id,
        recipient_email=queue_item.recipient_email,
        sender_email=sender_email,
        provider=provider,
        provider_message_id=queue_item.provider_message_id,
        subject=queue_item.subject,
        body_text=queue_item.body_text,
        status="queued",
        metadata_json={
            "created_from": "email_queue"
        },
    )

    db.add(delivery)
    db.commit()
    db.refresh(delivery)

    return delivery


def record_sent_queue_delivery(
    db: Session,
    *,
    queue_item: EmailQueue,
) -> EmailDelivery:
    """Persist every successful send for reply matching and follow-up safety."""
    delivery = create_delivery_from_queue(
        db=db,
        user_id=queue_item.user_id,
        queue_id=queue_item.id,
    )
    now = datetime.now(timezone.utc)
    delivery.status = "sent"
    delivery.sent_at = delivery.sent_at or queue_item.sent_at or now
    delivery.provider_message_id = queue_item.provider_message_id
    delivery.updated_at = now
    db.commit()
    db.refresh(delivery)
    return delivery


def update_delivery_event(
    db: Session,
    delivery: EmailDelivery,
    event: EmailDeliveryEvent,
) -> EmailDelivery:

    new_status = event.status.strip().lower()

    if new_status not in ALLOWED_STATUSES:
        raise ValueError(
            "Invalid delivery status."
        )

    now = datetime.now(timezone.utc)

    delivery.status = new_status

    if event.provider_message_id:
        delivery.provider_message_id = (
            event.provider_message_id
        )

    if event.bounce_type:
        delivery.bounce_type = (
            event.bounce_type
        )

    if event.bounce_reason:
        delivery.bounce_reason = (
            event.bounce_reason
        )

    if event.complaint_type:
        delivery.complaint_type = (
            event.complaint_type
        )

    if event.failure_reason:
        delivery.failure_reason = (
            event.failure_reason
        )

    if event.metadata:
        delivery.metadata_json = {
            **delivery.metadata_json,
            **event.metadata,
        }

    if new_status == "sending":
        pass

    elif new_status == "sent":
        delivery.sent_at = (
            delivery.sent_at or now
        )

    elif new_status == "delivered":
        delivery.delivered_at = (
            delivery.delivered_at or now
        )

    elif new_status == "opened":
        delivery.opened_at = (
            delivery.opened_at or now
        )

    elif new_status == "clicked":
        delivery.clicked_at = (
            delivery.clicked_at or now
        )

    elif new_status == "bounced":
        delivery.bounced_at = (
            delivery.bounced_at or now
        )

    elif new_status == "complained":
        delivery.complained_at = (
            delivery.complained_at or now
        )

    elif new_status == "unsubscribed":
        delivery.unsubscribed_at = (
            delivery.unsubscribed_at or now
        )

    elif new_status == "failed":
        delivery.failed_at = (
            delivery.failed_at or now
        )

    delivery.updated_at = now

    db.commit()
    db.refresh(delivery)

    return delivery


def record_bounce(
    db: Session,
    delivery: EmailDelivery,
    bounce_type: str,
    reason: str,
) -> EmailDelivery:

    delivery.status = "bounced"

    delivery.bounced_at = (
        delivery.bounced_at
        or datetime.now(timezone.utc)
    )

    delivery.bounce_type = bounce_type
    delivery.bounce_reason = reason

    delivery.updated_at = (
        datetime.now(timezone.utc)
    )

    if delivery.email_account_id:

        account = db.scalar(
            select(EmailAccount).where(
                EmailAccount.id
                == delivery.email_account_id
            )
        )

        if account:
            account.bounce_count += 1
            account.updated_at = (
                datetime.now(timezone.utc)
            )

    db.commit()
    db.refresh(delivery)

    return delivery


def record_complaint(
    db: Session,
    delivery: EmailDelivery,
    complaint_type: str | None = None,
) -> EmailDelivery:

    delivery.status = "complained"

    delivery.complained_at = (
        delivery.complained_at
        or datetime.now(timezone.utc)
    )

    delivery.complaint_type = complaint_type

    delivery.updated_at = (
        datetime.now(timezone.utc)
    )

    if delivery.email_account_id:

        account = db.scalar(
            select(EmailAccount).where(
                EmailAccount.id
                == delivery.email_account_id
            )
        )

        if account:
            account.complaint_count += 1
            account.updated_at = (
                datetime.now(timezone.utc)
            )

    db.commit()
    db.refresh(delivery)

    return delivery


def record_unsubscribe(
    db: Session,
    delivery: EmailDelivery,
) -> EmailDelivery:

    delivery.status = "unsubscribed"

    delivery.unsubscribed_at = (
        delivery.unsubscribed_at
        or datetime.now(timezone.utc)
    )

    delivery.updated_at = (
        datetime.now(timezone.utc)
    )

    if delivery.email_account_id:

        account = db.scalar(
            select(EmailAccount).where(
                EmailAccount.id
                == delivery.email_account_id
            )
        )

        if account:
            account.unsubscribe_count += 1
            account.updated_at = (
                datetime.now(timezone.utc)
            )

    db.commit()
    db.refresh(delivery)

    return delivery
