from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.services.redis import redis_service
from app.workers.job_types import JobType


def publish_job(
    *,
    job_type: JobType | str,
    payload: dict[str, Any],
    job_id: str | None = None,
) -> dict[str, str]:
    resolved_job_id = job_id or str(uuid4())

    stream_message_id = redis_service.add_job(
        job_id=resolved_job_id,
        job_type=str(job_type),
        payload=payload,
    )

    return {
        "job_id": resolved_job_id,
        "stream_message_id": stream_message_id,
    }