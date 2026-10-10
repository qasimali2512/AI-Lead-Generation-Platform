from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_email_draft import AIEmailDraft
from app.models.brand_settings import BrandSettings
from app.models.email_account import EmailAccount
from app.models.email_queue import EmailQueue
from app.models.lead import Lead
from app.services.ai_email import validate_draft_content


def _missing_brand_delivery_fields(
    db: Session,
    user_id: UUID,
) -> list[str]:
    """
    Only sender name and company name are required.
    Phone, website, postal address, and unsubscribe URL are optional —
    they enrich the email template but must not block sending.
    """
    brand = db.scalar(
        select(BrandSettings).where(BrandSettings.user_id == user_id)
    )
    if not brand:
        return ["Brand Settings (at minimum: sender name and company)"]

    required = {
        "sender name": brand.sender_name,
        "company":     brand.agency_name,
    }
    return [name for name, value in required.items() if not str(value or "").strip()]


def create_queue_item(
    db: Session,
    *,
    user_id: UUID,
    draft: AIEmailDraft,
    email_account_id: UUID | None = None,
    scheduled_at: datetime | None = None,
    priority: int = 100,
    queue_type: str = "initial",
) -> EmailQueue:

    lead = db.scalar(
        select(Lead).where(
            Lead.id == draft.lead_id,
            Lead.user_id == user_id,
        )
    )

    if not lead:
        raise ValueError(
            "Lead not found."
        )

    if not lead.email:
        raise ValueError(
            "Lead does not have an email address."
        )

    if draft.status != "approved":
        raise ValueError(
            "Only approved AI email drafts can be queued."
        )

    quality_errors = validate_draft_content(
        draft.subject,
        draft.body_text,
    )
    if quality_errors:
        raise ValueError(
            "Draft cannot be queued because it failed email quality checks: "
            + "; ".join(quality_errors)
            + "."
        )

    missing_brand_fields = _missing_brand_delivery_fields(db, user_id)
    if missing_brand_fields:
        raise ValueError(
            "Complete Brand Settings before queueing email: "
            + ", ".join(missing_brand_fields)
            + "."
        )

    account = None

    if email_account_id:
        account = db.scalar(
            select(EmailAccount).where(
                EmailAccount.id == email_account_id,
                EmailAccount.user_id == user_id,
                EmailAccount.status == "active",
            )
        )

        if not account:
            raise ValueError(
                "Selected email account was not found "
                "or is inactive."
            )

    if scheduled_at is None:
        scheduled_at = datetime.now(timezone.utc)

    queue_item = EmailQueue(
        user_id=user_id,
        lead_id=lead.id,
        draft_id=draft.id,
        email_account_id=(
            account.id
            if account
            else None
        ),
        recipient_email=lead.email,
        subject=draft.subject,
        body_text=draft.body_text,
        queue_type=queue_type,
        status="pending",
        priority=priority,
        scheduled_at=scheduled_at,
        attempt_count=0,
        max_attempts=3,
    )

    db.add(queue_item)
    db.commit()
    db.refresh(queue_item)

    return queue_item


def get_queue_item(
    db: Session,
    user_id: UUID,
    queue_id: UUID,
) -> EmailQueue | None:

    return db.scalar(
        select(EmailQueue).where(
            EmailQueue.id == queue_id,
            EmailQueue.user_id == user_id,
        )
    )


def list_queue_items(
    db: Session,
    user_id: UUID,
    status: str | None = None,
    limit: int = 100,
    days: int | None = 3,
) -> list[EmailQueue]:

    statement = select(EmailQueue).where(
        EmailQueue.user_id == user_id
    )

    if status:
        statement = statement.where(
            EmailQueue.status == status
        )

    # Default: last 3 days only
    if days is not None:
        from datetime import datetime, timezone, timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        statement = statement.where(
            EmailQueue.created_at >= cutoff
        )

    # Latest first (created_at DESC), then by priority
    statement = (
        statement
        .order_by(
            EmailQueue.created_at.desc(),
            EmailQueue.priority.asc(),
        )
        .limit(limit)
    )

    return list(
        db.scalars(statement).all()
    )


def get_ready_queue_items(
    db: Session,
    limit: int = 20,
) -> list[EmailQueue]:

    now = datetime.now(timezone.utc)

    statement = (
        select(EmailQueue)
        .where(
            EmailQueue.status.in_(
                ["pending", "scheduled"]
            ),
            EmailQueue.scheduled_at <= now,
        )
        .order_by(
            EmailQueue.priority.asc(),
            EmailQueue.scheduled_at.asc(),
        )
        .limit(limit)
    )

    return list(
        db.scalars(statement).all()
    )


def mark_processing(
    db: Session,
    queue_item: EmailQueue,
) -> EmailQueue:

    now = datetime.now(timezone.utc)

    queue_item.status = "processing"
    queue_item.started_at = now
    queue_item.last_attempt_at = now
    queue_item.attempt_count += 1
    queue_item.updated_at = now

    db.commit()
    db.refresh(queue_item)

    return queue_item


def mark_sent(
    db: Session,
    queue_item: EmailQueue,
    provider_message_id: str | None = None,
) -> EmailQueue:

    now = datetime.now(timezone.utc)

    queue_item.status = "sent"
    queue_item.sent_at = now
    queue_item.provider_message_id = (
        provider_message_id
    )
    queue_item.last_error = None
    queue_item.last_error_at = None
    queue_item.updated_at = now

    db.commit()
    db.refresh(queue_item)

    return queue_item


def mark_failed(
    db: Session,
    queue_item: EmailQueue,
    error_message: str,
) -> EmailQueue:

    now = datetime.now(timezone.utc)

    queue_item.last_error = error_message
    queue_item.last_error_at = now
    queue_item.updated_at = now

    if queue_item.attempt_count >= queue_item.max_attempts:
        # Max attempts reached — permanently failed
        queue_item.status = "failed"
        queue_item.next_retry_at = None
    else:
        # Schedule retry — use "scheduled" (DB constraint allows this)
        queue_item.status = "scheduled"
        queue_item.next_retry_at = (
            now + timedelta(minutes=5 * queue_item.attempt_count)
        )
        queue_item.scheduled_at = queue_item.next_retry_at

    db.commit()
    db.refresh(queue_item)

    return queue_item


def cancel_queue_item(
    db: Session,
    queue_item: EmailQueue,
) -> EmailQueue:

    queue_item.status = "cancelled"
    queue_item.updated_at = (
        datetime.now(timezone.utc)
    )

    db.commit()
    db.refresh(queue_item)

    return queue_item
