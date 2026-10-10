from __future__ import annotations

import logging
from typing import Any

from app.workers.job_types import JobType


logger = logging.getLogger(__name__)


class JobProcessor:
    async def process(
        self,
        job_type: str,
        payload: dict[str, Any],
    ) -> None:
        if job_type == JobType.EMAIL_SEND:
            await self.process_email_send(payload)
            return

        if job_type == JobType.FOLLOW_UP:
            await self.process_follow_up(payload)
            return

        if job_type == JobType.REPLY_SYNC:
            await self.process_reply_sync(payload)
            return

        if job_type == JobType.DELIVERY_SYNC:
            await self.process_delivery_sync(payload)
            return

        if job_type == JobType.WEBSITE_SCAN:
            await self.process_website_scan(payload)
            return

        if job_type == JobType.AI_ANALYSIS:
            await self.process_ai_analysis(payload)
            return

        raise ValueError(
            f"Unsupported job type: {job_type}"
        )

    async def process_email_send(
        self,
        payload: dict[str, Any],
    ) -> None:
        logger.info(
            "Email send job received: %s",
            payload,
        )

        # Actual email provider sending will be connected
        # after the email provider/OAuth implementation.

    async def process_follow_up(
        self,
        payload: dict[str, Any],
    ) -> None:
        logger.info(
            "Follow-up job received: %s",
            payload,
        )

    async def process_reply_sync(
        self,
        payload: dict[str, Any],
    ) -> None:
        logger.info(
            "Reply sync job received: %s",
            payload,
        )

    async def process_delivery_sync(
        self,
        payload: dict[str, Any],
    ) -> None:
        logger.info(
            "Delivery sync job received: %s",
            payload,
        )

    async def process_website_scan(
        self,
        payload: dict[str, Any],
    ) -> None:
        logger.info(
            "Website scan job received: %s",
            payload,
        )

    async def process_ai_analysis(
        self,
        payload: dict[str, Any],
    ) -> None:
        logger.info(
            "AI analysis job received: %s",
            payload,
        )


job_processor = JobProcessor()