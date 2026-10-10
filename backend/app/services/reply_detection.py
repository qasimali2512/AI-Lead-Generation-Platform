import re
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.email_delivery import EmailDelivery
from app.models.email_message import EmailMessage
from app.models.email_queue import EmailQueue
from app.models.email_thread import EmailThread
from app.models.follow_up_sequence import FollowUpSequence
from app.models.follow_up_step import FollowUpStep


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_email(value: str | None) -> str:
    if not value:
        return ""

    return value.strip().lower()


def _normalize_subject(subject: str | None) -> str:
    if not subject:
        return ""

    value = subject.strip()

    while True:
        updated = re.sub(
            r"^\s*((re|fw|fwd)\s*:\s*)+",
            "",
            value,
            flags=re.IGNORECASE,
        )

        if updated == value:
            break

        value = updated

    return value.strip().lower()


def _references_match(
    in_reply_to: str | None,
    references_header: str | None,
    candidate_message: EmailMessage,
) -> bool:
    candidate_ids = {
        value.strip()
        for value in [
            candidate_message.provider_message_id,
            candidate_message.internet_message_id,
        ]
        if value
    }

    if in_reply_to and in_reply_to.strip() in candidate_ids:
        return True

    if references_header:
        references = set(re.findall(r"<[^>]+>", references_header))

        for candidate_id in candidate_ids:
            if candidate_id in references:
                return True

    return False


def _find_matching_delivery(
    db: Session,
    user_id: UUID,
    from_email: str,
    subject: str | None,
) -> EmailDelivery | None:
    normalized_email = _normalize_email(from_email)
    normalized_subject = _normalize_subject(subject)

    deliveries = db.scalars(
        select(EmailDelivery)
        .where(
            EmailDelivery.user_id == user_id,
            EmailDelivery.recipient_email == normalized_email,
            EmailDelivery.status.in_(
                [
                    "sent",
                    "delivered",
                    "opened",
                    "clicked",
                ]
            ),
        )
        .order_by(EmailDelivery.sent_at.desc())
        .limit(50)
    ).all()

    if not deliveries:
        return None

    for delivery in deliveries:
        if _normalize_subject(delivery.subject) == normalized_subject:
            return delivery

    return deliveries[0]


def _find_matching_message(
    db: Session,
    user_id: UUID,
    provider: str,
    in_reply_to: str | None,
    references_header: str | None,
) -> EmailMessage | None:
    if not in_reply_to and not references_header:
        return None

    messages = db.scalars(
        select(EmailMessage)
        .where(
            EmailMessage.user_id == user_id,
            EmailMessage.provider == provider,
            EmailMessage.direction == "outbound",
        )
        .order_by(EmailMessage.sent_at.desc())
        .limit(200)
    ).all()

    for message in messages:
        if _references_match(
            in_reply_to,
            references_header,
            message,
        ):
            return message

    return None


def _find_thread(
    db: Session,
    user_id: UUID,
    provider: str,
    provider_thread_id: str | None,
    lead_id: UUID | None,
    subject: str | None,
) -> EmailThread | None:
    if provider_thread_id:
        thread = db.scalar(
            select(EmailThread)
            .where(
                EmailThread.user_id == user_id,
                EmailThread.provider == provider,
                EmailThread.provider_thread_id == provider_thread_id,
            )
        )

        if thread:
            return thread

    if lead_id:
        normalized_subject = _normalize_subject(subject)

        threads = db.scalars(
            select(EmailThread)
            .where(
                EmailThread.user_id == user_id,
                EmailThread.lead_id == lead_id,
            )
            .order_by(EmailThread.last_message_at.desc())
            .limit(50)
        ).all()

        for thread in threads:
            if _normalize_subject(thread.subject) == normalized_subject:
                return thread

    return None


def _stop_follow_up_sequences(
    db: Session,
    user_id: UUID,
    lead_id: UUID,
) -> int:
    sequences = db.scalars(
        select(FollowUpSequence)
        .where(
            FollowUpSequence.user_id == user_id,
            FollowUpSequence.lead_id == lead_id,
            FollowUpSequence.status.in_(
                [
                    "active",
                    "paused",
                ]
            ),
        )
    ).all()

    stopped_count = 0
    now = _now()

    for sequence in sequences:
        if sequence.stop_on_reply:
            sequence.status = "stopped"
            sequence.stop_reason = "reply"
            sequence.stopped_at = now
            sequence.updated_at = now

            steps = db.scalars(
                select(FollowUpStep)
                .where(
                    FollowUpStep.sequence_id == sequence.id,
                    FollowUpStep.status.in_(
                        [
                            "pending",
                            "scheduled",
                            "queued",
                        ]
                    ),
                )
            ).all()

            for step in steps:
                if step.queue_id:
                    queue = db.get(
                        EmailQueue,
                        step.queue_id,
                    )

                    if queue and queue.status in {
                        "pending",
                        "scheduled",
                    }:
                        queue.status = "cancelled"
                        queue.updated_at = now

                step.status = "stopped"
                step.skipped_at = now
                step.skip_reason = "lead_replied"
                step.updated_at = now

            stopped_count += 1

    return stopped_count


