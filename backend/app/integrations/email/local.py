"""Development email sender: writes the rendered email to data/runtime/outbox/."""

from __future__ import annotations

import re
import uuid
from pathlib import Path


class LocalOutboxSender:
    name = "local-outbox"

    def __init__(self, outbox: Path) -> None:
        self._outbox = outbox
        self._outbox.mkdir(parents=True, exist_ok=True)

    def send(self, *, to: str, subject: str, html: str, text: str) -> str:
        message_id = uuid.uuid4().hex[:12]
        safe = re.sub(r"[^a-zA-Z0-9]+", "-", subject)[:40].strip("-")
        (self._outbox / f"{message_id}-{safe}.html").write_text(html, encoding="utf-8")
        (self._outbox / f"{message_id}-{safe}.txt").write_text(
            f"To: {to}\nSubject: {subject}\n\n{text}", encoding="utf-8"
        )
        return message_id
