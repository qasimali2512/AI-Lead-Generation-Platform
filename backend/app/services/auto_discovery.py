"""
Auto-discovery service.

"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.auto_discovery import AutoDiscoverySettings, AutoDiscoveryVisitedCity
from app.schemas.discovery import BusinessDiscoveryResult
from app.services.city_search import (
    TransientSearchError,
    fetch_city_elements,
    filter_already_saved,
    find_city_area,
    load_existing_emails,
    normalize_elements,
    score_business,
)
from app.services.discovery import normalize_industry
from app.services.email_finder import enrich_emails
from app.services.geonames import (
    City,
    GeoData,
    GeoDataUnavailable,
    get_geo_data,
    pick_city,
)
from app.services.leads import save_discovery_results

logger = logging.getLogger("ai-lead-auto-discovery")

CITY_MAX_SECONDS = 200            # ek shehr par ~3 minute
RUN_MAX_SECONDS = 15 * 60         # ek poore run ki hadd
MIN_TIME_FOR_NEW_CITY = 40        # itna waqt bacha ho tabhi naya shehr
MAX_CITIES_PER_RUN = 80
MAX_CONSECUTIVE_FAILURES = 3
ENRICH_CANDIDATE_LIMIT = 400


@dataclass
class RunContext:
    user_id: UUID
    existing_emails: set[str] = field(default_factory=set)


def industry_key(industry: str | None) -> str:
    return " ".join((industry or "").lower().split())[:100]


# =========================================================
# Visited cities (per user + industry)
# =========================================================

def _load_visited(db: Session, user_id: UUID, key: str) -> set[int]:
    rows = db.scalars(
        select(AutoDiscoveryVisitedCity.geoname_id).where(
            AutoDiscoveryVisitedCity.user_id == user_id,
            AutoDiscoveryVisitedCity.industry_key == key,
        )
    ).all()
    db.commit()
    return {int(r) for r in rows}


def _record_visit(db: Session, user_id: UUID, key: str, geoname_id: int, found: int) -> None:
    stmt = (
        pg_insert(AutoDiscoveryVisitedCity)
        .values(user_id=user_id, industry_key=key, geoname_id=geoname_id, found=found)
        .on_conflict_do_update(
            index_elements=["user_id", "industry_key", "geoname_id"],
            set_={"found": found, "visited_at": func.now()},
        )
    )
    db.execute(stmt)
    db.commit()


def clear_visited(db: Session, user_id: UUID, key: str) -> None:
    db.execute(
        delete(AutoDiscoveryVisitedCity).where(
            AutoDiscoveryVisitedCity.user_id == user_id,
            AutoDiscoveryVisitedCity.industry_key == key,
        )
    )
    db.commit()


def count_visited(db: Session, user_id: UUID, key: str) -> int:
    value = db.scalar(
        select(func.count()).select_from(AutoDiscoveryVisitedCity).where(
            AutoDiscoveryVisitedCity.user_id == user_id,
            AutoDiscoveryVisitedCity.industry_key == key,
        )
    ) or 0
    db.commit()
    return int(value)


# =========================================================
# Ek shehr
# =========================================================

async def _discover_city(
    db: Session,
    cfg: AutoDiscoverySettings,
    ctx: RunContext,
    geo: GeoData,
    city: City,
    need: int,
) -> int:
    """Ek shehr se zyada se zyada `need` naye leads save karo. Returns saved count."""
    deadline = time.monotonic() + CITY_MAX_SECONDS
    industry = normalize_industry(cfg.industry or "")

    country_name = geo.country_name(city.country_code)
    state_name = geo.state_name(city)

    queries = [city.name]
    if city.ascii_name and city.ascii_name != city.name:
        queries.append(city.ascii_name)

    location = await find_city_area(
        queries,
        country_code=city.country_code,
        near=(city.latitude, city.longitude),
    )
    elements = await fetch_city_elements(industry, location, deadline=deadline)

    businesses = normalize_elements(
        elements,
        industry,
        city=city.name,
        state=state_name,
        country=country_name,
    )

    # Pehle se saved hatao -- limit lagne se PEHLE
    fresh, _skipped = filter_already_saved(db, cfg.user_id, businesses)

    # "Website" button
    if cfg.require_website:
        fresh = [b for b in fresh if b.website]

    # Is run mein pehle shehron se aaye emails + purane emails
    seen_emails = ctx.existing_emails

    if cfg.require_email:
        with_email: list[BusinessDiscoveryResult] = []
        need_lookup: list[BusinessDiscoveryResult] = []
        for b in fresh:
            if b.email:
                key = b.email.lower()
                if key in seen_emails:
                    continue
                seen_emails.add(key)
                with_email.append(b)
            elif b.website:
                need_lookup.append(b)

        if len(with_email) < need and need_lookup:
            enriched = await enrich_emails(
                need_lookup[:ENRICH_CANDIDATE_LIMIT],
                seen_emails,
                target=need - len(with_email),
                deadline=deadline,
            )
            with_email.extend(enriched)
        fresh = with_email
    else:
        unique: list[BusinessDiscoveryResult] = []
        for b in fresh:
            if b.email:
                key = b.email.lower()
                if key in seen_emails:
                    continue
                seen_emails.add(key)
            unique.append(b)
        fresh = unique

    fresh.sort(key=score_business, reverse=True)
    selected = fresh[:need]
    if not selected:
        return 0

    result = save_discovery_results(db=db, user_id=cfg.user_id, businesses=selected)
    return int(result["created"])


# =========================================================
# Poora run
# =========================================================

def _city_label(geo: GeoData, city: City) -> str:
    state = geo.state_name(city)
    return ", ".join(p for p in (city.name, state, geo.country_name(city.country_code)) if p)


async def run_for_settings(db: Session, cfg: AutoDiscoverySettings) -> dict:
    if not cfg.industry:
        return {"skipped": True}

    user_id = cfg.user_id
    key = industry_key(cfg.industry)
    batch_size = cfg.batch_size
    countries = {str(c).upper() for c in (cfg.countries or [])}

    run_deadline = time.monotonic() + RUN_MAX_SECONDS

    try:
        geo = await asyncio.to_thread(get_geo_data)
    except GeoDataUnavailable as exc:
        cfg.last_error = str(exc)[:500]
        cfg.last_run_at = datetime.now(timezone.utc)
        db.commit()
        return {"error": cfg.last_error}

    ctx = RunContext(user_id=user_id, existing_emails=load_existing_emails(db, user_id))
    visited = _load_visited(db, user_id, key)
    rng = random.Random()

    saved_total = 0
    tried = 0
    failures = 0
    skip_ids: set[int] = set()
    last_error: str | None = None
    last_label: str | None = None
    progress_reset = False

    while (
        saved_total < batch_size
        and tried < MAX_CITIES_PER_RUN
        and time.monotonic() < run_deadline - MIN_TIME_FOR_NEW_CITY
    ):
        city, status = pick_city(
            geo,
            city_size=cfg.city_size,
            position=cfg.mix_position,
            countries=countries,
            excluded_ids=visited | skip_ids,
            rng=rng,
        )

        if city is None:
            if status == "exhausted" and not progress_reset:
                # Sab shehr ho chuke -- naya round shuru
                clear_visited(db, user_id, key)
                visited = set()
                skip_ids = set()
                progress_reset = True
                continue
            last_error = (
                "No cities match your country / city-size selection."
                if status == "no_match"
                else "All matching cities were tried this round."
            )
            break

        tried += 1
        label = _city_label(geo, city)
        last_label = label
        need = batch_size - saved_total

        try:
            created = await _discover_city(db, cfg, ctx, geo, city, need)
        except (TransientSearchError, TimeoutError) as exc:
            failures += 1
            skip_ids.add(city.geoname_id)
            last_error = f"{label}: {str(exc)[:250]}"
            logger.warning("Auto-discovery transient failure for %s: %s", label, exc)
            if failures >= MAX_CONSECUTIVE_FAILURES:
                break
            continue
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            failures += 1
            skip_ids.add(city.geoname_id)
            last_error = f"{label}: {str(exc)[:250]}"
            logger.exception("Auto-discovery failed for %s", label)
            if failures >= MAX_CONSECUTIVE_FAILURES:
                break
            continue

        failures = 0
        visited.add(city.geoname_id)
        saved_total += created
        logger.info("Auto-discovery %s: %d new leads (%d/%d)", label, created, saved_total, batch_size)

        cfg = db.merge(cfg)
        _record_visit(db, user_id, key, city.geoname_id, created)
        cfg.mix_position = (cfg.mix_position or 0) + 1
        cfg.last_location = label[:255]
        cfg.last_run_found = saved_total
        cfg.total_found = (cfg.total_found or 0) + created
        cfg.last_run_at = datetime.now(timezone.utc)
        cfg.last_error = None
        db.commit()

    cfg = db.merge(cfg)
    if last_label and saved_total == 0:
        cfg.last_location = last_label[:255]
        cfg.last_run_found = 0
    cfg.last_error = last_error
    cfg.last_run_at = datetime.now(timezone.utc)
    db.commit()

    # Auto-campaign: agar leads mile aur threshold meet hua to campaign banao
    try:
        cfg = db.merge(cfg)
        await _maybe_create_auto_campaign(db, cfg, saved_total)
    except Exception:  # noqa: BLE001
        logger.exception("Auto-campaign creation failed after discovery run.")

    return {
        "saved": saved_total,
        "cities_tried": tried,
        "last_location": last_label,
        "error": last_error,
    }


# =========================================================
# Auto-Campaign: leads mile to campaign banao aur bhejo
# =========================================================

async def _maybe_create_auto_campaign(
    db: Session,
    cfg: AutoDiscoverySettings,
    new_leads_count: int,
) -> None:
    """Create one campaign after enough qualified leads accumulate."""
    if (
        not cfg.auto_campaign_enabled
        or cfg.auto_campaign_paused
        or not cfg.auto_campaign_email_account_ids
    ):
        return

    from uuid import UUID as PyUUID
    from sqlalchemy import select as sa_select
    from app.models.lead import Lead
    from app.models.lead_qualification import LeadQualification
    from app.models.email_account import EmailAccount
    from app.models.campaign import Campaign, CampaignLead

    now = datetime.now(timezone.utc)
    target = max(1, int(cfg.auto_campaign_daily_limit))
    threshold = float(cfg.auto_campaign_opportunity_threshold or 0)

    enrolled_ids = set(db.scalars(sa_select(CampaignLead.lead_id)).all())
    available_leads = list(
        db.scalars(
            sa_select(Lead)
            .where(
                Lead.user_id == cfg.user_id,
                Lead.email.is_not(None),
                Lead.email != "",
            )
            .order_by(Lead.created_at.desc())
        ).all()
    )
    available_leads = [
        lead for lead in available_leads if lead.id not in enrolled_ids
    ]
    if not available_leads:
        return

    qualification_by_lead = {
        record.lead_id: record
        for record in db.scalars(
            sa_select(LeadQualification).where(
                LeadQualification.user_id == cfg.user_id,
                LeadQualification.lead_id.in_(
                    [lead.id for lead in available_leads]
                ),
            )
        ).all()
    }
    qualified_leads = [
        lead
        for lead in available_leads
        if (
            qualification_by_lead.get(lead.id) is not None
            and qualification_by_lead[lead.id].total_score >= threshold
        )
    ]
    if len(qualified_leads) < target:
        logger.info(
            "Auto-campaign waiting: %d/%d qualified leads.",
            len(qualified_leads),
            target,
        )
        return

    qualified_leads.sort(
        key=lambda lead: qualification_by_lead[lead.id].total_score,
        reverse=True,
    )
    selected_leads = qualified_leads[:target]

    account_ids = []
    for account_id in cfg.auto_campaign_email_account_ids:
        try:
            account_ids.append(PyUUID(str(account_id)))
        except (ValueError, AttributeError):
            continue
    accounts = list(
        db.scalars(
            sa_select(EmailAccount).where(
                EmailAccount.user_id == cfg.user_id,
                EmailAccount.id.in_(account_ids),
                EmailAccount.status == "active",
            )
        ).all()
    )
    if not accounts:
        logger.warning("Auto-campaign: no active email accounts found.")
        return

    industry_label = (cfg.industry or "Leads").title()
    campaign = Campaign(
        user_id=cfg.user_id,
        name=f"Auto Campaign - {industry_label} {now:%b %d, %Y}",
        status="active",
        started_at=now,
        selected_lead_count=len(selected_leads),
        email_account_ids=[str(account.id) for account in accounts],
        sending_settings={
            "daily_limit": target,
            "start_time": cfg.auto_campaign_start_time or "00:00",
            "end_time": cfg.auto_campaign_end_time or "23:59",
            "delay_min_minutes": 5,
            "delay_max_minutes": 15,
            "business_days_only": False,
        },
        follow_up_settings=[],
        metadata_json={
            "created_from": "auto_discovery",
            "auto_discovery_industry": cfg.industry,
            "minimum_lead_score": threshold,
        },
    )
    db.add(campaign)
    db.flush()

    for index, lead in enumerate(selected_leads):
        db.add(
            CampaignLead(
                campaign_id=campaign.id,
                lead_id=lead.id,
                email_account_id=accounts[index % len(accounts)].id,
                status="pending_ai",
            )
        )

    cfg.auto_campaign_last_created_at = now
    cfg.auto_campaigns_created = (cfg.auto_campaigns_created or 0) + 1
    cfg.enabled = False
    cfg.auto_campaign_paused = True
    db.commit()
    logger.info(
        "Auto-campaign created: '%s' with %d leads; discovery paused.",
        campaign.name,
        len(selected_leads),
    )


# =========================================================
# Scheduler / API helpers
# =========================================================

def _claim(db: Session, cfg: AutoDiscoverySettings) -> bool:
    """Atomic claim -- do instances ek hi user ko ek saath run na karein."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=cfg.run_every_minutes)
    result = db.execute(
        update(AutoDiscoverySettings)
        .where(
            AutoDiscoverySettings.id == cfg.id,
            or_(
                AutoDiscoverySettings.last_run_at.is_(None),
                AutoDiscoverySettings.last_run_at <= cutoff,
            ),
        )
        .values(last_run_at=now)
    )
    db.commit()
    return (result.rowcount or 0) == 1


