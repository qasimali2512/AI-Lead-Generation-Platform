from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.models.email_queue import EmailQueue

def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RecoveryService:

    def calculate_retry_delay(
        self,
        attempt_count: int,
    ) -> int:
        """
        Exponential backoff:

        attempt 1 -> base delay
        attempt 2 -> 2 * base
        attempt 3 -> 4 * base

        Capped at retry_max_delay_seconds.
        """

        exponent = max(
            attempt_count - 1,
            0,
        )

        delay = (
            settings.retry_base_delay_seconds
            * (2 ** exponent)
        )

        delay = min(
            delay,
            settings.retry_max_delay_seconds,
        )

        if settings.retry_jitter_seconds > 0:
            delay += random.randint(
                0,
                settings.retry_jitter_seconds,
            )

        return delay

    def mark_retryable_failure(
        self,
        db: Session,
        queue: EmailQueue,
        error: str,
    ) -> dict[str, Any]:

        now = utc_now()

        queue.last_error = error
        queue.last_error_at = now
        queue.updated_at = now

        if queue.attempt_count >= queue.max_attempts:
            queue.status = "failed"
            queue.next_retry_at = None

            db.flush()

            return {
                "status": "failed",
                "retry": False,
                "attempt_count": queue.attempt_count,
                "max_attempts": queue.max_attempts,
                "next_retry_at": None,
            }

        delay_seconds = self.calculate_retry_delay(
            queue.attempt_count
        )

        next_retry = now + timedelta(
            seconds=delay_seconds
        )

        queue.status = "scheduled"
        queue.next_retry_at = next_retry
        queue.scheduled_at = next_retry

        db.flush()

        return {
            "status": "scheduled",
            "retry": True,
            "attempt_count": queue.attempt_count,
            "max_attempts": queue.max_attempts,
            "delay_seconds": delay_seconds,
            "next_retry_at": next_retry,
        }

    def mark_success(
        self,
        db: Session,
        queue: EmailQueue,
    ) -> None:

        now = utc_now()

        queue.status = "sent"
        queue.sent_at = now
        queue.last_error = None
        queue.last_error_at = None
        queue.next_retry_at = None
        queue.updated_at = now

        db.flush()

    def cancel(
        self,
        db: Session,
        queue: EmailQueue,
        reason: str,
    ) -> None:

        queue.status = "cancelled"
        queue.last_error = reason
        queue.last_error_at = utc_now()
        queue.next_retry_at = None
        queue.updated_at = utc_now()

        db.flush()


recovery_service = RecoveryService()