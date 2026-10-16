from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.campaign import Campaign, CampaignLead
from app.models.email_account import EmailAccount
from app.models.lead import Lead
from app.schemas.campaign import CampaignCreate


ACTIVE_ACCOUNT_STATUSES = {
    "active",
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _validate_time(
    value: str,
    field_name: str,
) -> str:
    try:
        hour, minute = value.split(":")
        hour_int = int(hour)
        minute_int = int(minute)

        if not (
            0 <= hour_int <= 23
            and 0 <= minute_int <= 59
        ):
            raise ValueError
    except (ValueError, TypeError):
        raise ValueError(
            f"Invalid {field_name}. Use HH:MM format."
        )

    return f"{hour_int:02d}:{minute_int:02d}"


def get_campaign(
    db: Session,
    user_id: UUID,
    campaign_id: UUID,
) -> Campaign | None:
    return db.scalar(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.user_id == user_id,
        )
    )


def list_campaigns(
    db: Session,
    user_id: UUID,
) -> list[Campaign]:
    statement = (
        select(Campaign)
        .where(
            Campaign.user_id == user_id
        )
        .order_by(
            Campaign.created_at.desc()
        )
    )

    return list(
        db.scalars(statement).all()
    )


def get_campaign_detail(
    db: Session,
    user_id: UUID,
    campaign_id: UUID,
) -> tuple[Campaign, list[CampaignLead]]:
    campaign = get_campaign(
        db=db,
        user_id=user_id,
        campaign_id=campaign_id,
    )

    if not campaign:
        raise LookupError(
            "Campaign not found."
        )

    campaign_leads = list(
        db.scalars(
            select(CampaignLead)
            .where(
                CampaignLead.campaign_id
                == campaign.id
            )
            .order_by(
                CampaignLead.created_at.asc()
            )
        ).all()
    )

    return campaign, campaign_leads


