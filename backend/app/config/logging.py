"""Structured JSON logging with secret redaction and request/job context."""

from __future__ import annotations

import contextvars
import json
import logging
import re
import sys
from datetime import UTC, datetime
from typing import Any

request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)
job_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("job_id", default=None)
investigation_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "investigation_id", default=None
)
user_ref_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("user_ref", default=None)

_SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"AIza[0-9A-Za-z_\-]{20,}"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9\-_\.=]+"),
    re.compile(r"eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+"),  # JWTs
]
_SENSITIVE_KEYS = {"authorization", "api_key", "apikey", "token", "password", "secret", "jwt", "content"}
_STD_ATTRS = set(vars(logging.makeLogRecord({})).keys()) | {"message", "asctime"}


def redact(value: Any) -> Any:
    if isinstance(value, str):
        for pattern in _SECRET_PATTERNS:
            value = pattern.sub("[REDACTED]", value)
        return value
    if isinstance(value, dict):
        return {
            k: ("[REDACTED]" if str(k).lower() in _SENSITIVE_KEYS else redact(v)) for k, v in value.items()
        }
    if isinstance(value, list | tuple):
        return [redact(v) for v in value]
    return value


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": redact(record.getMessage()),
        }
        for key, var in (
            ("request_id", request_id_var),
            ("job_id", job_id_var),
            ("investigation_id", investigation_id_var),
            ("user_ref", user_ref_var),
        ):
            val = var.get()
            if val:
                payload[key] = val
        for key, val in record.__dict__.items():
            if key not in _STD_ATTRS and not key.startswith("_"):
                payload[key] = redact(val)
        if record.exc_info:
            payload["error_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None
            payload["exc"] = redact(self.formatException(record.exc_info))
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    if any(getattr(h, "_signalroom", False) for h in root.handlers):
        root.setLevel(level)
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler._signalroom = True  # type: ignore[attr-defined]
    root.handlers = [handler]
    root.setLevel(level)
    for noisy in ("httpx", "httpcore", "botocore", "urllib3", "yfinance", "peewee"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
