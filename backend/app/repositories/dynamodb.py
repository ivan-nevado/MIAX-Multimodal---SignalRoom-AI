"""DynamoDB repositories (BACKEND_MODE=aws).

Item layout: key/index attributes are stored as top-level attributes; the full
record is stored as zlib-compressed JSON in `doc` (keeps items far below the
400 KB limit and avoids float/Decimal conversions). Table names and keys must
match `terraform/modules/dynamodb`.
"""

from __future__ import annotations

import contextlib
import json
import time
import zlib
from typing import Any

import boto3
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError

from app.schemas.assets import WatchlistItem
from app.schemas.briefings import Briefing
from app.schemas.investigations import InvestigationEvent, InvestigationRecord
from app.schemas.uploads import UploadRecord
from app.schemas.users import UserRecord
from app.utils.time import utc_now_iso

USER_INDEX = "user_id-created_at-index"
EVENT_TTL_SECONDS = 7 * 24 * 3600
DELIVERY_TTL_SECONDS = 45 * 24 * 3600

TABLE_SUFFIXES = {
    "users": "users",
    "watchlists": "watchlists",
    "investigations": "investigations",
    "events": "investigation-events",
    "briefings": "briefings",
    "deliveries": "briefing-deliveries",
    "uploads": "uploads",
    "cache": "cache",
}


def table_name(prefix: str, logical: str) -> str:
    return f"{prefix}-{TABLE_SUFFIXES[logical]}"


def encode_doc(data: Any) -> bytes:
    return zlib.compress(json.dumps(data, default=str, separators=(",", ":")).encode("utf-8"))


def decode_doc(raw: Any) -> Any:
    blob = raw.value if hasattr(raw, "value") else raw
    return json.loads(zlib.decompress(bytes(blob)).decode("utf-8"))


class DynamoTables:
    def __init__(self, prefix: str, region: str, endpoint_url: str | None = None) -> None:
        self._resource = boto3.resource("dynamodb", region_name=region, endpoint_url=endpoint_url)
        self.prefix = prefix

    def table(self, logical: str) -> Any:
        return self._resource.Table(table_name(self.prefix, logical))


def _query_all(table: Any, **kwargs: Any) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    while True:
        resp = table.query(**kwargs)
        items.extend(resp.get("Items", []))
        if "LastEvaluatedKey" not in resp or ("Limit" in kwargs and len(items) >= kwargs["Limit"]):
            return items
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]


class DynamoUserRepository:
    def __init__(self, tables: DynamoTables) -> None:
        self._t = tables.table("users")

    def get(self, user_id: str) -> UserRecord | None:
        item = self._t.get_item(Key={"user_id": user_id}).get("Item")
        return UserRecord.model_validate(decode_doc(item["doc"])) if item else None

    def put(self, user: UserRecord) -> None:
        self._t.put_item(
            Item={
                "user_id": user.user_id,
                "briefing_enabled": user.preferences.briefing.enabled,
                "doc": encode_doc(user.model_dump(mode="json")),
            }
        )

    def delete(self, user_id: str) -> None:
        self._t.delete_item(Key={"user_id": user_id})

    def list_briefing_enabled(self) -> list[UserRecord]:
        users: list[UserRecord] = []
        kwargs: dict[str, Any] = {"FilterExpression": Attr("briefing_enabled").eq(True)}
        while True:
            resp = self._t.scan(**kwargs)
            users.extend(UserRecord.model_validate(decode_doc(i["doc"])) for i in resp.get("Items", []))
            if "LastEvaluatedKey" not in resp:
                return users
            kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]


class DynamoCredentialRepository:
    """Only used with AUTH_MODE=local against LocalStack; Cognito owns credentials in AWS."""

    def __init__(self, tables: DynamoTables) -> None:
        self._t = tables.table("users")

    def get(self, email: str) -> dict[str, Any] | None:
        item = self._t.get_item(Key={"user_id": f"credential#{email.lower()}"}).get("Item")
        if not item:
            return None
        result: dict[str, Any] = decode_doc(item["doc"])
        return result

    def put(self, email: str, data: dict[str, Any]) -> None:
        self._t.put_item(
            Item={
                "user_id": f"credential#{email.lower()}",
                "briefing_enabled": False,
                "doc": encode_doc(data),
            }
        )


