from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_email_draft import AIEmailDraft
from app.models.email_delivery import EmailDelivery
from app.models.email_queue import EmailQueue
from app.models.email_suppression import EmailSuppression
from app.models.email_message import EmailMessage
from app.models.campaign import Campaign, CampaignLead
from app.models.follow_up_sequence import FollowUpSequence
from app.models.follow_up_step import FollowUpStep
from app.schemas.follow_up import FollowUpSequenceCreate
from app.schemas.ai_email import AIEmailGenerateRequest
from app.services.ai_email import generate_email_draft
from app.services.email_queue import create_queue_item


ALLOWED_SEQUENCE_STATUSES = {
    "active",
    "paused",
    "completed",
    "stopped",
    "cancelled",
}


def get_sequence(
    db: Session,
    user_id: UUID,
    sequence_id: UUID,
) -> FollowUpSequence | None:

    return db.scalar(
        select(FollowUpSequence).where(
            FollowUpSequence.id == sequence_id,
            FollowUpSequence.user_id == user_id,
        )
    )


def list_sequences(
    db: Session,
    user_id: UUID,
    sequence_status: str | None = None,
) -> list[FollowUpSequence]:

    statement = select(FollowUpSequence).where(
        FollowUpSequence.user_id == user_id
    )

    if sequence_status:
        statement = statement.where(
            FollowUpSequence.status == sequence_status
        )

    statement = statement.order_by(
        FollowUpSequence.created_at.desc()
    )

    return list(
        db.scalars(statement).all()
    )


def _is_suppressed(
    db: Session,
    user_id: UUID,
    email: str,
) -> bool:

    return db.scalar(
        select(EmailSuppression.id).where(
            EmailSuppression.user_id == user_id,
            EmailSuppression.email == email.lower().strip(),
        )
    ) is not None


def _has_blocking_delivery_event(
    db: Session,
    user_id: UUID,
    lead_id: UUID,
) -> tuple[bool, str | None]:

    deliveries = list(
        db.scalars(
            select(EmailDelivery).where(
                EmailDelivery.user_id == user_id,
                EmailDelivery.lead_id == lead_id,
            )
        ).all()
    )

    for delivery in deliveries:

        if delivery.status == "complained":
            return True, "complaint"

        if delivery.status == "unsubscribed":
            return True, "unsubscribe"

        # Any reported bounce ends outreach.  A soft bounce can later be
        # retried by the delivery layer, but it must not trigger a new
        # follow-up sequence in the meantime.
        if delivery.status == "bounced":
            return True, "bounce"

    return False, None


def _has_reply(db: Session, user_id: UUID, lead_id: UUID) -> bool:
    return db.scalar(
        select(EmailMessage.id).where(
            EmailMessage.user_id == user_id,
            EmailMessage.lead_id == lead_id,
            EmailMessage.direction == "inbound",
        ).limit(1)
    ) is not None


def create_campaign_follow_up_sequence(
    db: Session,
    *,
    initial_delivery: EmailDelivery,
) -> FollowUpSequence | None:
    """Create dynamic, delay-from-initial follow-up steps for a campaign."""
    campaign_lead = db.scalar(
        select(CampaignLead).where(
            CampaignLead.email_queue_id == initial_delivery.queue_id,
            CampaignLead.lead_id == initial_delivery.lead_id,
        )
    )
    if not campaign_lead:
        return None
    campaign = db.get(Campaign, campaign_lead.campaign_id)
    if not campaign:
        return None
    settings = [item for item in (campaign.follow_up_settings or []) if item.get("enabled", True)]
    if not settings:
        return None
    existing = db.scalar(select(FollowUpSequence).where(
        FollowUpSequence.initial_delivery_id == initial_delivery.id,
    ))
    if existing:
        return existing

    sequence = FollowUpSequence(
        user_id=initial_delivery.user_id,
        lead_id=initial_delivery.lead_id,
        initial_delivery_id=initial_delivery.id,
        status="active",
        current_step=0,
        max_steps=len(settings),
        stop_on_reply=True,
        stop_on_bounce=True,
        stop_on_complaint=True,
        stop_on_unsubscribe=True,
        metadata_json={"created_from": "campaign", "campaign_id": str(campaign.id), "generation": "at_due_time"},
    )
    db.add(sequence)
    db.flush()
    base_time = initial_delivery.sent_at or datetime.now(timezone.utc)
    for number, setting in enumerate(settings, start=1):
        delay = max(1, int(setting.get("delay", 3)))
        if str(setting.get("unit", "days")).lower() == "days":
            delay *= 24
        db.add(FollowUpStep(
            user_id=initial_delivery.user_id,
            sequence_id=sequence.id,
            draft_id=None,
            step_number=number,
            delay_hours=delay,
            # Each UI delay is relative to the initial email, not cumulative.
            scheduled_at=base_time + timedelta(hours=delay),
            status="pending",
        ))
    db.commit()
    db.refresh(sequence)
    return sequence


