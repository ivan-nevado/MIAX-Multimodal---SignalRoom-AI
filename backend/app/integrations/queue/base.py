from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Protocol

QueueName = Literal["investigations", "briefings"]


@dataclass
class ReceivedMessage:
    body: dict[str, Any]
    receipt: str
    receive_count: int = 1


class QueueBackend(Protocol):
    name: str

    def send(self, queue: QueueName, body: dict[str, Any]) -> str: ...
    def receive(
        self, queue: QueueName, max_messages: int = 1, wait_seconds: int = 10
    ) -> list[ReceivedMessage]: ...
    def ack(self, queue: QueueName, receipt: str) -> None: ...
    def release(self, queue: QueueName, receipt: str, delay_seconds: int = 0) -> None: ...