def _reset_daily_auto_campaigns(db: Session) -> int:
    """Resume discovery after the previous auto-campaign day is finished."""
    from app.models.campaign import Campaign

    now = datetime.now(timezone.utc)
    reset_count = 0
    settings = list(
        db.scalars(
            select(AutoDiscoverySettings).where(
                    AutoDiscoverySettings.auto_campaign_paused.is_(True),
                    AutoDiscoverySettings.auto_campaign_last_created_at.is_not(None),
            )
        ).all()
    )

    for cfg in settings:
        if not cfg.auto_campaign_last_created_at:
            continue
        if cfg.auto_campaign_last_created_at.astimezone(timezone.utc).date() >= now.date():
            continue

        open_campaign = False
        campaigns = db.scalars(
            select(Campaign).where(
                Campaign.user_id == cfg.user_id,
                Campaign.status.in_(("draft", "scheduled", "active", "paused")),
            )
        ).all()
        for campaign in campaigns:
            if (campaign.metadata_json or {}).get("created_from") == "auto_discovery":
                open_campaign = True
                break

        if not open_campaign:
            cfg.enabled = True
            cfg.auto_campaign_paused = False
            reset_count += 1

    if reset_count:
        db.commit()
        logger.info(
            "Auto-campaign daily reset: resumed discovery for %d user(s).",
            reset_count,
        )

    return reset_count