def get_campaign_detail_enriched(
    db: Session,
    user_id: UUID,
    campaign_id: UUID,
) -> tuple[Campaign, list[dict]]:
    """
    Returns the campaign plus a list of enriched dicts containing:
    - All CampaignLead fields
    - Lead name + email (from leads table)
    - Queue subject, body_text, scheduled_at, queue status (from email_queue)

    Uses batch queries (4 total) instead of N+1 per-lead queries.
    """
    from app.models.ai_email_draft import AIEmailDraft
    from app.models.email_queue import EmailQueue

    campaign = get_campaign(
        db=db,
        user_id=user_id,
        campaign_id=campaign_id,
    )

    if not campaign:
        raise LookupError(
            "Campaign not found."
        )

    # ------------------------------------------------------------------ #
    # 1. Fetch all CampaignLeads for this campaign (1 query)
    # ------------------------------------------------------------------ #
    campaign_leads = list(
        db.scalars(
            select(CampaignLead)
            .where(CampaignLead.campaign_id == campaign.id)
            .order_by(CampaignLead.created_at.asc())
        ).all()
    )

    if not campaign_leads:
        return campaign, []

    # ------------------------------------------------------------------ #
    # 2. Batch-fetch all related Leads (1 query)
    # ------------------------------------------------------------------ #
    lead_ids = list({cl.lead_id for cl in campaign_leads})
    leads_by_id: dict[UUID, Lead] = {
        lead.id: lead
        for lead in db.scalars(
            select(Lead).where(Lead.id.in_(lead_ids))
        ).all()
    }

    # ------------------------------------------------------------------ #
    # 3. Batch-fetch all related EmailQueue items (1 query)
    # ------------------------------------------------------------------ #
    queue_ids = [
        cl.email_queue_id
        for cl in campaign_leads
        if cl.email_queue_id is not None
    ]
    queues_by_id: dict[UUID, EmailQueue] = {}
    if queue_ids:
        queues_by_id = {
            q.id: q
            for q in db.scalars(
                select(EmailQueue).where(EmailQueue.id.in_(queue_ids))
            ).all()
        }

    # ------------------------------------------------------------------ #
    # 4. Batch-fetch all related AIEmailDraft items (1 query)
    # ------------------------------------------------------------------ #
    draft_ids = [
        cl.ai_email_draft_id
        for cl in campaign_leads
        if cl.ai_email_draft_id is not None
    ]
    drafts_by_id: dict[UUID, AIEmailDraft] = {}
    if draft_ids:
        drafts_by_id = {
            d.id: d
            for d in db.scalars(
                select(AIEmailDraft).where(AIEmailDraft.id.in_(draft_ids))
            ).all()
        }

    # ------------------------------------------------------------------ #
    # 5. Batch-fetch all related EmailAccount items (1 query)
    # ------------------------------------------------------------------ #
    account_ids = list({
        cl.email_account_id
        for cl in campaign_leads
        if cl.email_account_id is not None
    })
    accounts_by_id: dict[UUID, EmailAccount] = {}
    if account_ids:
        accounts_by_id = {
            a.id: a
            for a in db.scalars(
                select(EmailAccount).where(EmailAccount.id.in_(account_ids))
            ).all()
        }

    # ------------------------------------------------------------------ #
    # 6. Assemble enriched dicts in Python (no more DB round-trips)
    # ------------------------------------------------------------------ #
    enriched: list[dict] = []

    for cl in campaign_leads:
        lead       = leads_by_id.get(cl.lead_id)
        queue_item = queues_by_id.get(cl.email_queue_id) if cl.email_queue_id else None
        draft      = drafts_by_id.get(cl.ai_email_draft_id) if cl.ai_email_draft_id else None
        account    = accounts_by_id.get(cl.email_account_id) if cl.email_account_id else None

        enriched.append({
            # CampaignLead fields
            "id":               str(cl.id),
            "campaign_id":      str(cl.campaign_id),
            "lead_id":          str(cl.lead_id),
            "email_account_id": str(cl.email_account_id) if cl.email_account_id else None,
            "ai_email_draft_id": str(cl.ai_email_draft_id) if cl.ai_email_draft_id else None,
            "email_queue_id":   str(cl.email_queue_id) if cl.email_queue_id else None,
            "status":           cl.status,
            "scheduled_at":     cl.scheduled_at.isoformat() if cl.scheduled_at else None,
            "last_error":       cl.last_error,
            "created_at":       cl.created_at.isoformat() if cl.created_at else None,
            "updated_at":       cl.updated_at.isoformat() if cl.updated_at else None,
            # Lead info
            "lead_name":     lead.name     if lead else None,
            "lead_email":    lead.email    if lead else None,
            "lead_industry": lead.industry if lead else None,
            "lead_city":     lead.city     if lead else None,
            # Sender email account info
            "sender_email":        account.email        if account else None,
            "sender_display_name": account.display_name if account else None,
            # Email content (queue preferred over draft)
            "email_subject": (
                queue_item.subject   if queue_item else
                (draft.subject       if draft      else None)
            ),
            "email_body": (
                queue_item.body_text if queue_item else
                (draft.body_text     if draft      else None)
            ),
            "queue_status": queue_item.status if queue_item else None,
            "queue_scheduled_at": (
                queue_item.scheduled_at.isoformat()
                if queue_item and queue_item.scheduled_at
                else (cl.scheduled_at.isoformat() if cl.scheduled_at else None)
            ),
            "recipient_email": (
                queue_item.recipient_email if queue_item else
                (lead.email                if lead       else None)
            ),
        })

    return campaign, enriched


def _validate_leads(
    db: Session,
    user_id: UUID,
    lead_ids: list[UUID],
) -> list[Lead]:
    if not lead_ids:
        raise ValueError(
            "At least one lead must be selected."
        )

    unique_ids = list(
        dict.fromkeys(lead_ids)
    )

    leads = list(
        db.scalars(
            select(Lead).where(
                Lead.user_id == user_id,
                Lead.id.in_(unique_ids),
            )
        ).all()
    )

    lead_map = {
        lead.id: lead
        for lead in leads
    }

    missing = [
        str(lead_id)
        for lead_id in unique_ids
        if lead_id not in lead_map
    ]

    if missing:
        raise ValueError(
            "One or more selected leads "
            "do not belong to this user."
        )

    return [
        lead_map[lead_id]
        for lead_id in unique_ids
    ]


