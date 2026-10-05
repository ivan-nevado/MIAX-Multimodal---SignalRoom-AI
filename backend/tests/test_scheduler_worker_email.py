from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.container import Container
from app.schemas.briefings import Briefing, BriefingSection, WatchlistMove
from app.schemas.common import Source
from app.schemas.users import UserRecord
from app.services.email_renderer import render_briefing_email
from app.utils.time import utc_now_iso
from app.workers.daily_briefing_scheduler import delivery_key, is_due, schedule_due_briefings
from app.workers.job_handlers import InvalidJob, parse_job
from app.workers.sqs_worker import Worker


def user(
    uid: str,
    *,
    enabled: bool = True,
    local_time: str = "08:00",
    tz: str = "Europe/Madrid",
    email: bool = False,
) -> UserRecord:
    u = UserRecord(user_id=uid, email=f"{uid}@example.com", created_at=utc_now_iso())
    u.preferences.briefing.enabled = enabled
    u.preferences.briefing.local_time = local_time
    u.preferences.briefing.timezone = tz
    u.preferences.briefing.email_enabled = email
    return u


def test_is_due_respects_timezone_and_window() -> None:
    madrid_0815 = datetime(2026, 10, 5, 6, 15, tzinfo=UTC)  # 08:15 CEST
    assert is_due(user("a"), madrid_0815) == (True, "2026-10-05")
    assert is_due(user("a"), datetime(2026, 10, 5, 5, 45, tzinfo=UTC))[0] is False  # 07:45 local: too early
    assert (
        is_due(user("a"), datetime(2026, 10, 5, 8, 30, tzinfo=UTC))[0] is False
    )  # 10:30 local: outside window
    ny = user("b", tz="America/New_York", local_time="07:00")
    assert is_due(ny, datetime(2026, 10, 5, 11, 5, tzinfo=UTC)) == (True, "2026-10-05")
    tokyo = user("c", tz="Asia/Tokyo", local_time="08:00")
    assert is_due(tokyo, datetime(2026, 10, 4, 23, 30, tzinfo=UTC)) == (
        True,
        "2026-10-05",
    )  # local date differs from UTC date
    assert is_due(user("d", enabled=False), madrid_0815)[0] is False


def test_scheduler_is_idempotent_and_respects_email_opt_in(container: Container) -> None:
    now = datetime(2026, 10, 5, 6, 15, tzinfo=UTC)
    container.repos.users.put(user("due", email=True))
    container.repos.users.put(user("noemail"))
    container.repos.users.put(user("later", local_time="18:00"))
    container.repos.users.put(user("off", enabled=False))
    first = schedule_due_briefings(container, now)
    assert len(first) == 2
    assert schedule_due_briefings(container, now) == []  # second (overlapping) run sends nothing
    assert container.repos.deliveries.get(delivery_key("due", "2026-10-05")) is not None
    jobs = []
    while msgs := container.queue.receive("briefings", 1, 0):
        jobs.append(msgs[0].body)
    by_user = {j["user_id"]: j for j in jobs}
    assert by_user["due"]["send_email"] is True and by_user["noemail"]["send_email"] is False
    assert by_user["due"]["delivery_key"] == "due#2026-10-05#daily"


async def test_scheduled_briefing_end_to_end_sends_one_email(container: Container) -> None:
    now = datetime.now(UTC)
    local = now.astimezone().strftime("%H:%M")
    u = user("u_mail", email=True, tz="UTC", local_time=now.strftime("%H:%M"))
    container.repos.users.put(u)
    schedule_due_briefings(container, now)
    worker = Worker(container, wait_seconds=0)
    assert await worker.process_one("briefings")
    briefing = container.repos.briefings.list_by_user("u_mail")[0]
    assert briefing.status == "completed" and briefing.email_status == "sent"
    # Simulated redelivery of the same job must not send a second email.
    container.queue.send(
        "briefings",
        {
            "job_type": "briefing",
            "job_id": "x",
            "briefing_id": briefing.briefing_id,
            "user_id": "u_mail",
            "send_email": True,
            "delivery_key": "u_mail#" + briefing.date + "#daily",
        },
    )
    assert await worker.process_one("briefings")
    assert len(list((container.settings.local_data_dir / "outbox").glob("*.html"))) == 1
    assert local  # silence unused


def test_parse_job_validation() -> None:
    assert (
        parse_job(
            {"job_type": "investigation", "job_id": "j", "user_id": "u", "investigation_id": "i"}
        ).investigation_id
        == "i"
    )
    for bad in (
        {"job_type": "nope", "job_id": "j", "user_id": "u"},
        {"job_type": "investigation", "job_id": "j", "user_id": "u"},
        {"job_type": "followup", "job_id": "j", "user_id": "u", "investigation_id": "i"},
    ):
        with pytest.raises(InvalidJob):
            parse_job(bad)


async def test_worker_acks_invalid_and_releases_on_crash(
    container: Container, monkeypatch: pytest.MonkeyPatch
) -> None:
    worker = Worker(container, wait_seconds=0)
    container.queue.send("investigations", {"garbage": True})
    assert await worker.process_one("investigations")
    assert container.queue.pending("investigations") == 0  # type: ignore[attr-defined]

    async def boom(*_: object) -> None:
        raise RuntimeError("worker crashed mid-job")

    monkeypatch.setattr("app.workers.sqs_worker.handle_job", boom)
    container.queue.send(
        "investigations",
        {"job_type": "investigation", "job_id": "j", "user_id": "u", "investigation_id": "i"},
    )
    assert await worker.process_one("investigations")
    assert (
        container.queue.pending("investigations") == 1
    )  # released for retry (SQS → DLQ after maxReceiveCount)
    assert await worker.process_one("investigations") is True
    assert await worker.process_one("investigations") is True
    assert container.queue.pending("investigations") == 0  # dropped after 3 receives (DLQ emulation)


def test_email_renderer_escapes_and_links() -> None:
    b = Briefing(
        briefing_id="b1",
        user_id="u1",
        date="2026-10-05",
        status="completed",
        headline="NVIDIA <script>alert(1)</script> leads",
        summary="Summary.",
        sections=[
            BriefingSection(
                title="NVIDIA",
                symbol="NVDA",
                body="Shares fell.",
                why_it_matters="Biggest mover.",
                source_ids=["s1"],
            )
        ],
        watchlist_moves=[WatchlistMove(symbol="NVDA", name="NVIDIA", move_pct=-6.2)],
        risk_flags=["Export rules"],
        sources=[
            Source(
                id="s1",
                title="Export rules",
                publisher="Reuters",
                url="https://reuters.com/a",
                retrieved_at=utc_now_iso(),
                source_type="news",
            )
        ],
        created_at=utc_now_iso(),
    )
    subject, html, text = render_briefing_email(
        b, frontend_url="https://d123.cloudfront.net", audio_url="https://audio"
    )
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "https://d123.cloudfront.net/app/briefing/b1" in html and "https://reuters.com/a" in html
    assert "Listen to briefing" in html and "unsubscribe" in html.lower()
    assert "▼ -6.20%" in html and "Export rules" in text and subject.startswith("SignalRoom")