def create_sequence(
    db: Session,
    user_id: UUID,
    payload: FollowUpSequenceCreate,
) -> FollowUpSequence:

    initial_delivery = db.scalar(
        select(EmailDelivery).where(
            EmailDelivery.id == payload.initial_delivery_id,
            EmailDelivery.user_id == user_id,
        )
    )

    if not initial_delivery:
        raise LookupError(
            "Initial email delivery not found."
        )

    if initial_delivery.status not in {
        "sent",
        "delivered",
        "opened",
        "clicked",
    }:
        raise ValueError(
            "Follow-up sequence can only start "
            "after the initial email has been sent."
        )

    if _is_suppressed(
        db,
        user_id,
        initial_delivery.recipient_email,
    ):
        raise ValueError(
            "Recipient is suppressed and cannot receive follow-ups."
        )

    existing = db.scalar(
        select(FollowUpSequence).where(
            FollowUpSequence.initial_delivery_id
            == initial_delivery.id,
            FollowUpSequence.status.in_(
                {
                    "active",
                    "paused",
                }
            ),
        )
    )

    if existing:
        raise ValueError(
            "An active follow-up sequence already exists."
        )

    if not payload.steps:
        raise ValueError(
            "At least one follow-up step is required."
        )

    if len(payload.steps) > 10:
        raise ValueError(
            "A maximum of 10 follow-up steps is allowed."
        )

    base_time = (
        initial_delivery.sent_at
        or datetime.now(timezone.utc)
    )

    sequence = FollowUpSequence(
        user_id=user_id,
        lead_id=initial_delivery.lead_id,
        initial_delivery_id=initial_delivery.id,
        status="active",
        current_step=0,
        max_steps=len(payload.steps),
        stop_on_reply=payload.stop_on_reply,
        stop_on_bounce=payload.stop_on_bounce,
        stop_on_complaint=payload.stop_on_complaint,
        stop_on_unsubscribe=payload.stop_on_unsubscribe,
        metadata_json={
            "created_from": "initial_delivery"
        },
    )

    db.add(sequence)
    db.flush()

    cumulative_hours = 0

    for index, step_payload in enumerate(
        payload.steps,
        start=1,
    ):

        draft = None
        if step_payload.draft_id:
            draft = db.scalar(select(AIEmailDraft).where(
                AIEmailDraft.id == step_payload.draft_id,
                AIEmailDraft.user_id == user_id,
                AIEmailDraft.lead_id == initial_delivery.lead_id,
            ))
            if not draft or draft.status != "approved" or draft.email_type != "follow_up":
                raise ValueError(f"Follow-up draft for step {index} must be an approved follow_up draft.")

        cumulative_hours += step_payload.delay_hours

        scheduled_at = (
            base_time
            + timedelta(hours=cumulative_hours)
        )

        step = FollowUpStep(
            user_id=user_id,
            sequence_id=sequence.id,
            draft_id=draft.id if draft else None,
            step_number=index,
            delay_hours=step_payload.delay_hours,
            scheduled_at=scheduled_at,
            status="pending",
        )

        db.add(step)

    db.commit()
    db.refresh(sequence)

    return sequence


def get_sequence_steps(
    db: Session,
    user_id: UUID,
    sequence_id: UUID,
) -> list[FollowUpStep]:

    return list(
        db.scalars(
            select(FollowUpStep).where(
                FollowUpStep.user_id == user_id,
                FollowUpStep.sequence_id == sequence_id,
            ).order_by(
                FollowUpStep.step_number.asc()
            )
        ).all()
    )


def stop_sequence(
    db: Session,
    sequence: FollowUpSequence,
    reason: str,
) -> FollowUpSequence:

    if sequence.status in {
        "completed",
        "cancelled",
    }:
        return sequence

    now = datetime.now(timezone.utc)

    sequence.status = "stopped"
    sequence.stop_reason = reason
    sequence.stopped_at = now
    sequence.updated_at = now

    pending_steps = list(
        db.scalars(
            select(FollowUpStep).where(
                FollowUpStep.sequence_id == sequence.id,
                FollowUpStep.status.in_(
                    {
                        "pending",
                        "scheduled",
                    }
                ),
            )
        ).all()
    )

    for step in pending_steps:
        step.status = "stopped"
        step.skipped_at = now
        step.skip_reason = reason
        step.updated_at = now

    db.commit()
    db.refresh(sequence)

    return sequence


