"""AWS adapters against moto: DynamoDB repositories, S3, SQS, Secrets Manager and SES.

These run fully offline (no AWS account needed) and validate the exact code paths
used in the deployed ECS tasks.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Iterator
from urllib.parse import parse_qs, urlparse

import boto3
import pytest
from moto import mock_aws

from app.config import secrets as secrets_mod
from app.integrations.email.ses import SESEmailSender
from app.integrations.queue.sqs import SQSQueue
from app.integrations.storage.s3 import S3Storage
from app.repositories import dynamodb as d
from app.repositories.dynamodb_schema import create_tables
from app.schemas.assets import WatchlistItem
from app.schemas.briefings import Briefing
from app.schemas.investigations import InvestigationEvent, InvestigationRecord
from app.schemas.uploads import UploadRecord
from app.schemas.users import UserRecord
from app.utils.time import utc_now_iso

REGION = "eu-west-1"
PREFIX = "signalroom-test"


@pytest.fixture
def aws() -> Iterator[None]:
    with mock_aws():
        yield


@pytest.fixture
def tables(aws: None) -> d.DynamoTables:
    create_tables(boto3.client("dynamodb", region_name=REGION), PREFIX)
    return d.DynamoTables(PREFIX, REGION)


def test_dynamo_users_and_briefing_enabled_scan(tables: d.DynamoTables) -> None:
    repo = d.DynamoUserRepository(tables)
    u1 = UserRecord(user_id="u1", email="a@x.com", created_at=utc_now_iso())
    u2 = UserRecord(user_id="u2", email="b@x.com", created_at=utc_now_iso())
    u2.preferences.briefing.enabled = True
    repo.put(u1)
    repo.put(u2)
    assert repo.get("u1") == u1
    assert [u.user_id for u in repo.list_briefing_enabled()] == ["u2"]
    repo.delete("u1")
    assert repo.get("u1") is None
    creds = d.DynamoCredentialRepository(tables)
    creds.put("A@x.com", {"user_id": "u9", "password": "h"})
    assert creds.get("a@x.com") == {"user_id": "u9", "password": "h"}
    assert [u.user_id for u in repo.list_briefing_enabled()] == [
        "u2"
    ]  # credential rows never leak into scans


def test_dynamo_watchlist(tables: d.DynamoTables) -> None:
    repo = d.DynamoWatchlistRepository(tables)
    for pos, sym in enumerate(["TSLA", "NVDA"]):
        repo.put(
            WatchlistItem(user_id="u1", symbol=sym, display_name=sym, position=pos, added_at=utc_now_iso())
        )
    repo.put(WatchlistItem(user_id="u2", symbol="AAPL", display_name="Apple", added_at=utc_now_iso()))
    assert [i.symbol for i in repo.list("u1")] == ["TSLA", "NVDA"]
    assert repo.delete("u1", "TSLA") and not repo.delete("u1", "TSLA")
    repo.delete_all("u1")
    assert repo.list("u1") == [] and len(repo.list("u2")) == 1


def test_dynamo_investigations_events_and_compression(tables: d.DynamoTables) -> None:
    repo = d.DynamoInvestigationRepository(tables)
    for i in range(3):
        repo.put(
            InvestigationRecord(
                investigation_id=f"inv{i}",
                user_id="u1",
                question="q" * 2000,
                created_at=f"2026-10-0{i + 1}T00:00:00",
                updated_at=utc_now_iso(),
            )
        )
    repo.put(
        InvestigationRecord(
            investigation_id="other",
            user_id="u2",
            question="q",
            created_at=utc_now_iso(),
            updated_at=utc_now_iso(),
        )
    )
    listed = repo.list_by_user("u1", limit=2)
    assert [r.investigation_id for r in listed] == ["inv2", "inv1"]  # newest first via GSI
    raw = boto3.client("dynamodb", region_name=REGION).get_item(
        TableName=f"{PREFIX}-investigations", Key={"investigation_id": {"S": "inv0"}}
    )
    assert len(raw["Item"]["doc"]["B"]) < 500  # zlib-compressed document

    events = d.DynamoEventRepository(tables)
    stored = [
        events.append(
            InvestigationEvent(investigation_id="inv0", seq=0, timestamp="", event_type=t, message=t)
        )
        for t in ("queued", "running", "completed")
    ]
    assert stored[0].seq < stored[1].seq < stored[2].seq
    assert [e.event_type for e in events.list_after("inv0", stored[0].seq)] == ["running", "completed"]
    item = boto3.client("dynamodb", region_name=REGION).scan(TableName=f"{PREFIX}-investigation-events")[
        "Items"
    ][0]
    assert int(item["expires_at"]["N"]) > time.time()  # TTL set
    events.delete_for("inv0")
    assert events.list_after("inv0") == []


def test_dynamo_briefings_uploads_cache(tables: d.DynamoTables) -> None:
    briefings = d.DynamoBriefingRepository(tables)
    briefings.put(Briefing(briefing_id="b1", user_id="u1", date="2026-10-05", created_at=utc_now_iso()))
    assert briefings.get("b1") is not None and briefings.list_by_user("u1")[0].briefing_id == "b1"
    uploads = d.DynamoUploadRepository(tables)
    uploads.put(
        UploadRecord(
            upload_id="up1",
            user_id="u1",
            kind="document",
            filename="a.pdf",
            content_type="application/pdf",
            size_bytes=1,
            storage_key="users/u1/x",
            created_at=utc_now_iso(),
        )
    )
    assert uploads.list_by_user("u1")[0].upload_id == "up1"
    cache = d.DynamoCacheRepository(tables)
    cache.set("k", {"v": [1, 2]}, 60)
    assert cache.get("k") == {"v": [1, 2]}
    cache.set("expired", 1, -5)
    assert cache.get("expired") is None


def test_dynamo_delivery_idempotency(tables: d.DynamoTables) -> None:
    repo = d.DynamoDeliveryRepository(tables)
    key = "u1#2026-10-05#daily"
    assert repo.claim(key, {"briefing_id": "b1"}) is True
    assert repo.claim(key, {"briefing_id": "b2"}) is False  # conditional write blocks duplicates
    repo.update(key, {"email_sent": True})
    assert repo.get(key) == {
        "briefing_id": "b1",
        "claimed_at": repo.get(key)["claimed_at"],
        "email_sent": True,
    }  # type: ignore[index]
    repo.release(key)
    assert repo.claim(key, {}) is True


def test_s3_storage_presign_and_prefix_delete(aws: None) -> None:
    boto3.client("s3", region_name=REGION).create_bucket(
        Bucket="sr-test", CreateBucketConfiguration={"LocationConstraint": REGION}
    )
    storage = S3Storage("sr-test", REGION)
    storage.put_bytes("users/u1/a.txt", b"hello", "text/plain")
    storage.put_bytes("users/u1/b.txt", b"%PDF-xyz", "application/pdf")
    assert storage.get_bytes("users/u1/a.txt") == b"hello" and storage.size("users/u1/a.txt") == 5
    assert storage.read_head("users/u1/b.txt", 4) == b"%PDF"
    assert storage.size("users/u1/missing") is None
    url, headers = storage.presign_put("users/u1/up.pdf", "application/pdf", 10)
    # No network in tests: check the URL is SigV4-signed for this key and binds the Content-Type.
    query = parse_qs(urlparse(url).query)
    assert urlparse(url).path.endswith("/users/u1/up.pdf") and "sr-test" in url
    assert query["X-Amz-Algorithm"] == ["AWS4-HMAC-SHA256"] and query["X-Amz-Expires"] == ["900"]
    assert "content-type" in query["X-Amz-SignedHeaders"][0] and headers == {
        "Content-Type": "application/pdf"
    }
    assert "response-content-disposition" in storage.presign_get("users/u1/a.txt", filename="a.txt")
    assert storage.delete_prefix("users/u1/") == 2


def test_sqs_queue_ack_and_release(aws: None) -> None:
    sqs = boto3.client("sqs", region_name=REGION)
    urls = {
        name: sqs.create_queue(QueueName=f"sr-{name}")["QueueUrl"] for name in ("investigations", "briefings")
    }
    queue = SQSQueue(urls, REGION)
    queue.send("investigations", {"job_type": "investigation", "job_id": "j1"})
    msg = queue.receive("investigations", wait_seconds=0)[0]
    assert msg.body["job_id"] == "j1" and msg.receive_count == 1
    queue.release("investigations", msg.receipt, 0)  # retry → visible again
    again = queue.receive("investigations", wait_seconds=0)[0]
    assert again.receive_count == 2
    queue.ack("investigations", again.receipt)
    assert queue.receive("investigations", wait_seconds=0) == []


def test_secrets_manager_loader(aws: None, monkeypatch: pytest.MonkeyPatch) -> None:
    sm = boto3.client("secretsmanager", region_name=REGION)
    sm.create_secret(
        Name="signalroom/test/app",
        SecretString=json.dumps(
            {
                "OPENROUTER_API_KEY": "sk-or-test",
                "FRED_API_KEY": "",
                "UNRELATED": "x",
                "SEC_USER_AGENT": "env-wins",
            }
        ),
    )
    monkeypatch.setenv("SECRETS_MANAGER_SECRET_ID", "signalroom/test/app")
    monkeypatch.setenv("AWS_REGION", REGION)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("SEC_USER_AGENT", "already-set")
    loaded = secrets_mod.load_secrets_into_environment()
    assert loaded == ["OPENROUTER_API_KEY"]  # empty values, unknown keys and existing env vars are skipped
    assert os.environ["OPENROUTER_API_KEY"] == "sk-or-test" and os.environ["SEC_USER_AGENT"] == "already-set"
    monkeypatch.setenv("OPENROUTER_API_KEY", "")


def test_ses_sender(aws: None) -> None:
    boto3.client("ses", region_name=REGION).verify_email_identity(EmailAddress="briefings@example.com")
    sender = SESEmailSender("briefings@example.com", REGION)
    message_id = sender.send(to="user@example.com", subject="Hi", html="<b>Hi</b>", text="Hi")
    assert message_id