def ingest_reply(
    db: Session,
    user_id: UUID,
    data,
) -> dict:
    existing_message = db.scalar(
        select(EmailMessage)
        .where(
            EmailMessage.user_id == user_id,
            EmailMessage.provider == data.provider,
            EmailMessage.provider_message_id
            == data.provider_message_id,
        )
    )

    if existing_message:
        return {
            "message_id": existing_message.id,
            "thread_id": existing_message.thread_id,
            "lead_id": existing_message.lead_id,
            "sequence_stopped": False,
            "stopped_sequence_count": 0,
            "duplicate": True,
        }

    matching_message = _find_matching_message(
        db=db,
        user_id=user_id,
        provider=data.provider,
        in_reply_to=data.in_reply_to,
        references_header=data.references_header,
    )

    lead_id = data.lead_id

    if matching_message:
        lead_id = matching_message.lead_id

    matching_delivery = None

    if not lead_id:
        matching_delivery = _find_matching_delivery(
            db=db,
            user_id=user_id,
            from_email=data.from_email,
            subject=data.subject,
        )

        if matching_delivery:
            lead_id = matching_delivery.lead_id

    if not lead_id:
        raise ValueError(
            "Could not match the incoming reply to a lead. "
            "Provide lead_id or valid reply headers."
        )

    thread = _find_thread(
        db=db,
        user_id=user_id,
        provider=data.provider,
        provider_thread_id=data.provider_thread_id,
        lead_id=lead_id,
        subject=data.subject,
    )

    now = _now()

    message_time = data.received_at or now

    if thread is None:
        thread = EmailThread(
            user_id=user_id,
            lead_id=lead_id,
            email_account_id=data.email_account_id,
            provider=data.provider,
            provider_thread_id=data.provider_thread_id,
            subject=data.subject,
            status="replied",
            last_direction="inbound",
            last_message_at=message_time,
            created_at=now,
            updated_at=now,
        )

        db.add(thread)
        db.flush()

    else:
        thread.status = "replied"
        thread.last_direction = "inbound"
        thread.last_message_at = message_time
        thread.updated_at = now

        if data.provider_thread_id:
            thread.provider_thread_id = data.provider_thread_id

        if data.email_account_id:
            thread.email_account_id = data.email_account_id

    message = EmailMessage(
        user_id=user_id,
        thread_id=thread.id,
        lead_id=lead_id,
        email_account_id=data.email_account_id,
        provider=data.provider,
        provider_message_id=data.provider_message_id,
        internet_message_id=data.internet_message_id,
        in_reply_to=data.in_reply_to,
        references_header=data.references_header,
        direction="inbound",
        from_email=_normalize_email(data.from_email),
        to_emails=data.to_emails,
        cc_emails=data.cc_emails,
        subject=data.subject,
        body_text=data.body_text,
        received_at=message_time,
        sent_at=None,
        metadata_json=data.metadata,
        created_at=now,
    )

    db.add(message)

    stopped_count = _stop_follow_up_sequences(
        db=db,
        user_id=user_id,
        lead_id=lead_id,
    )

    db.commit()
    db.refresh(message)

    return {
        "message_id": message.id,
        "thread_id": thread.id,
        "lead_id": lead_id,
        "sequence_stopped": stopped_count > 0,
        "stopped_sequence_count": stopped_count,
        "duplicate": False,
    }


def list_threads(
    db: Session,
    user_id: UUID,
    status: str | None = None,
    skip: int = 0,
    limit: int = 50,
):
    query = (
        select(EmailThread)
        .where(
            EmailThread.user_id == user_id,
        )
        .order_by(
            EmailThread.last_message_at.desc(),
            EmailThread.created_at.desc(),
        )
        .offset(skip)
        .limit(limit)
    )

    if status:
        query = query.where(
            EmailThread.status == status
        )

    return db.scalars(query).all()


def get_thread(
    db: Session,
    user_id: UUID,
    thread_id: UUID,
) -> EmailThread | None:
    return db.scalar(
        select(EmailThread)
        .where(
            EmailThread.id == thread_id,
            EmailThread.user_id == user_id,
        )
    )


def list_thread_messages(
    db: Session,
    user_id: UUID,
    thread_id: UUID,
):
    thread = get_thread(
        db=db,
        user_id=user_id,
        thread_id=thread_id,
    )

    if not thread:
        return None

    messages = db.scalars(
        select(EmailMessage)
        .where(
            EmailMessage.user_id == user_id,
            EmailMessage.thread_id == thread_id,
        )
        .order_by(
            EmailMessage.received_at.asc(),
            EmailMessage.sent_at.asc(),
            EmailMessage.created_at.asc(),
        )
    ).all()

    return messages