def pause_sequence(
    db: Session,
    sequence: FollowUpSequence,
) -> FollowUpSequence:

    if sequence.status != "active":
        raise ValueError(
            "Only active sequences can be paused."
        )

    sequence.status = "paused"
    sequence.updated_at = (
        datetime.now(timezone.utc)
    )

    db.commit()
    db.refresh(sequence)

    return sequence


def resume_sequence(
    db: Session,
    sequence: FollowUpSequence,
) -> FollowUpSequence:

    if sequence.status != "paused":
        raise ValueError(
            "Only paused sequences can be resumed."
        )

    blocked, reason = _has_blocking_delivery_event(
        db=db,
        user_id=sequence.user_id,
        lead_id=sequence.lead_id,
    )

    if blocked:
        return stop_sequence(
            db=db,
            sequence=sequence,
            reason=reason or "delivery_event",
        )

    sequence.status = "active"
    sequence.updated_at = (
        datetime.now(timezone.utc)
    )

    db.commit()
    db.refresh(sequence)

    return sequence


def get_ready_steps(
    db: Session,
    limit: int = 20,
) -> list[FollowUpStep]:

    now = datetime.now(timezone.utc)

    statement = (
        select(FollowUpStep)
        .join(
            FollowUpSequence,
            FollowUpSequence.id
            == FollowUpStep.sequence_id,
        )
        .where(
            FollowUpStep.status == "pending",
            FollowUpStep.scheduled_at <= now,
            FollowUpSequence.status == "active",
        )
        .order_by(
            FollowUpStep.scheduled_at.asc()
        )
        .limit(limit)
    )

    return list(
        db.scalars(statement).all()
    )


def _conversation_context(
    db: Session,
    sequence: FollowUpSequence,
) -> list[dict]:
    """Return every sent message so a fresh follow-up can avoid repetition."""
    deliveries = list(db.scalars(
        select(EmailDelivery).where(
            EmailDelivery.user_id == sequence.user_id,
            EmailDelivery.lead_id == sequence.lead_id,
            EmailDelivery.status.in_({"sent", "delivered", "opened", "clicked"}),
        ).order_by(EmailDelivery.sent_at.asc())
    ).all())
    return [{"subject": item.subject, "body_text": item.body_text or ""} for item in deliveries]


async def generate_and_queue_ready_step(
    db: Session,
    step: FollowUpStep,
) -> FollowUpStep:
    """At due time: re-check stop conditions, generate, validate, then queue."""
    sequence = db.get(FollowUpSequence, step.sequence_id)
    if not sequence or sequence.status != "active":
        return step
    blocked, reason = _has_blocking_delivery_event(db, sequence.user_id, sequence.lead_id)
    if blocked or (sequence.stop_on_reply and _has_reply(db, sequence.user_id, sequence.lead_id)):
        stop_sequence(db, sequence, reason or "reply")
        return step

    initial_delivery = db.scalar(select(EmailDelivery).where(
        EmailDelivery.id == sequence.initial_delivery_id,
        EmailDelivery.user_id == sequence.user_id,
    ))
    if not initial_delivery or _is_suppressed(db, sequence.user_id, initial_delivery.recipient_email):
        stop_sequence(db, sequence, "suppression" if initial_delivery else "initial_delivery_missing")
        return step

    # A scheduler retry must never generate/queue a second email for one step.
    if step.queue_id:
        return step
    history = _conversation_context(db, sequence)
    draft = await generate_email_draft(
        db=db,
        user_id=sequence.user_id,
        lead_id=sequence.lead_id,
        request=AIEmailGenerateRequest(
            email_type="follow_up",
            tone="professional",
            length="concise",
            prior_messages=history,
            follow_up_number=step.step_number,
        ),
    )
    # Scheduler-created drafts are validated inside generate_email_draft;
    # approval here is system approval, not reuse of an old user draft.
    draft.status = "approved"
    db.commit()
    queue_item = create_queue_item(
        db=db,
        user_id=sequence.user_id,
        draft=draft,
        email_account_id=initial_delivery.email_account_id,
        scheduled_at=datetime.now(timezone.utc),
        priority=100,
        queue_type="follow_up",
    )
    queue_item.metadata_json = {
        "created_from": "dynamic_follow_up_step",
        "sequence_id": str(sequence.id),
        "step_id": str(step.id),
        "step_number": step.step_number,
        "generated_at_due_time": True,
    }
    step.draft_id = draft.id
    step.queue_id = queue_item.id
    step.status = "queued"
    step.updated_at = datetime.now(timezone.utc)
    sequence.current_step = step.step_number
    sequence.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(step)
    return step