def _validate_accounts(
    db: Session,
    user_id: UUID,
    account_ids: list[UUID],
) -> list[EmailAccount]:
    if not account_ids:
        raise ValueError(
            "At least one email account must be selected."
        )

    unique_ids = list(
        dict.fromkeys(account_ids)
    )

    accounts = list(
        db.scalars(
            select(EmailAccount).where(
                EmailAccount.user_id
                == user_id,
                EmailAccount.id.in_(
                    unique_ids
                ),
            )
        ).all()
    )

    account_map = {
        account.id: account
        for account in accounts
    }

    missing = [
        str(account_id)
        for account_id in unique_ids
        if account_id not in account_map
    ]

    if missing:
        raise ValueError(
            "One or more selected email "
            "accounts do not belong to this user."
        )

    inactive = [
        account.email
        for account in accounts
        if account.status
        not in ACTIVE_ACCOUNT_STATUSES
    ]

    if inactive:
        raise ValueError(
            "One or more selected email "
            "accounts are not active."
        )

    return [
        account_map[account_id]
        for account_id in unique_ids
    ]


def create_campaign(
    db: Session,
    user_id: UUID,
    payload: CampaignCreate,
) -> Campaign:
    if (
        payload.delay_max_minutes
        < payload.delay_min_minutes
    ):
        raise ValueError(
            "Maximum delay cannot be smaller "
            "than minimum delay."
        )

    start_time = _validate_time(
        payload.start_time,
        "start_time",
    )

    end_time = _validate_time(
        payload.end_time,
        "end_time",
    )

    # scheduled_start_at validation
    scheduled_start_at = None
    if payload.scheduled_start_at is not None:
        now = _utc_now()
        # Ensure timezone-aware
        sched = payload.scheduled_start_at
        if sched.tzinfo is None:
            from datetime import timezone as _tz
            sched = sched.replace(tzinfo=_tz.utc)
        if sched <= now:
            raise ValueError(
                "scheduled_start_at must be a future datetime."
            )
        scheduled_start_at = sched

    leads = _validate_leads(
        db=db,
        user_id=user_id,
        lead_ids=payload.selected_lead_ids,
    )

    accounts = _validate_accounts(
        db=db,
        user_id=user_id,
        account_ids=payload.email_account_ids,
    )

    total_capacity = sum(
        int(
            account.daily_send_limit or 0
        )
        for account in accounts
    )

    if (
        total_capacity > 0
        and payload.daily_limit
        > total_capacity
    ):
        raise ValueError(
            "Daily limit cannot exceed the "
            "selected accounts' configured capacity."
        )

    # sending_settings mein scheduled_start_at bhi store karo
    sending_settings: dict = {
        "daily_limit": payload.daily_limit,
        "start_time": start_time,
        "end_time": end_time,
        "delay_min_minutes": payload.delay_min_minutes,
        "delay_max_minutes": payload.delay_max_minutes,
        "business_days_only": payload.business_days_only,
    }
    if scheduled_start_at is not None:
        sending_settings["scheduled_start_at"] = (
            scheduled_start_at.isoformat()
        )

    campaign = Campaign(
        user_id=user_id,
        name=payload.name.strip(),
        status="draft",
        selected_lead_count=len(leads),
        email_account_ids=[
            str(account.id)
            for account in accounts
        ],
        sending_settings=sending_settings,
        follow_up_settings=(
            payload.follow_ups
        ),
        metadata_json={
            "created_from":
                "campaign_builder",
            "email_accounts_capacity":
                total_capacity,
        },
    )

    db.add(campaign)
    db.flush()

    for index, lead in enumerate(leads):
        account = accounts[
            index % len(accounts)
        ]

        campaign_lead = CampaignLead(
            campaign_id=campaign.id,
            lead_id=lead.id,
            email_account_id=account.id,
            status="pending_ai",
        )

        db.add(campaign_lead)

    db.commit()
    db.refresh(campaign)

    return campaign


