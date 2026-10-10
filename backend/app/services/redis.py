from __future__ import annotations

from typing import Any

import redis
from redis import Redis

from app.config import settings


class RedisService:
    def __init__(self) -> None:
        self.client: Redis = redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            health_check_interval=30,
            socket_connect_timeout=5,
            socket_timeout=10,
        )

    def ping(self) -> bool:
        return bool(self.client.ping())

    def ensure_consumer_group(self) -> None:
        try:
            self.client.xgroup_create(
                name=settings.redis_stream_name,
                groupname=settings.redis_consumer_group,
                id="0",
                mkstream=True,
            )
        except redis.ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    def add_job(
        self,
        *,
        job_id: str,
        job_type: str,
        payload: dict[str, Any],
    ) -> str:
        return self.client.xadd(
            settings.redis_stream_name,
            {
                "job_id": job_id,
                "job_type": job_type,
                "payload": self._serialize_payload(payload),
            },
        )

    def read_jobs(
        self,
        *,
        count: int | None = None,
        block_ms: int | None = None,
    ):
        self.ensure_consumer_group()

        return self.client.xreadgroup(
            groupname=settings.redis_consumer_group,
            consumername=settings.redis_consumer_name,
            streams={
                settings.redis_stream_name: ">"
            },
            count=count or settings.worker_batch_size,
            block=(
                block_ms
                if block_ms is not None
                else settings.worker_block_ms
            ),
        )

    def acknowledge(self, message_id: str) -> int:
        return self.client.xack(
            settings.redis_stream_name,
            settings.redis_consumer_group,
            message_id,
        )

    def delete_message(self, message_id: str) -> int:
        return self.client.xdel(
            settings.redis_stream_name,
            message_id,
        )

    @staticmethod
    def _serialize_payload(
        payload: dict[str, Any],
    ) -> str:
        import json

        return json.dumps(
            payload,
            separators=(",", ":"),
            default=str,
        )

    @staticmethod
    def deserialize_payload(value: str) -> dict[str, Any]:
        import json

        return json.loads(value)


redis_service = RedisService()