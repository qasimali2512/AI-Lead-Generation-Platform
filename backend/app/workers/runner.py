from __future__ import annotations

import asyncio
import logging
import signal

from app.services.redis import redis_service
from app.workers.processor import job_processor


logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(name)s | "
        "%(message)s"
    ),
)

logger = logging.getLogger("ai-lead-worker")


class WorkerRunner:
    def __init__(self) -> None:
        self.running = True

    def stop(self, *_args) -> None:
        logger.info("Worker shutdown requested.")
        self.running = False

    async def run(self) -> None:
        logger.info("Starting AI Lead Generation worker.")

        redis_service.ensure_consumer_group()

        logger.info(
            "Redis stream: %s",
            redis_service.client.connection_pool.connection_kwargs.get(
                "host"
            ),
        )

        logger.info("Consumer group ready.")

        while self.running:
            try:
                results = redis_service.read_jobs()

                if not results:
                    continue

                for _stream_name, messages in results:
                    for message_id, fields in messages:
                        await self.handle_message(
                            message_id,
                            fields,
                        )

            except asyncio.CancelledError:
                logger.info(
                    "Worker task cancelled."
                )
                break

            except Exception:
                logger.exception(
                    "Worker loop error."
                )

                await asyncio.sleep(5)

        logger.info(
            "AI Lead Generation worker stopped."
        )

    async def handle_message(
        self,
        message_id: str,
        fields: dict[str, str],
    ) -> None:
        job_id = fields.get("job_id")
        job_type = fields.get("job_type")
        payload_raw = fields.get("payload")

        if not job_id:
            logger.error(
                "Job missing job_id: %s",
                message_id,
            )
            redis_service.acknowledge(message_id)
            return

        if not job_type:
            logger.error(
                "Job missing job_type: %s",
                job_id,
            )
            redis_service.acknowledge(message_id)
            return

        if not payload_raw:
            logger.error(
                "Job missing payload: %s",
                job_id,
            )
            redis_service.acknowledge(message_id)
            return

        payload = redis_service.deserialize_payload(
            payload_raw
        )

        logger.info(
            "Processing job=%s type=%s",
            job_id,
            job_type,
        )

        try:
            await job_processor.process(
                job_type=job_type,
                payload=payload,
            )

            redis_service.acknowledge(message_id)

            logger.info(
                "Completed job=%s",
                job_id,
            )

        except Exception:
            logger.exception(
                "Job failed job=%s",
                job_id,
            )

            # Do not ACK failed jobs here.
            #
            # They remain pending in the Redis consumer
            # group and can later be reclaimed/retried.
            #
            # Retry/recovery policy will be completed
            # in the failure-recovery phase.


async def main() -> None:
    runner = WorkerRunner()

    signal.signal(
        signal.SIGINT,
        runner.stop,
    )

    signal.signal(
        signal.SIGTERM,
        runner.stop,
    )

    await runner.run()


if __name__ == "__main__":
    asyncio.run(main())