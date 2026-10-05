from __future__ import annotations

from typing import Protocol


class EmailSender(Protocol):
    name: str

    def send(self, *, to: str, subject: str, html: str, text: str) -> str: ...