def queue_ready_step(
    db: Session,
    step: FollowUpStep,
) -> FollowUpStep:

    sequence = db.scalar(
        select(FollowUpSequence).where(
            FollowUpSequence.id
            == step.sequence_id
        )
    )

    if not sequence:
        raise LookupError(
            "Follow-up sequence not found."
        )

    if sequence.status != "active":
        raise ValueError(
            "Follow-up sequence is not active."
        )

    blocked, reason = _has_blocking_delivery_event(
        db=db,
        user_id=sequence.user_id,
        lead_id=sequence.lead_id,
    )

    if blocked:
        stop_sequence(
            db=db,
            sequence=sequence,
            reason=reason or "delivery_event",
        )

        return step

    if sequence.stop_on_reply and _has_reply(db, sequence.user_id, sequence.lead_id):
        stop_sequence(db=db, sequence=sequence, reason="reply")
        return step

    draft = db.scalar(
        select(AIEmailDraft).where(
            AIEmailDraft.id == step.draft_id,
            AIEmailDraft.user_id == step.user_id,
        )
    )

    if not draft:
        raise ValueError("This dynamic follow-up must be generated by the scheduler.")

    if _is_suppressed(
        db,
        sequence.user_id,
        _get_recipient_email(
            db,
            sequence.initial_delivery_id,
        ),
    ):
        stop_sequence(
            db=db,
            sequence=sequence,
            reason="suppression",
        )

        return step

    existing_queue = db.scalar(
        select(EmailQueue).where(
            EmailQueue.draft_id == draft.id,
            EmailQueue.status.in_(
                {
                    "pending",
                    "scheduled",
                    "processing",
                    "sent",
                }
            ),
        )
    )

    if existing_queue:
        step.queue_id = existing_queue.id
        step.status = "queued"
        step.updated_at = (
            datetime.now(timezone.utc)
        )

        db.commit()
        db.refresh(step)

        return step

    initial_delivery = db.scalar(
        select(EmailDelivery).where(
            EmailDelivery.id
            == sequence.initial_delivery_id,
            EmailDelivery.user_id
            == sequence.user_id,
        )
    )

    if not initial_delivery:
        raise LookupError(
            "Initial delivery not found."
        )

    queue_item = EmailQueue(
        user_id=sequence.user_id,
        lead_id=sequence.lead_id,
        draft_id=draft.id,
        email_account_id=(
            initial_delivery.email_account_id
        ),
        recipient_email=(
            initial_delivery.recipient_email
        ),
        subject=draft.subject,
        body_text=draft.body_text,
        queue_type="follow_up",
        status="scheduled",
        priority=100,
        scheduled_at=(
            step.scheduled_at
        ),
        attempt_count=0,
        max_attempts=3,
        metadata_json={
            "created_from": "follow_up_step",
            "sequence_id": str(sequence.id),
            "step_id": str(step.id),
            "step_number": step.step_number,
        },
    )

    db.add(queue_item)
    db.flush()

    step.queue_id = queue_item.id
    step.status = "queued"
    step.updated_at = (
        datetime.now(timezone.utc)
    )

    sequence.current_step = step.step_number
    sequence.updated_at = (
        datetime.now(timezone.utc)
    )

    db.commit()
    db.refresh(step)

    return step


def _get_recipient_email(
    db: Session,
    delivery_id: UUID,
) -> str:

    delivery = db.scalar(
        select(EmailDelivery.recipient_email).where(
            EmailDelivery.id == delivery_id
        )
    )

    if not delivery:
        return ""

    return delivery


def complete_sequence_if_needed(
    db: Session,
    sequence: FollowUpSequence,
) -> FollowUpSequence:

    remaining = db.scalar(
        select(FollowUpStep.id).where(
            FollowUpStep.sequence_id == sequence.id,
            FollowUpStep.status.in_(
                {
                    "pending",
                    "scheduled",
                    "queued",
                }
            ),
        )
    )

    if remaining:
        return sequence

    sequence.status = "completed"
    sequence.completed_at = (
        datetime.now(timezone.utc)
    )
    sequence.updated_at = (
        datetime.now(timezone.utc)
    )

    db.commit()
    db.refresh(sequence)

    return sequence
