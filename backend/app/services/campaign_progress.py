"""
Keeps campaign / campaign-lead / follow-up statuses in sync with what the
email queue actually did.

Before this module existed:
  * CampaignLead never changed from "queued" to "sent"
  * FollowUpStep stayed "queued" after the follow-up was sent
  * FollowUpSequence was never marked "completed"
  * Campaign was marked "completed" as soon as emails were *queued*

Now a campaign becomes "completed" only when:
  1. every campaign lead is in a final state (sent / failed / skipped /
     cancelled), AND
  2. every follow-up sequence of the campaign is finished
     (completed / stopped / cancelled) - i.e. first follow-up (3 days),
     second follow-up (8 days) etc. have all been sent or stopped.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.campaign import Campaign, CampaignLead
from app.models.email_queue import EmailQueue
from app.models.follow_up_sequence import FollowUpSequence
from app.models.follow_up_step import FollowUpStep

logger = logging.getLogger("ai-lead-scheduler")

# Lead states that still need work.
LEAD_OPEN_STATUSES = {
    "pending_ai",
    "generating_ai",
    "retry",
    "queued",
    "paused",
}

# Sequence states that are still running.
SEQUENCE_OPEN_STATUSES = {"active", "paused"}

STEP_OPEN_STATUSES = {"pending", "scheduled", "queued"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _queue_is_dead(queue: EmailQueue) -> bool:
    """Failed and no retries left."""
    return queue.status == "failed" and (
        queue.attempt_count >= (queue.max_attempts or 1)
    )


def sync_campaign_lead_statuses(db: Session) -> int:
    """queued -> sent / failed, based on the linked email_queue row."""
    rows = db.execute(
        select(CampaignLead, EmailQueue)
        .join(EmailQueue, EmailQueue.id == CampaignLead.email_queue_id)
        .where(CampaignLead.status == "queued")
    ).all()

    changed = 0
    now = _now()

    for campaign_lead, queue in rows:
        if queue.status == "sent":
            campaign_lead.status = "sent"
            campaign_lead.last_error = None
        elif _queue_is_dead(queue):
            campaign_lead.status = "failed"
            campaign_lead.last_error = (queue.last_error or "Send failed.")[:2000]
        elif queue.status in {"cancelled", "canceled"}:
            campaign_lead.status = "cancelled"
        else:
            continue

        campaign_lead.updated_at = now
        changed += 1

    if changed:
        db.commit()

    return changed


def sync_follow_up_statuses(db: Session) -> int:
    """
    Follow-up step queued -> sent / failed, then close sequences that have no
    open steps left.
    """
    now = _now()
    changed = 0

    rows = db.execute(
        select(FollowUpStep, EmailQueue)
        .join(EmailQueue, EmailQueue.id == FollowUpStep.queue_id)
        .where(FollowUpStep.status == "queued")
    ).all()

    for step, queue in rows:
        if queue.status == "sent":
            step.status = "sent"
            step.sent_at = queue.sent_at or now
        elif _queue_is_dead(queue):
            step.status = "failed"
        else:
            continue

        step.updated_at = now
        changed += 1

    if changed:
        db.commit()

    # Close sequences whose steps are all finished.
    sequences = db.scalars(
        select(FollowUpSequence).where(
            FollowUpSequence.status == "active"
        )
    ).all()

    for sequence in sequences:
        open_step = db.scalar(
            select(FollowUpStep.id)
            .where(
                FollowUpStep.sequence_id == sequence.id,
                FollowUpStep.status.in_(STEP_OPEN_STATUSES),
            )
            .limit(1)
        )
        if open_step:
            continue

        sequence.status = "completed"
        sequence.completed_at = now
        sequence.updated_at = now
        changed += 1

    db.commit()

    return changed


def _campaign_has_open_follow_ups(db: Session, campaign: Campaign) -> bool:
    open_sequence = db.scalar(
        select(FollowUpSequence.id)
        .where(
            FollowUpSequence.status.in_(SEQUENCE_OPEN_STATUSES),
            FollowUpSequence.metadata_json["campaign_id"].astext
            == str(campaign.id),
        )
        .limit(1)
    )
    return open_sequence is not None


def complete_finished_campaigns(db: Session) -> int:
    """Mark active campaigns "completed" when everything is really done."""
    now = _now()
    completed = 0

    campaigns = db.scalars(
        select(Campaign).where(Campaign.status == "active")
    ).all()

    for campaign in campaigns:
        open_lead = db.scalar(
            select(CampaignLead.id)
            .where(
                CampaignLead.campaign_id == campaign.id,
                CampaignLead.status.in_(LEAD_OPEN_STATUSES),
            )
            .limit(1)
        )
        if open_lead:
            continue

        if _campaign_has_open_follow_ups(db, campaign):
            continue

        campaign.status = "completed"
        campaign.completed_at = now
        campaign.updated_at = now
        completed += 1

        logger.info(
            "Campaign completed: id=%s name=%r",
            campaign.id,
            campaign.name,
        )

    if completed:
        db.commit()

    return completed


def sync_campaign_progress(db: Session) -> dict:
    """Run all status syncs. Safe to call on every scheduler cycle."""
    leads = sync_campaign_lead_statuses(db)
    follow_ups = sync_follow_up_statuses(db)
    completed = complete_finished_campaigns(db)

    return {
        "campaign_leads_synced": leads,
        "follow_up_items_synced": follow_ups,
        "campaigns_completed": completed,
    }