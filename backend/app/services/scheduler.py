from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.email_queue import EmailQueue
from app.models.follow_up_step import FollowUpStep


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SchedulerService:

    def get_due_email_queue(
        self,
        db: Session,
        batch_size: int,
    ) -> list[EmailQueue]:
        now = utc_now()

        query = (
            select(EmailQueue)
            .where(
                EmailQueue.status.in_(
                    [
                        "pending",
                        "scheduled",
                    ]
                ),
                EmailQueue.scheduled_at <= now,
            )
            .order_by(
                EmailQueue.priority.asc(),
                EmailQueue.scheduled_at.asc(),
            )
            .limit(batch_size)
        )

        return list(
            db.scalars(query).all()
        )

    def get_retryable_email_queue(
        self,
        db: Session,
        batch_size: int,
    ) -> list[EmailQueue]:
        now = utc_now()

        query = (
            select(EmailQueue)
            .where(
                EmailQueue.status == "scheduled",
                EmailQueue.next_retry_at.is_not(None),
                EmailQueue.next_retry_at <= now,
            )
            .order_by(
                EmailQueue.next_retry_at.asc(),
            )
            .limit(batch_size)
        )

        return list(
            db.scalars(query).all()
        )

    def get_due_follow_up_steps(
        self,
        db: Session,
        batch_size: int,
    ) -> list[FollowUpStep]:
        now = utc_now()

        query = (
            select(FollowUpStep)
            .where(
                FollowUpStep.status.in_(
                    [
                        "pending",
                        "scheduled",
                    ]
                ),
                FollowUpStep.scheduled_at <= now,
            )
            .order_by(
                FollowUpStep.scheduled_at.asc(),
            )
            .limit(batch_size)
        )

        return list(
            db.scalars(query).all()
        )

    def claim_email_queue(
        self,
        db: Session,
        queue: EmailQueue,
    ) -> bool:
        if queue.status not in {
            "pending",
            "scheduled",
        }:
            return False

        now = utc_now()

        queue.status = "processing"
        queue.started_at = now
        queue.attempt_count += 1
        queue.last_attempt_at = now
        queue.updated_at = now

        db.flush()

        return True

    def claim_follow_up_step(
        self,
        db: Session,
        step: FollowUpStep,
    ) -> bool:
        if step.status not in {
            "pending",
            "scheduled",
        }:
            return False

        step.status = "queued"
        step.updated_at = utc_now()

        db.flush()

        return True

    def process_due_jobs(
        self,
        db: Session,
        batch_size: int,
    ) -> dict:
        email_jobs = self.get_due_email_queue(
            db=db,
            batch_size=batch_size,
        )

        retry_jobs = self.get_retryable_email_queue(
            db=db,
            batch_size=batch_size,
        )

        follow_up_steps = self.get_due_follow_up_steps(
            db=db,
            batch_size=batch_size,
        )

        claimed_email_jobs = 0
        claimed_retry_jobs = 0
        claimed_follow_ups = 0

        normal_queue_ids = {
            queue.id
            for queue in email_jobs
        }

        for queue in email_jobs:
            if self.claim_email_queue(
                db=db,
                queue=queue,
            ):
                claimed_email_jobs += 1

        for queue in retry_jobs:
            if queue.id in normal_queue_ids:
                continue

            if self.claim_email_queue(
                db=db,
                queue=queue,
            ):
                claimed_retry_jobs += 1

        for step in follow_up_steps:
            if self.claim_follow_up_step(
                db=db,
                step=step,
            ):
                claimed_follow_ups += 1

        db.commit()

        return {
            "email_jobs_found": len(
                email_jobs
            ),
            "retry_jobs_found": len(
                retry_jobs
            ),
            "follow_up_steps_found": len(
                follow_up_steps
            ),
            "email_jobs_claimed": claimed_email_jobs,
            "retry_jobs_claimed": claimed_retry_jobs,
            "follow_up_steps_claimed": claimed_follow_ups,
        }


scheduler_service = SchedulerService()