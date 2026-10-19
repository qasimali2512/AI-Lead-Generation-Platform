from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone

from sqlalchemy import update

from app.config import settings
from app.database import SessionLocal
from app.models.email_queue import EmailQueue
from app.models.website_opportunity import WebsiteOpportunity

from app.services.campaign_progress import sync_campaign_progress
from app.services.gmail_sender import process_due_queue
from app.services.scheduler import scheduler_service


logging.basicConfig(
    level=getattr(
        logging,
        settings.log_level.upper(),
        logging.INFO,
    ),
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(name)s | "
        "%(message)s"
    ),
)

logger = logging.getLogger(
    "ai-lead-scheduler"
)


class SchedulerRunner:

    def __init__(self) -> None:
        self.running = True

    def stop(self) -> None:
        logger.info(
            "Scheduler shutdown requested."
        )
        self.running = False

    def _requeue_retryable_failures(self, db) -> int:
        """
        Stuck 'processing' items (crash se reh gayi) aur
        'failed' items jinka next_retry_at aa gaya ho —
        dono ko wapas 'scheduled' kar do.
        """
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)

        # 1. Processing mein stuck items — 10 min se zyada se
        from datetime import timedelta
        stale_cutoff = now - timedelta(minutes=10)

        result1 = db.execute(
            update(EmailQueue)
            .where(
                EmailQueue.status == "processing",
                EmailQueue.started_at <= stale_cutoff,
                EmailQueue.attempt_count < EmailQueue.max_attempts,
            )
            .values(
                status="scheduled",
                scheduled_at=now,
                updated_at=now,
            )
        )

        # 2. Failed items with retry due
        result2 = db.execute(
            update(EmailQueue)
            .where(
                EmailQueue.status == "failed",
                EmailQueue.next_retry_at.is_not(None),
                EmailQueue.next_retry_at <= now,
                EmailQueue.attempt_count < EmailQueue.max_attempts,
            )
            .values(
                status="scheduled",
                scheduled_at=now,
                updated_at=now,
            )
        )

        db.commit()

        return (result1.rowcount or 0) + (result2.rowcount or 0)

    def _auto_generate_opportunities(self, db) -> int:
        """
        Har cycle mein no-website leads check karo.
        Jinke liye opportunity nahi bani, unke liye background mein
        AI opportunity generate karo (max 5 per cycle taake API rate
        limit na ho aur cycle fast rahe).

        Returns: number of opportunities generated this cycle.
        """
        from sqlalchemy import select
        from app.models.lead import Lead
        from app.models.website_opportunity import WebsiteOpportunity
        from app.config import settings as app_settings
        from app.services.website_opportunity import (
            generate_opportunity,
            PROMPT_VERSION,
        )

        BATCH = 5  # per-cycle limit

        # All users ke liye — group by user
        # Already generated lead IDs
        existing_pairs = set(
            (str(row[0]), str(row[1]))
            for row in db.execute(
                select(
                    WebsiteOpportunity.user_id,
                    WebsiteOpportunity.lead_id,
                )
            ).all()
        )

        # No-website leads without opportunity (across all users)
        candidates = list(
            db.scalars(
                select(Lead)
                .where(Lead.website_status == "no_website")
                .order_by(Lead.created_at.desc())
                .limit(BATCH * 3)   # fetch a few extra, filter in Python
            ).all()
        )

        # Filter to only those without an existing opportunity
        to_process = [
            lead for lead in candidates
            if (str(lead.user_id), str(lead.id)) not in existing_pairs
        ][:BATCH]

        generated = 0

        for lead in to_process:
            try:
                analysis = asyncio.run(
                    generate_opportunity(lead)
                )

                location_parts = [
                    p for p in [lead.city, lead.state, lead.country] if p
                ]

                record = WebsiteOpportunity(
                    user_id=lead.user_id,
                    lead_id=lead.id,
                    opportunity_type="website_development",
                    industry=lead.industry,
                    business_name=lead.name,
                    location_summary=", ".join(location_parts),
                    business_summary=analysis["business_summary"],
                    opportunity_summary=analysis["opportunity_summary"],
                    recommended_solution=analysis["recommended_solution"],
                    sales_angle=analysis["sales_angle"],
                    personalization_points=analysis.get(
                        "personalization_points", []
                    ),
                    suggested_features=analysis.get(
                        "suggested_features", []
                    ),
                    qualification_status="pending",
                    opportunity_status="open",
                    analysis_json=analysis,
                    provider="cloudflare",
                    model=app_settings.cloudflare_ai_model,
                    prompt_version=PROMPT_VERSION,
                )

                db.add(record)
                db.commit()
                generated += 1

                logger.info(
                    "Auto-generated opportunity for lead=%s business=%r",
                    lead.id,
                    lead.name,
                )

            except Exception as exc:
                db.rollback()
                logger.warning(
                    "Auto-opportunity failed for lead=%s: %s",
                    lead.id,
                    str(exc)[:200],
                )

        return generated

    def _reset_daily_counters(self, db) -> int:
        """
        Har cycle mein check karo — jinke accounts ka last_sent_at aaj se
        pehle ka hai, unka sent_today = 0 reset karo.
        """
        from datetime import datetime, timezone, timedelta
        from sqlalchemy import select, update
        from app.models.email_account import EmailAccount

        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        result = db.execute(
            update(EmailAccount)
            .where(
                EmailAccount.sent_today > 0,
                EmailAccount.last_sent_at < today_start,
            )
            .values(sent_today=0)
        )
        if result.rowcount:
            db.commit()
            logger.info("Daily counters reset for %d account(s).", result.rowcount)

        return result.rowcount or 0

    def _activate_scheduled_campaigns(self, db) -> int:
        """
        'scheduled' status wali campaigns jinki scheduled_start_at
        aa gayi ho — unhe 'active' kar do aur process karo.
        """
        from datetime import datetime, timezone
        from sqlalchemy import select
        from app.models.campaign import Campaign, CampaignLead

        now = datetime.now(timezone.utc)

        # Fetch all scheduled campaigns
        scheduled = list(
            db.scalars(
                select(Campaign).where(Campaign.status == "scheduled")
            ).all()
        )

        activated = 0

        for campaign in scheduled:
            sched_iso = (
                campaign.sending_settings or {}
            ).get("scheduled_start_at")

            if not sched_iso:
                # No scheduled time stored — activate immediately
                pass
            else:
                try:
                    sched_dt = datetime.fromisoformat(sched_iso)
                    if sched_dt.tzinfo is None:
                        sched_dt = sched_dt.replace(
                            tzinfo=timezone.utc
                        )
                except (ValueError, TypeError):
                    sched_dt = None

                if sched_dt and sched_dt > now:
                    # Still in the future — skip
                    continue

            # Time has come — activate
            campaign.status = "active"
            campaign.started_at = now
            campaign.paused_at = None
            campaign.last_error = None
            campaign.updated_at = now

            # pending_ai leads jo paused hain unhe wapas pending karo
            db.execute(
                CampaignLead.__table__.update()
                .where(
                    CampaignLead.campaign_id == campaign.id,
                    CampaignLead.status == "paused",
                )
                .values(status="pending_ai", updated_at=now)
            )

            activated += 1
            logger.info(
                "Scheduled campaign activated: id=%s name=%r",
                campaign.id,
                campaign.name,
            )

        if activated:
            db.commit()

        return activated

    async def _process_active_campaigns(self, db) -> int:
        """
        Active campaigns ke pending leads ke liye AI email generate karke
        email queue mein daalta hai.

        Pehle yeh kaam sirf browser se POST /campaigns/{id}/process call
        hone par hota tha. Is liye scheduled campaign "active" to ho jati
        thi, lekin leads "Pending AI" hi rehte the - na email generate hoti
        thi na send. Ab scheduler khud karta hai.

        Per cycle per campaign limited leads (taake sending / follow-ups
        block na hon).
        """
        from sqlalchemy import select
        from app.models.campaign import Campaign, CampaignLead
        from app.services.campaign_automation import process_campaign

        PER_CAMPAIGN_BATCH = 10

        campaigns = list(
            db.scalars(
                select(Campaign)
                .where(
                    Campaign.status == "active",
                    Campaign.id.in_(
                        select(CampaignLead.campaign_id).where(
                            CampaignLead.status.in_(
                                ["pending_ai", "retry", "generating_ai"]
                            )
                        )
                    ),
                )
                .order_by(Campaign.started_at.asc())
            ).all()
        )

        queued = 0

        for campaign in campaigns:
            try:
                result = await process_campaign(
                    db=db,
                    user_id=campaign.user_id,
                    campaign_id=campaign.id,
                    include_failed=False,
                    max_leads=PER_CAMPAIGN_BATCH,
                )
                queued += result.get("queued", 0)
            except Exception:
                db.rollback()
                logger.exception(
                    "Campaign processing failed: id=%s",
                    campaign.id,
                )

        return queued

    async def _queue_due_follow_up_steps(self, db) -> int:
        """
        Due follow-ups ko yahin fresh generate karke actual email queue mein
        daalta hai. Purana flow sirf step ko "queued" mark karta tha, is liye
        Gmail sender ko bhejne ke liye koi queue item milta hi nahi tha.
        """
        steps = scheduler_service.get_due_follow_up_steps(
            db=db,
            batch_size=settings.scheduler_batch_size,
        )

        queued = 0
        from app.services.follow_up import generate_and_queue_ready_step

        for step in steps:
            try:
                result = await generate_and_queue_ready_step(db=db, step=step)
                if result.status == "queued":
                    queued += 1
            except Exception:
                db.rollback()
                logger.exception("Dynamic follow-up generation failed for step=%s", step.id)

        return queued

    def run_once(self) -> dict:
        db = SessionLocal()

        try:
            requeued = self._requeue_retryable_failures(db)

            self._reset_daily_counters(db)

            activated = self._activate_scheduled_campaigns(db)

            campaign_emails_queued = asyncio.run(
                self._process_active_campaigns(db)
            )

            opps_generated = self._auto_generate_opportunities(db)

            follow_ups = asyncio.run(self._queue_due_follow_up_steps(db))

            email_result = asyncio.run(
                process_due_queue(
                    db=db,
                    batch_size=settings.scheduler_batch_size,
                )
            )

            # Sent -> campaign lead "sent", follow-up steps "sent",
            # sequences / campaigns "completed" (only when truly finished).
            progress = sync_campaign_progress(db)

            result = {
                "retries_requeued": requeued,
                "campaigns_activated": activated,
                "campaign_emails_queued": campaign_emails_queued,
                **progress,
                "opportunities_generated": opps_generated,
                "follow_up_steps_queued": follow_ups,
                "emails_processed": email_result["processed"],
                "emails_sent": email_result["sent"],
                "emails_failed": email_result["failed"],
            }

            logger.info(
                "Scheduler cycle: %s",
                result,
            )

            for item in email_result["results"]:
                if not item["success"]:
                    logger.error(
                        "Email to %s failed: %s",
                        item["recipient"],
                        item["error"],
                    )

            return result

        except Exception:
            db.rollback()

            logger.exception(
                "Scheduler cycle failed."
            )

            return {
                "error": True,
            }

        finally:
            db.close()

    def run(self) -> None:
        logger.info(
            "Starting scheduler."
        )

        logger.info(
            "Interval: %s seconds",
            settings.scheduler_interval_seconds,
        )

        while self.running:
            self.run_once()

            time.sleep(
                settings.scheduler_interval_seconds
            )

        logger.info(
            "Scheduler stopped."
        )


if __name__ == "__main__":
    runner = SchedulerRunner()

    try:
        runner.run()

    except KeyboardInterrupt:
        runner.stop()