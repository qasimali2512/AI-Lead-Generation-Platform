from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.campaign import Campaign, CampaignLead
from app.models.email_account import EmailAccount
from app.models.lead import Lead
from app.schemas.ai_email import AIEmailGenerateRequest
from app.services.ai_email import generate_email_draft
from app.services.email_queue import create_queue_item


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_time(value: str) -> tuple[int, int]:
    hour, minute = value.split(":")
    return int(hour), int(minute)


def _next_schedule_time(
    campaign: Campaign,
    previous_time: datetime | None = None,
) -> datetime:
    settings = campaign.sending_settings or {}

    delay_min = int(settings.get("delay_min_minutes", 5))
    delay_max = int(settings.get("delay_max_minutes", 15))
    delay_min = max(delay_min, 0)
    delay_max = max(delay_max, delay_min)

    now = _utc_now()

    if previous_time is None:
        # First email — send as soon as possible (small random delay)
        delay = random.randint(delay_min, max(delay_min, 1))
        return now + timedelta(minutes=delay)

    # Subsequent emails — add random delay to previous
    delay = random.randint(delay_min, delay_max)
    scheduled = previous_time + timedelta(minutes=delay)

    # If scheduled is in the past (e.g. previous campaign run),
    # reset to now + delay
    if scheduled < now:
        scheduled = now + timedelta(minutes=delay)

    return scheduled


def _get_campaign_lead(
    db: Session,
    user_id: UUID,
    campaign_lead_id: UUID,
) -> CampaignLead | None:
    statement = (
        select(CampaignLead)
        .join(
            Campaign,
            Campaign.id
            == CampaignLead.campaign_id,
        )
        .where(
            CampaignLead.id
            == campaign_lead_id,
            Campaign.user_id
            == user_id,
        )
    )

    return db.scalar(statement)


def _get_lead(
    db: Session,
    user_id: UUID,
    lead_id: UUID,
) -> Lead | None:
    return db.scalar(
        select(Lead).where(
            Lead.id == lead_id,
            Lead.user_id == user_id,
        )
    )


def _get_email_account(
    db: Session,
    user_id: UUID,
    account_id: UUID,
) -> EmailAccount | None:
    return db.scalar(
        select(EmailAccount).where(
            EmailAccount.id == account_id,
            EmailAccount.user_id == user_id,
        )
    )


def _build_ai_request(
    campaign: Campaign,
    account: EmailAccount,
    lead: Lead,
) -> AIEmailGenerateRequest:
    metadata = (
        campaign.metadata_json
        if campaign.metadata_json
        else {}
    )

    sender_name = (
        metadata.get("sender_name")
        or account.display_name
        or ""
    )

    sender_company = (
        metadata.get("sender_company")
        or ""
    )

    sender_service = (
        metadata.get("sender_service")
        or "website development and SEO services"
    )

    return AIEmailGenerateRequest(
        email_type="initial_outreach",
        sender_name=str(sender_name),
        sender_company=str(sender_company),
        sender_service=str(sender_service),
        call_to_action=(
            "If you would like, I can send over "
            "the specific findings and suggested "
            "next steps."
        ),
    )


async def process_campaign_lead(
    db: Session,
    user_id: UUID,
    campaign_lead_id: UUID,
    scheduled_at: datetime | None = None,
) -> CampaignLead:
    campaign_lead = _get_campaign_lead(
        db=db,
        user_id=user_id,
        campaign_lead_id=campaign_lead_id,
    )

    if not campaign_lead:
        raise LookupError(
            "Campaign lead not found."
        )

    # The background worker and the manual /process endpoint can run at the
    # same time; never generate a second email for a lead that is already
    # being handled / queued / sent.
    if campaign_lead.status not in {
        "pending_ai",
        "retry",
        "failed",
    }:
        return campaign_lead

    campaign = db.scalar(
        select(Campaign).where(
            Campaign.id
            == campaign_lead.campaign_id,
            Campaign.user_id
            == user_id,
        )
    )

    if not campaign:
        raise LookupError(
            "Campaign not found."
        )

    if campaign.status != "active":
        return campaign_lead

    lead = _get_lead(
        db=db,
        user_id=user_id,
        lead_id=campaign_lead.lead_id,
    )

    if not lead:
        campaign_lead.status = "failed"
        campaign_lead.last_error = (
            "Lead not found."
        )
        campaign_lead.updated_at = _utc_now()

        db.commit()
        db.refresh(campaign_lead)

        return campaign_lead

    if not lead.email:
        campaign_lead.status = "skipped"
        campaign_lead.last_error = (
            "Lead has no email address."
        )
        campaign_lead.updated_at = _utc_now()

        db.commit()
        db.refresh(campaign_lead)

        return campaign_lead

    if not campaign_lead.email_account_id:
        campaign_lead.status = "failed"
        campaign_lead.last_error = (
            "No email account assigned."
        )
        campaign_lead.updated_at = _utc_now()

        db.commit()
        db.refresh(campaign_lead)

        return campaign_lead

    account = _get_email_account(
        db=db,
        user_id=user_id,
        account_id=campaign_lead.email_account_id,
    )

    if not account:
        campaign_lead.status = "failed"
        campaign_lead.last_error = (
            "Email account not found."
        )
        campaign_lead.updated_at = _utc_now()

        db.commit()
        db.refresh(campaign_lead)

        return campaign_lead

    if account.status != "active":
        campaign_lead.status = "failed"
        campaign_lead.last_error = (
            "Email account is not active."
        )
        campaign_lead.updated_at = _utc_now()

        db.commit()
        db.refresh(campaign_lead)

        return campaign_lead

    campaign_lead.status = "generating_ai"
    campaign_lead.last_error = None
    campaign_lead.updated_at = _utc_now()

    db.commit()

    try:
        ai_request = _build_ai_request(
            campaign=campaign,
            account=account,
            lead=lead,
        )

        draft = await generate_email_draft(
            db=db,
            user_id=user_id,
            lead_id=lead.id,
            request=ai_request,
        )

        draft.status = "approved"

        db.commit()
        db.refresh(draft)

        campaign_lead.ai_email_draft_id = draft.id
        campaign_lead.status = "queued"
        campaign_lead.updated_at = _utc_now()

        # The batch planner passes a unique, cumulative send time.  Without
        # it every lead calculated "now" independently and all emails became
        # due at once.
        if scheduled_at is None:
            scheduled_at = _next_schedule_time(campaign=campaign)

        queue_item = create_queue_item(
            db=db,
            user_id=user_id,
            draft=draft,
            email_account_id=account.id,
            scheduled_at=scheduled_at,
            priority=100,
            queue_type="initial",
        )

        campaign_lead.email_queue_id = queue_item.id
        campaign_lead.scheduled_at = (
            scheduled_at
        )
        campaign_lead.status = "queued"
        campaign_lead.updated_at = _utc_now()

        db.commit()
        db.refresh(campaign_lead)

        return campaign_lead

    except Exception as exc:
        db.rollback()

        campaign_lead = _get_campaign_lead(
            db=db,
            user_id=user_id,
            campaign_lead_id=campaign_lead_id,
        )

        if not campaign_lead:
            raise

        campaign_lead.status = "failed"
        campaign_lead.last_error = str(exc)[:2000]
        campaign_lead.updated_at = _utc_now()

        db.commit()
        db.refresh(campaign_lead)

        return campaign_lead