def start_campaign(
    db: Session,
    user_id: UUID,
    campaign_id: UUID,
) -> Campaign:
    campaign = get_campaign(
        db=db,
        user_id=user_id,
        campaign_id=campaign_id,
    )

    if not campaign:
        raise LookupError(
            "Campaign not found."
        )

    if campaign.status == "active":
        return campaign

    if campaign.status == "scheduled":
        # Already waiting — return as-is
        return campaign

    if campaign.status in {
        "completed",
        "cancelled",
    }:
        raise ValueError(
            "This campaign cannot be started again."
        )

    # Check if a future scheduled_start_at is stored
    sched_iso = (
        campaign.sending_settings or {}
    ).get("scheduled_start_at")

    if sched_iso:
        from datetime import timezone as _tz
        try:
            sched_dt = datetime.fromisoformat(sched_iso)
            if sched_dt.tzinfo is None:
                sched_dt = sched_dt.replace(tzinfo=_tz.utc)
        except (ValueError, TypeError):
            sched_dt = None

        if sched_dt and sched_dt > _utc_now():
            # Future date — mark as scheduled, do NOT activate yet
            campaign.status = "scheduled"
            campaign.updated_at = _utc_now()
            db.commit()
            db.refresh(campaign)
            return campaign

    # Immediate start
    campaign.status = "active"
    campaign.started_at = _utc_now()
    campaign.paused_at = None
    campaign.last_error = None
    campaign.updated_at = _utc_now()

    db.execute(
        CampaignLead.__table__.update()
        .where(
            CampaignLead.campaign_id
            == campaign.id,
            CampaignLead.status
            == "paused",
        )
        .values(
            status="pending_ai",
            updated_at=_utc_now(),
        )
    )

    db.commit()
    db.refresh(campaign)

    return campaign


def pause_campaign(
    db: Session,
    user_id: UUID,
    campaign_id: UUID,
) -> Campaign:
    campaign = get_campaign(
        db=db,
        user_id=user_id,
        campaign_id=campaign_id,
    )

    if not campaign:
        raise LookupError(
            "Campaign not found."
        )

    if campaign.status != "active":
        raise ValueError(
            "Only an active campaign can be paused."
        )

    campaign.status = "paused"
    campaign.paused_at = _utc_now()
    campaign.updated_at = _utc_now()

    db.execute(
        CampaignLead.__table__.update()
        .where(
            CampaignLead.campaign_id
            == campaign.id,
            CampaignLead.status
            == "pending_ai",
        )
        .values(
            status="paused",
            updated_at=_utc_now(),
        )
    )

    db.commit()
    db.refresh(campaign)

    return campaign


def resume_campaign(
    db: Session,
    user_id: UUID,
    campaign_id: UUID,
) -> Campaign:
    campaign = get_campaign(
        db=db,
        user_id=user_id,
        campaign_id=campaign_id,
    )

    if not campaign:
        raise LookupError(
            "Campaign not found."
        )

    if campaign.status != "paused":
        raise ValueError(
            "Only a paused campaign can be resumed."
        )

    campaign.status = "active"
    campaign.paused_at = None
    campaign.last_error = None
    campaign.updated_at = _utc_now()

    db.execute(
        CampaignLead.__table__.update()
        .where(
            CampaignLead.campaign_id
            == campaign.id,
            CampaignLead.status
            == "paused",
        )
        .values(
            status="pending_ai",
            updated_at=_utc_now(),
        )
    )

    db.commit()
    db.refresh(campaign)

    return campaign


def cancel_campaign(
    db: Session,
    user_id: UUID,
    campaign_id: UUID,
) -> Campaign:
    campaign = get_campaign(
        db=db,
        user_id=user_id,
        campaign_id=campaign_id,
    )

    if not campaign:
        raise LookupError(
            "Campaign not found."
        )

    if campaign.status in {
        "completed",
        "cancelled",
    }:
        return campaign

    campaign.status = "cancelled"
    campaign.updated_at = _utc_now()

    db.execute(
        CampaignLead.__table__.update()
        .where(
            CampaignLead.campaign_id
            == campaign.id,
            CampaignLead.status.notin_(
                [
                    "sent",
                    "failed",
                    "skipped",
                ]
            ),
        )
        .values(
            status="cancelled",
            updated_at=_utc_now(),
        )
    )

    db.commit()
    db.refresh(campaign)

    return campaign


def delete_campaign(
    db: Session,
    user_id: UUID,
    campaign_id: UUID,
) -> None:
    campaign = get_campaign(
        db=db,
        user_id=user_id,
        campaign_id=campaign_id,
    )

    if not campaign:
        raise LookupError(
            "Campaign not found."
        )

    if campaign.status == "active":
        raise ValueError(
            "Pause or cancel the campaign before deleting it."
        )

    # Delete all campaign leads first (cascade would handle it in the DB
    # but we do it explicitly for clarity and to avoid FK issues in tests)
    db.execute(
        CampaignLead.__table__.delete().where(
            CampaignLead.campaign_id == campaign.id
        )
    )

    db.delete(campaign)
    db.commit()