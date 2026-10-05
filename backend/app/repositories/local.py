"""Local development repositories: JSON files on disk guarded by a process lock.

Used when BACKEND_MODE=local so the whole product runs on a laptop with no AWS
account. The DynamoDB implementations in `dynamodb.py` have the same behaviour.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

from app.schemas.assets import WatchlistItem
from app.schemas.briefings import Briefing
from app.schemas.investigations import InvestigationEvent, InvestigationRecord
from app.schemas.uploads import UploadRecord
from app.schemas.users import UserRecord
from app.utils.time import utc_now_iso

_LOCK = threading.RLock()


class JsonTable:
    def __init__(self, path: Path | None) -> None:
        self._path = path
        self._data: dict[str, Any] = {}
        self._mtime = 0.0
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            self._reload()

    def _reload(self) -> None:
        """Pick up changes written by another process (e.g. scripts/seed_demo.py)."""
        if self._path is None or not self._path.exists():
            return
        mtime = self._path.stat().st_mtime
        if mtime == self._mtime:
            return
        try:
            self._data = json.loads(self._path.read_text(encoding="utf-8"))
            self._mtime = mtime
        except (OSError, json.JSONDecodeError):
            pass

    def _flush(self) -> None:
        if self._path is None:
            return
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._data, default=str), encoding="utf-8")
        tmp.replace(self._path)
        self._mtime = self._path.stat().st_mtime

    def get(self, key: str) -> Any | None:
        with _LOCK:
            self._reload()
            value = self._data.get(key)
            return json.loads(json.dumps(value)) if value is not None else None

    def put(self, key: str, value: Any) -> None:
        with _LOCK:
            self._reload()
            self._data[key] = json.loads(json.dumps(value, default=str))
            self._flush()

    def put_if_absent(self, key: str, value: Any) -> bool:
        with _LOCK:
            self._reload()
            if key in self._data:
                return False
            self._data[key] = value
            self._flush()
            return True

    def delete(self, key: str) -> bool:
        with _LOCK:
            self._reload()
            existed = self._data.pop(key, None) is not None
            if existed:
                self._flush()
            return existed

    def values(self) -> list[Any]:
        with _LOCK:
            self._reload()
            return json.loads(json.dumps(list(self._data.values())))

    def keys(self) -> list[str]:
        with _LOCK:
            self._reload()
            return list(self._data.keys())


def _table(base: Path | None, name: str) -> JsonTable:
    return JsonTable(base / f"{name}.json" if base else None)


class LocalUserRepository:
    def __init__(self, base: Path | None) -> None:
        self._t = _table(base, "users")

    def get(self, user_id: str) -> UserRecord | None:
        raw = self._t.get(user_id)
        return UserRecord.model_validate(raw) if raw else None

    def put(self, user: UserRecord) -> None:
        self._t.put(user.user_id, user.model_dump(mode="json"))

    def delete(self, user_id: str) -> None:
        self._t.delete(user_id)

    def list_briefing_enabled(self) -> list[UserRecord]:
        users = [UserRecord.model_validate(v) for v in self._t.values()]
        return [u for u in users if u.preferences.briefing.enabled]


class LocalCredentialRepository:
    def __init__(self, base: Path | None) -> None:
        self._t = _table(base, "local_credentials")

    def get(self, email: str) -> dict[str, Any] | None:
        result: dict[str, Any] | None = self._t.get(email.lower())
        return result

    def put(self, email: str, data: dict[str, Any]) -> None:
        self._t.put(email.lower(), data)


class LocalWatchlistRepository:
    def __init__(self, base: Path | None) -> None:
        self._t = _table(base, "watchlists")

    def list(self, user_id: str) -> list[WatchlistItem]:
        raw = self._t.get(user_id) or {}
        items = [WatchlistItem.model_validate(v) for v in raw.values()]
        return sorted(items, key=lambda i: (i.position, i.added_at))

    def put(self, item: WatchlistItem) -> None:
        with _LOCK:
            raw = self._t.get(item.user_id) or {}
            raw[item.symbol] = item.model_dump(mode="json")
            self._t.put(item.user_id, raw)

    def delete(self, user_id: str, symbol: str) -> bool:
        with _LOCK:
            raw = self._t.get(user_id) or {}
            existed = raw.pop(symbol, None) is not None
            self._t.put(user_id, raw)
            return existed

    def delete_all(self, user_id: str) -> None:
        self._t.delete(user_id)


class LocalInvestigationRepository:
    def __init__(self, base: Path | None) -> None:
        self._t = _table(base, "investigations")

    def get(self, investigation_id: str) -> InvestigationRecord | None:
        raw = self._t.get(investigation_id)
        return InvestigationRecord.model_validate(raw) if raw else None

    def put(self, record: InvestigationRecord) -> None:
        self._t.put(record.investigation_id, record.model_dump(mode="json"))

    def list_by_user(self, user_id: str, limit: int = 20) -> list[InvestigationRecord]:
        records = [
            InvestigationRecord.model_validate(v) for v in self._t.values() if v.get("user_id") == user_id
        ]
        records.sort(key=lambda r: r.created_at, reverse=True)
        return records[:limit]

    def delete(self, investigation_id: str) -> None:
        self._t.delete(investigation_id)


class LocalEventRepository:
    def __init__(self, base: Path | None) -> None:
        self._t = _table(base, "investigation_events")
        self._last_seq = 0

    def append(self, event: InvestigationEvent) -> InvestigationEvent:
        with _LOCK:
            seq = max(time.time_ns() // 1000, self._last_seq + 1)
            self._last_seq = seq
            stored = event.model_copy(update={"seq": seq, "timestamp": event.timestamp or utc_now_iso()})
            events = self._t.get(event.investigation_id) or []
            events.append(stored.model_dump(mode="json"))
            self._t.put(event.investigation_id, events)
            return stored

    def list_after(self, investigation_id: str, after_seq: int = 0) -> list[InvestigationEvent]:
        events = self._t.get(investigation_id) or []
        return [InvestigationEvent.model_validate(e) for e in events if e["seq"] > after_seq]

    def delete_for(self, investigation_id: str) -> None:
        self._t.delete(investigation_id)


class LocalBriefingRepository:
    def __init__(self, base: Path | None) -> None:
        self._t = _table(base, "briefings")

    def get(self, briefing_id: str) -> Briefing | None:
        raw = self._t.get(briefing_id)
        return Briefing.model_validate(raw) if raw else None

    def put(self, briefing: Briefing) -> None:
        self._t.put(briefing.briefing_id, briefing.model_dump(mode="json"))

    def list_by_user(self, user_id: str, limit: int = 20) -> list[Briefing]:
        items = [Briefing.model_validate(v) for v in self._t.values() if v.get("user_id") == user_id]
        items.sort(key=lambda b: b.created_at, reverse=True)
        return items[:limit]

    def delete(self, briefing_id: str) -> None:
        self._t.delete(briefing_id)


class LocalDeliveryRepository:
    def __init__(self, base: Path | None) -> None:
        self._t = _table(base, "briefing_deliveries")

    def claim(self, key: str, metadata: dict[str, Any]) -> bool:
        return self._t.put_if_absent(key, {**metadata, "claimed_at": utc_now_iso()})

    def get(self, key: str) -> dict[str, Any] | None:
        result: dict[str, Any] | None = self._t.get(key)
        return result

    def update(self, key: str, metadata: dict[str, Any]) -> None:
        with _LOCK:
            current = self._t.get(key) or {}
            current.update(metadata)
            self._t.put(key, current)

    def release(self, key: str) -> None:
        self._t.delete(key)


class LocalUploadRepository:
    def __init__(self, base: Path | None) -> None:
        self._t = _table(base, "uploads")

    def get(self, upload_id: str) -> UploadRecord | None:
        raw = self._t.get(upload_id)
        return UploadRecord.model_validate(raw) if raw else None

    def put(self, record: UploadRecord) -> None:
        self._t.put(record.upload_id, record.model_dump(mode="json"))

    def list_by_user(self, user_id: str) -> list[UploadRecord]:
        return [UploadRecord.model_validate(v) for v in self._t.values() if v.get("user_id") == user_id]

    def delete(self, upload_id: str) -> None:
        self._t.delete(upload_id)


class MemoryCacheRepository:
    """Process-local TTL cache (local mode). AWS mode uses the DynamoDB cache table."""

    def __init__(self) -> None:
        self._data: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        with _LOCK:
            hit = self._data.get(key)
            if not hit:
                return None
            expires, value = hit
            if expires < time.time():
                self._data.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        with _LOCK:
            self._data[key] = (time.time() + ttl_seconds, value)