class DynamoWatchlistRepository:
    def __init__(self, tables: DynamoTables) -> None:
        self._t = tables.table("watchlists")

    def list(self, user_id: str) -> list[WatchlistItem]:
        items = _query_all(self._t, KeyConditionExpression=Key("user_id").eq(user_id))
        parsed = [WatchlistItem.model_validate(decode_doc(i["doc"])) for i in items]
        return sorted(parsed, key=lambda i: (i.position, i.added_at))

    def put(self, item: WatchlistItem) -> None:
        self._t.put_item(
            Item={
                "user_id": item.user_id,
                "symbol": item.symbol,
                "doc": encode_doc(item.model_dump(mode="json")),
            }
        )

    def delete(self, user_id: str, symbol: str) -> bool:
        resp = self._t.delete_item(Key={"user_id": user_id, "symbol": symbol}, ReturnValues="ALL_OLD")
        return "Attributes" in resp

    def delete_all(self, user_id: str) -> None:
        for item in self.list(user_id):
            self.delete(user_id, item.symbol)


class DynamoInvestigationRepository:
    def __init__(self, tables: DynamoTables) -> None:
        self._t = tables.table("investigations")

    def get(self, investigation_id: str) -> InvestigationRecord | None:
        item = self._t.get_item(Key={"investigation_id": investigation_id}).get("Item")
        return InvestigationRecord.model_validate(decode_doc(item["doc"])) if item else None

    def put(self, record: InvestigationRecord) -> None:
        self._t.put_item(
            Item={
                "investigation_id": record.investigation_id,
                "user_id": record.user_id,
                "created_at": record.created_at,
                "status": record.status,
                "doc": encode_doc(record.model_dump(mode="json")),
            }
        )

    def list_by_user(self, user_id: str, limit: int = 20) -> list[InvestigationRecord]:
        items = _query_all(
            self._t,
            IndexName=USER_INDEX,
            KeyConditionExpression=Key("user_id").eq(user_id),
            ScanIndexForward=False,
            Limit=limit,
        )
        return [InvestigationRecord.model_validate(decode_doc(i["doc"])) for i in items[:limit]]

    def delete(self, investigation_id: str) -> None:
        self._t.delete_item(Key={"investigation_id": investigation_id})


