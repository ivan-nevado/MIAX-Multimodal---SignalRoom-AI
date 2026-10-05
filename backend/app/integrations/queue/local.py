"""In-process queue for local development (mirrors SQS semantics: receive → ack/release)."""

from __future__ import annotations

import queue
import threading
import uuid
from typing import Any

from app.integrations.queue.base import QueueName, ReceivedMessage


class LocalQueue:
    name = "local"

    def __init__(self) -> None:
        self._queues: dict[str, queue.Queue[tuple[dict[str, Any], int]]] = {
            "investigations": queue.Queue(),
            "briefings": queue.Queue(),
        }
        self._inflight: dict[str, tuple[str, dict[str, Any], int]] = {}
        self._lock = threading.Lock()

    def send(self, queue_name: QueueName, body: dict[str, Any]) -> str:
        message_id = str(uuid.uuid4())
        self._queues[queue_name].put(({**body, "_message_id": message_id}, 0))
        return message_id

    def receive(
        self, queue_name: QueueName, max_messages: int = 1, wait_seconds: int = 10
    ) -> list[ReceivedMessage]:
        out: list[ReceivedMessage] = []
        try:
            body, count = self._queues[queue_name].get(timeout=wait_seconds)
        except queue.Empty:
            return out
        receipt = str(uuid.uuid4())
        with self._lock:
            self._inflight[receipt] = (queue_name, body, count + 1)
        out.append(ReceivedMessage(body=body, receipt=receipt, receive_count=count + 1))
        return out

    def ack(self, queue_name: QueueName, receipt: str) -> None:
        with self._lock:
            self._inflight.pop(receipt, None)

    def release(self, queue_name: QueueName, receipt: str, delay_seconds: int = 0) -> None:
        with self._lock:
            item = self._inflight.pop(receipt, None)
        if item and item[2] < 3:  # emulate maxReceiveCount=3 then "DLQ" (dropped locally)
            self._queues[queue_name].put((item[1], item[2]))

    def pending(self, queue_name: QueueName) -> int:
        return self._queues[queue_name].qsize()