async def run_due_users(db: Session) -> int:
    _reset_daily_auto_campaigns(db)

    due = list(
        db.scalars(
            select(AutoDiscoverySettings).where(
                AutoDiscoverySettings.enabled.is_(True),
                AutoDiscoverySettings.industry.is_not(None),
            )
        ).all()
    )
    db.commit()

    now = datetime.now(timezone.utc)
    ran = 0
    for cfg in due:
        if cfg.last_run_at and cfg.last_run_at + timedelta(
            minutes=cfg.run_every_minutes
        ) > now:
            continue
        if not _claim(db, cfg):
            continue
        db.refresh(cfg)
        # A previous run may already have accumulated the complete target.
        # Check before discovering another city so campaign creation cannot be
        # missed when the final qualified leads were saved by another worker.
        try:
            await _maybe_create_auto_campaign(db, cfg, 0)
        except Exception:
            db.rollback()
            logger.exception(
                "Accumulated auto-campaign check failed for user %s.",
                cfg.user_id,
            )
        db.refresh(cfg)
        if not cfg.enabled:
            ran += 1
            continue
        await run_for_settings(db, cfg)
        ran += 1
    return ran


async def run_now_background(user_id: UUID) -> None:
    """'Run now' button ke liye (background task)."""
    db = SessionLocal()
    try:
        cfg = db.scalar(
            select(AutoDiscoverySettings).where(
                AutoDiscoverySettings.user_id == user_id
            )
        )
        if cfg is None or not cfg.industry:
            return
        await run_for_settings(db, cfg)
    except Exception:  # noqa: BLE001
        logger.exception("Run-now auto-discovery failed.")
    finally:
        db.close()