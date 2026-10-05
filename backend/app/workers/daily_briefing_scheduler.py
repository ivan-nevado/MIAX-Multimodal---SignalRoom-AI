"""One-shot scheduler: `python -m app.workers.daily_briefing_scheduler`.

Invoked by Amazon EventBridge Scheduler every 15 minutes as an ECS RunTask
(no cron loop inside any container). It:

1. determines the current UTC time
2. finds users whose local briefing time has arrived (within a 2-hour catch-up window)
3. claims an idempotency key  user_id#local_date#daily  (conditional write)
4. creates the briefing record and sends a job to the briefing SQS queue
5. exits

The idempotency key guarantees a user never receives the same daily briefing twice,
even if two scheduler runs overlap or a run is retried.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.config.logging import configure_logging
from app.container import Container, get_container
from app.schemas.briefings import Briefing
from app.schemas.users import UserRecord
from app.utils.ids import new_id
from app.utils.time import utc_now, utc_now_iso

logger = logging.getLogger(__name__)

CATCH_UP_WINDOW = timedelta(hours=2)


def is_due(user: UserRecord, now_utc: datetime) -> tuple[bool, str]:
    prefs = user.preferences.briefing
    if not prefs.enabled:
        return False, ""
    local_now = now_utc.astimezone(ZoneInfo(prefs.timezone))
    hour, minute = (int(x) for x in prefs.local_time.split(":"))
    scheduled = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    due = scheduled <= local_now < scheduled + CATCH_UP_WINDOW
    return due, local_now.date().isoformat()


def delivery_key(user_id: str, local_date: str, briefing_type: str = "daily") -> str:
    return f"{user_id}#{local_date}#{briefing_type}"


def schedule_due_briefings(c: Container, now_utc: datetime | None = None) -> list[str]:
    now_utc = now_utc or utc_now()
    created: list[str] = []
    for user in c.repos.users.list_briefing_enabled():
        due, local_date = is_due(user, now_utc)
        if not due:
            continue
        key = delivery_key(user.user_id, local_date)
        briefing_id = new_id("brf")
        if not c.repos.deliveries.claim(key, {"briefing_id": briefing_id, "user_id": user.user_id}):
            continue  # already scheduled/sent today
        prefs = user.preferences.briefing
        c.repos.briefings.put(
            Briefing(
                briefing_id=briefing_id,
                user_id=user.user_id,
                date=local_date,
                briefing_type="daily",
                audio_status="pending" if prefs.audio_enabled else "none",
                email_status="pending" if prefs.email_enabled else "not_requested",
                created_at=utc_now_iso(),
            )
        )
        c.queue.send(
            "briefings",
            {
                "job_type": "briefing",
                "job_id": key,
                "briefing_id": briefing_id,
                "user_id": user.user_id,
                "with_audio": prefs.audio_enabled,
                "send_email": prefs.email_enabled,  # never email unless the user enabled it
                "delivery_key": key,
            },
        )
        user.last_briefing_date = local_date
        c.repos.users.put(user)
        created.append(briefing_id)
    logger.info("daily_briefings_scheduled", extra={"count": len(created)})
    return created


def main() -> None:
    container = get_container()
    configure_logging(container.settings.log_level)
    schedule_due_briefings(container)


if __name__ == "__main__":
    main()