async def process_campaign(
    db: Session,
    user_id: UUID,
    campaign_id: UUID,
    include_failed: bool = True,
    max_leads: int | None = None,
) -> dict:
    """
    Generate AI emails and queue them for a campaign's pending leads.

    include_failed: manual /process call retries failed leads too. The
        background worker passes False, otherwise a permanently failing
        lead would be retried on every scheduler cycle.
    max_leads: cap per call so one big campaign cannot block the scheduler
        (sending + follow-ups) for minutes.
    """
    campaign = db.scalar(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.user_id == user_id,
        )
    )

    if not campaign:
        raise LookupError(
            "Campaign not found."
        )

    if campaign.status != "active":
        raise ValueError(
            "Campaign must be active."
        )

    # Leads stuck in "generating_ai" (for example because the browser
    # request was cancelled or the server restarted mid-run) would never
    # be picked up again, so put them back into the retry state.
    stale_before = _utc_now() - timedelta(minutes=5)

    stuck_leads = db.scalars(
        select(CampaignLead).where(
            CampaignLead.campaign_id == campaign.id,
            CampaignLead.status == "generating_ai",
            CampaignLead.updated_at < stale_before,
        )
    ).all()

    for stuck in stuck_leads:
        stuck.status = "retry"
        stuck.updated_at = _utc_now()

    if stuck_leads:
        db.commit()

    retry_statuses = ["pending_ai", "retry"]
    if include_failed:
        retry_statuses.append("failed")

    lead_query = (
        select(CampaignLead)
        .where(
            CampaignLead.campaign_id == campaign.id,
            CampaignLead.status.in_(retry_statuses),
        )
        .order_by(CampaignLead.created_at.asc())
    )
    if max_leads:
        lead_query = lead_query.limit(max_leads)

    campaign_leads = list(db.scalars(lead_query).all())

    processed = 0
    queued = 0
    failed = 0
    skipped = 0

    # Resume after the last item already planned for this campaign.  This is
    # also important if a failed lead is retried later.
    previous_scheduled_at = max(
        (
            lead.scheduled_at
            for lead in db.scalars(
                select(CampaignLead).where(
                    CampaignLead.campaign_id == campaign.id,
                    CampaignLead.scheduled_at.is_not(None),
                )
            ).all()
            if lead.scheduled_at is not None
        ),
        default=None,
    )
    if previous_scheduled_at and previous_scheduled_at < _utc_now():
        previous_scheduled_at = None

    for campaign_lead in campaign_leads:
        processed += 1

        planned_at = _next_schedule_time(
            campaign=campaign,
            previous_time=previous_scheduled_at,
        )

        try:
            result = await process_campaign_lead(
                db=db,
                user_id=user_id,
                campaign_lead_id=campaign_lead.id,
                scheduled_at=planned_at,
            )
        except Exception:
            # e.g. the database dropped the connection mid-run. Do not
            # abort the whole campaign; this lead stays in
            # "generating_ai" and is retried on the next process call.
            db.rollback()
            failed += 1
            continue

        if result.status == "queued":
            queued += 1
            previous_scheduled_at = planned_at
        elif result.status == "failed":
            failed += 1
        elif result.status == "skipped":
            skipped += 1

        db.expire_all()

        current_campaign = db.scalar(
            select(Campaign).where(
                Campaign.id == campaign.id,
                Campaign.user_id == user_id,
            )
        )

        if (
            not current_campaign
            or current_campaign.status != "active"
        ):
            break

    # NOTE: the campaign is NOT marked "completed" here any more.  Queued
    # is not sent, and follow-ups are still to come.  Completion is decided
    # by app.services.campaign_progress.sync_campaign_progress() once every
    # lead is sent/failed/skipped and every follow-up sequence has finished.

    return {
        "campaign_id": str(campaign_id),
        "processed": processed,
        "queued": queued,
        "failed": failed,
        "skipped": skipped,
    }