class DynamoEventRepository:
    def __init__(self, tables: DynamoTables) -> None:
        self._t = tables.table("events")
        self._last_seq = 0

    def append(self, event: InvestigationEvent) -> InvestigationEvent:
        seq = max(time.time_ns() // 1000, self._last_seq + 1)
        self._last_seq = seq
        stored = event.model_copy(update={"seq": seq, "timestamp": event.timestamp or utc_now_iso()})
        self._t.put_item(
            Item={
                "investigation_id": stored.investigation_id,
                "seq": seq,
                "expires_at": int(time.time()) + EVENT_TTL_SECONDS,
                "doc": encode_doc(stored.model_dump(mode="json")),
            }
        )
        return stored

    def list_after(self, investigation_id: str, after_seq: int = 0) -> list[InvestigationEvent]:
        items = _query_all(
            self._t,
            KeyConditionExpression=Key("investigation_id").eq(investigation_id) & Key("seq").gt(after_seq),
            ScanIndexForward=True,
        )
        return [InvestigationEvent.model_validate(decode_doc(i["doc"])) for i in items]

    def delete_for(self, investigation_id: str) -> None:
        items = _query_all(self._t, KeyConditionExpression=Key("investigation_id").eq(investigation_id))
        with self._t.batch_writer() as batch:
            for item in items:
                batch.delete_item(Key={"investigation_id": investigation_id, "seq": item["seq"]})


class DynamoBriefingRepository:
    def __init__(self, tables: DynamoTables) -> None:
        self._t = tables.table("briefings")

    def get(self, briefing_id: str) -> Briefing | None:
        item = self._t.get_item(Key={"briefing_id": briefing_id}).get("Item")
        return Briefing.model_validate(decode_doc(item["doc"])) if item else None

    def put(self, briefing: Briefing) -> None:
        self._t.put_item(
            Item={
                "briefing_id": briefing.briefing_id,
                "user_id": briefing.user_id,
                "created_at": briefing.created_at,
                "doc": encode_doc(briefing.model_dump(mode="json")),
            }
        )

    def list_by_user(self, user_id: str, limit: int = 20) -> list[Briefing]:
        items = _query_all(
            self._t,
            IndexName=USER_INDEX,
            KeyConditionExpression=Key("user_id").eq(user_id),
            ScanIndexForward=False,
            Limit=limit,
        )
        return [Briefing.model_validate(decode_doc(i["doc"])) for i in items[:limit]]

    def delete(self, briefing_id: str) -> None:
        self._t.delete_item(Key={"briefing_id": briefing_id})


class DynamoDeliveryRepository:
    """Idempotency markers: `user_id#date#briefing_type` written with a conditional put."""

    def __init__(self, tables: DynamoTables) -> None:
        self._t = tables.table("deliveries")

    def claim(self, key: str, metadata: dict[str, Any]) -> bool:
        try:
            self._t.put_item(
                Item={
                    "delivery_key": key,
                    "expires_at": int(time.time()) + DELIVERY_TTL_SECONDS,
                    "doc": encode_doc({**metadata, "claimed_at": utc_now_iso()}),
                },
                ConditionExpression="attribute_not_exists(delivery_key)",
            )
            return True
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return False
            raise

    def get(self, key: str) -> dict[str, Any] | None:
        item = self._t.get_item(Key={"delivery_key": key}).get("Item")
        if not item:
            return None
        result: dict[str, Any] = decode_doc(item["doc"])
        return result

    def update(self, key: str, metadata: dict[str, Any]) -> None:
        current = self.get(key) or {}
        current.update(metadata)
        self._t.put_item(
            Item={
                "delivery_key": key,
                "expires_at": int(time.time()) + DELIVERY_TTL_SECONDS,
                "doc": encode_doc(current),
            }
        )

    def release(self, key: str) -> None:
        self._t.delete_item(Key={"delivery_key": key})


class DynamoUploadRepository:
    def __init__(self, tables: DynamoTables) -> None:
        self._t = tables.table("uploads")

    def get(self, upload_id: str) -> UploadRecord | None:
        item = self._t.get_item(Key={"upload_id": upload_id}).get("Item")
        return UploadRecord.model_validate(decode_doc(item["doc"])) if item else None

    def put(self, record: UploadRecord) -> None:
        self._t.put_item(
            Item={
                "upload_id": record.upload_id,
                "user_id": record.user_id,
                "created_at": record.created_at,
                "doc": encode_doc(record.model_dump(mode="json")),
            }
        )

    def list_by_user(self, user_id: str) -> list[UploadRecord]:
        items = _query_all(self._t, IndexName=USER_INDEX, KeyConditionExpression=Key("user_id").eq(user_id))
        return [UploadRecord.model_validate(decode_doc(i["doc"])) for i in items]

    def delete(self, upload_id: str) -> None:
        self._t.delete_item(Key={"upload_id": upload_id})


class DynamoCacheRepository:
    def __init__(self, tables: DynamoTables) -> None:
        self._t = tables.table("cache")

    def get(self, key: str) -> Any | None:
        try:
            item = self._t.get_item(Key={"cache_key": key}).get("Item")
        except ClientError:
            return None
        if not item or int(item.get("expires_at", 0)) < time.time():
            return None
        return decode_doc(item["doc"])

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        doc = encode_doc(value)
        if len(doc) > 350_000:  # stay below the DynamoDB item limit
            return
        with contextlib.suppress(ClientError):
            self._t.put_item(
                Item={"cache_key": key, "expires_at": int(time.time()) + ttl_seconds, "doc": doc}
            )
