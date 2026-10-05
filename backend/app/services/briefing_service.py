from __future__ import annotations

from app.config.settings import Settings
from app.integrations.queue.base import QueueBackend
from app.integrations.storage.base import StorageBackend, key_belongs_to
from app.repositories.base import Repositories
from app.schemas.briefings import (
    Briefing,
    BriefingSummary,
    BriefingView,
    GenerateBriefingRequest,
    GenerateBriefingResponse,
)
from app.services.email_renderer import render_briefing_email
from app.services.errors import ConflictError, NotFoundError
from app.utils.ids import new_id
from app.utils.time import utc_now, utc_now_iso


class BriefingService:
    def __init__(
        self, repos: Repositories, queue: QueueBackend, storage: StorageBackend, settings: Settings
    ) -> None:
        self._repos = repos
        self._queue = queue
        self._storage = storage
        self._settings = settings

    def owned(self, user_id: str, briefing_id: str) -> Briefing:
        b = self._repos.briefings.get(briefing_id)
        if b is None or b.user_id != user_id:
            raise NotFoundError("Briefing not found.")
        return b

    def audio_url(self, b: Briefing) -> str | None:
        if b.audio_status != "ready" or not b.audio_key or not key_belongs_to(b.audio_key, b.user_id):
            return None
        return self._storage.presign_get(b.audio_key, 3600 * 24, f"signalroom-briefing-{b.date}.wav")

    def view(self, user_id: str, briefing_id: str) -> BriefingView:
        b = self.owned(user_id, briefing_id)
        return BriefingView(**b.model_dump(), audio_url=self.audio_url(b))

    def list_summaries(self, user_id: str, limit: int = 20) -> list[BriefingSummary]:
        return [
            BriefingSummary(
                briefing_id=b.briefing_id,
                date=b.date,
                briefing_type=b.briefing_type,
                status=b.status,
                headline=b.headline,
                audio_status=b.audio_status,
                created_at=b.created_at,
            )
            for b in self._repos.briefings.list_by_user(user_id, limit)
        ]

    def generate(self, user_id: str, req: GenerateBriefingRequest) -> GenerateBriefingResponse:
        recent = self._repos.briefings.list_by_user(user_id, 50)
        if any(b.status in ("queued", "running") for b in recent[:5]):
            raise ConflictError("A briefing is already being prepared.")
        today = utc_now().date().isoformat()
        limit = self._settings.max_briefings_per_day
        if (
            sum(1 for b in recent if b.briefing_type == "on_demand" and b.created_at.startswith(today))
            >= limit
        ):
            from app.services.investigation_service import RateLimited

            raise RateLimited(
                f"Daily limit of {limit} on-demand briefings reached for this demo. Try again tomorrow."
            )
        briefing = Briefing(
            briefing_id=new_id("brf"),
            user_id=user_id,
            date=utc_now().date().isoformat(),
            briefing_type="on_demand",
            audio_status="pending" if req.with_audio else "none",
            email_status="pending" if req.send_email else "not_requested",
            created_at=utc_now_iso(),
        )
        self._repos.briefings.put(briefing)
        self._queue.send(
            "briefings",
            {
                "job_type": "briefing",
                "job_id": briefing.briefing_id,
                "briefing_id": briefing.briefing_id,
                "user_id": user_id,
                "with_audio": req.with_audio,
                "send_email": req.send_email,
            },
        )
        return GenerateBriefingResponse(briefing_id=briefing.briefing_id, status="queued")

    def email_preview(self, user_id: str, briefing_id: str) -> str:
        b = self.owned(user_id, briefing_id)
        if b.status != "completed":
            raise ConflictError("The briefing is not ready yet.")
        _, html, _ = render_briefing_email(
            b, frontend_url=self._settings.frontend_url, audio_url=self.audio_url(b)
        )
        return html
