"""In-process worker thread for local development (BACKEND_MODE=local).

Runs the exact same Worker loop as ECS, against the in-memory LocalQueue, in a
dedicated thread with its own event loop. Never used in AWS (SQS + ECS worker there).
"""

from __future__ import annotations

import asyncio
import logging
import threading

from app.container import Container
from app.workers.sqs_worker import Worker

logger = logging.getLogger(__name__)


class LocalWorkerThread:
    def __init__(self, container: Container) -> None:
        self._worker = Worker(container, wait_seconds=1)
        self._thread = threading.Thread(target=self._run, name="signalroom-local-worker", daemon=True)

    def _run(self) -> None:
        asyncio.run(self._worker.run_forever())

    def start(self) -> None:
        logger.info("local_worker_starting")
        self._thread.start()

    def stop(self) -> None:
        self._worker.stop()
        self._thread.join(timeout=5)
