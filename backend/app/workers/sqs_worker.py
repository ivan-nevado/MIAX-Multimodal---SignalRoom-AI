"""Queue worker: `python -m app.workers.sqs_worker`.

1. polls SQS (investigation + briefing queues)  2. validates the payload
3. runs the LangGraph workflow                  4. progress is written to DynamoDB by the workflow
5. saves the output                             6. deletes (acks) the message ONLY after success

If the process crashes before the ack, SQS makes the message visible again after the
visibility timeout; after maxReceiveCount deliveries it moves to the dead-letter queue.
Handlers are idempotent so retries never duplicate audio or emails.
"""

from __future__ import annotations

import asyncio
import logging
import signal
import time
from types import FrameType

from app.config.logging import configure_logging
from app.container import Container, get_container
from app.integrations.queue.base import QueueName
from app.workers.job_handlers import InvalidJob, handle_job

logger = logging.getLogger(__name__)

QUEUES: tuple[QueueName, ...] = ("investigations", "briefings")
RETRY_DELAY_SECONDS = 30


class Worker:
    def __init__(
        self, container: Container, queues: tuple[QueueName, ...] = QUEUES, wait_seconds: int = 10
    ) -> None:
        self._c = container
        self._queues = queues
        self._wait = wait_seconds
        self._stopping = False

    def stop(self, *_: object) -> None:
        logger.info("worker_stopping")
        self._stopping = True

    async def process_one(self, queue: QueueName) -> bool:
        """Receive and process at most one message. Returns True if a message was handled."""
        messages = await asyncio.to_thread(self._c.queue.receive, queue, 1, self._wait)
        if not messages:
            return False
        msg = messages[0]
        started = time.perf_counter()
        try:
            await handle_job(self._c, msg.body)
        except InvalidJob as exc:
            logger.error("job_invalid_dropped", extra={"queue": queue, "error": str(exc)[:200]})
            await asyncio.to_thread(self._c.queue.ack, queue, msg.receipt)
            return True
        except Exception as exc:
            # Unexpected failure outside the workflow's own error handling: let SQS retry (→ DLQ).
            logger.exception(
                "job_failed_will_retry",
                extra={"queue": queue, "receive_count": msg.receive_count, "error_type": type(exc).__name__},
            )
            await asyncio.to_thread(self._c.queue.release, queue, msg.receipt, RETRY_DELAY_SECONDS)
            return True
        await asyncio.to_thread(self._c.queue.ack, queue, msg.receipt)
        logger.info(
            "job_acked", extra={"queue": queue, "elapsed_ms": int((time.perf_counter() - started) * 1000)}
        )
        return True

    async def run_forever(self) -> None:
        logger.info("worker_started", extra={"queues": list(self._queues), "backend": self._c.queue.name})
        while not self._stopping:
            for queue in self._queues:
                if self._stopping:
                    break
                try:
                    await self.process_one(queue)
                except Exception as exc:  # e.g. transient SQS errors
                    logger.exception("worker_poll_error", extra={"error_type": type(exc).__name__})
                    await asyncio.sleep(5)
        logger.info("worker_stopped")


def main() -> None:
    container = get_container()
    configure_logging(container.settings.log_level)
    worker = Worker(container)

    def _handle(signum: int, frame: FrameType | None) -> None:
        worker.stop()

    signal.signal(signal.SIGTERM, _handle)
    signal.signal(signal.SIGINT, _handle)
    asyncio.run(worker.run_forever())


if __name__ == "__main__":
    main()
