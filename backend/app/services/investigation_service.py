"""Investigation use cases. Long-running work is always queued; this service never runs agents."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.integrations.queue.base import QueueBackend
from app.integrations.storage.base import StorageBackend, key_belongs_to, user_prefix
from app.models.status import InvestigationStatus
from app.repositories.base import Repositories
from app.schemas.agents import AudioFindings, Transcript, VideoFindings
from app.schemas.investigations import (
    CreateInvestigationRequest,
    CreateInvestigationResponse,
    FollowUp,
    FollowUpRequest,
    FollowUpResponse,
    InvestigationEvent,
    InvestigationRecord,
    InvestigationSummary,
    InvestigationView,
    MediaJobResponse,
)
from app.services.entity_resolution import EntityResolver, find_alias_in_text
from app.services.errors import ConflictError, NotFoundError, ServiceError, ValidationFailed
from app.services.upload_service import UploadService
from app.utils.ids import new_id
from app.utils.time import utc_now, utc_now_iso

logger = logging.getLogger(__name__)


class RateLimited(ServiceError):
    status_code = 429
    code = "rate_limited"


class InvestigationService:
    def __init__(
        self,
        repos: Repositories,
        queue: QueueBackend,
        storage: StorageBackend,
        uploads: UploadService,
        resolver: EntityResolver,
        max_per_day: int = 20,
    ) -> None:
        self._max_per_day = max_per_day
        self._repos = repos
        self._queue = queue
        self._storage = storage
        self._uploads = uploads
        self._resolver = resolver

    # ------------------------------------------------------------------ create
    async def create(self, user_id: str, req: CreateInvestigationRequest) -> CreateInvestigationResponse:
        today = utc_now().date().isoformat()
        recent = self._repos.investigations.list_by_user(user_id, self._max_per_day + 1)
        if sum(1 for r in recent if r.created_at.startswith(today)) >= self._max_per_day:
            raise RateLimited(
                f"Daily limit of {self._max_per_day} investigations reached for this demo. Try again tomorrow."
            )

        attachments = self._uploads.attachments(user_id, req.upload_ids)
        match = None
        if req.asset:
            match = await self._resolver.resolve(req.asset)
            if match is None:
                raise ValidationFailed(f"Could not resolve '{req.asset}' to a known asset.")
        else:
            match = find_alias_in_text(req.question)
        if match is None and not attachments:
            raise ValidationFailed("Choose an asset or attach a document, image, audio or video file.")

        now = utc_now_iso()
        record = InvestigationRecord(
            investigation_id=new_id("inv"),
            user_id=user_id,
            symbol=match.symbol if match else None,
            asset_name=match.name if match else None,
            asset_type=match.asset_type if match else None,
            question=req.question,
            attachments=attachments,
            generate_audio=req.generate_audio,
            audio_status="pending" if req.generate_audio else "none",
            created_at=now,
            updated_at=now,
        )
        self._repos.investigations.put(record)
        self._event(record.investigation_id, "queued", "Investigation queued", status="queued")
        self._queue.send(
            "investigations",
            {
                "job_type": "investigation",
                "job_id": record.investigation_id,
                "investigation_id": record.investigation_id,
                "user_id": user_id,
            },
        )
        logger.info(
            "investigation_queued",
            extra={"investigation_id": record.investigation_id, "attachments": len(attachments)},
        )
        return CreateInvestigationResponse(investigation_id=record.investigation_id, status=record.status)

    def _event(self, investigation_id: str, event_type: str, message: str, **kwargs: Any) -> None:
        self._repos.events.append(
            InvestigationEvent(
                investigation_id=investigation_id,
                seq=0,
                timestamp=utc_now_iso(),
                event_type=event_type,
                message=message,
                **kwargs,
            )
        )

    # ------------------------------------------------------------------ read
    def owned(self, user_id: str, investigation_id: str) -> InvestigationRecord:
        record = self._repos.investigations.get(investigation_id)
        # Same 404 for "missing" and "not yours": never leak the existence of other users' data.
        if record is None or record.user_id != user_id:
            raise NotFoundError("Investigation not found.")
        return record

    def _signed(self, key: str | None, user_id: str, filename: str) -> str | None:
        if not key or not key_belongs_to(key, user_id):
            return None
        return self._storage.presign_get(key, 3600, filename)

    def view(self, user_id: str, investigation_id: str) -> InvestigationView:
        r = self.owned(user_id, investigation_id)
        return InvestigationView(
            investigation_id=r.investigation_id,
            symbol=r.symbol,
            asset_name=r.asset_name,
            asset_type=r.asset_type,
            question=r.question,
            status=r.status,
            progress=r.progress,
            current_agent=r.current_agent,
            status_message=r.status_message,
            plan=r.plan,
            attachments=[a.model_dump(exclude={"storage_key"}) for a in r.attachments],
            result=r.result,
            error=r.error,
            audio_status=r.audio_status,
            audio_url=self._signed(r.audio_key, user_id, f"signalroom-{r.symbol or 'brief'}.wav")
            if r.audio_status == "ready"
            else None,
            infographic_status=r.infographic_status,
            infographic_url=self._signed(r.infographic_key, user_id, "visual-brief.png")
            if r.infographic_status == "ready"
            else None,
            followups=r.followups,
            created_at=r.created_at,
            updated_at=r.updated_at,
            completed_at=r.completed_at,
        )

    def list_summaries(self, user_id: str, limit: int = 20) -> list[InvestigationSummary]:
        out = []
        for r in self._repos.investigations.list_by_user(user_id, limit):
            move = r.result.market.metrics.move_pct if r.result and r.result.market else None
            out.append(
                InvestigationSummary(
                    investigation_id=r.investigation_id,
                    symbol=r.symbol,
                    asset_name=r.asset_name,
                    question=r.question,
                    status=r.status,
                    progress=r.progress,
                    summary=r.summary,
                    move_pct=move,
                    created_at=r.created_at,
                    completed_at=r.completed_at,
                )
            )
        return out

    def events(self, user_id: str, investigation_id: str, after_seq: int = 0) -> list[InvestigationEvent]:
        self.owned(user_id, investigation_id)
        return self._repos.events.list_after(investigation_id, after_seq)

    def transcript(self, user_id: str, investigation_id: str, upload_id: str) -> Transcript:
        r = self.owned(user_id, investigation_id)
        media: list[AudioFindings | VideoFindings] = [*r.result.audio, *r.result.videos] if r.result else []
        for clip in media:
            if (
                clip.upload_id == upload_id
                and clip.transcript_key
                and key_belongs_to(clip.transcript_key, user_id)
            ):
                return Transcript.model_validate(json.loads(self._storage.get_bytes(clip.transcript_key)))
        raise NotFoundError("Transcript not found.")

    # ------------------------------------------------------------------ mutate
    def delete(self, user_id: str, investigation_id: str) -> None:
        self.owned(user_id, investigation_id)
        self._repos.events.delete_for(investigation_id)
        self._repos.investigations.delete(investigation_id)
        self._storage.delete_prefix(f"{user_prefix(user_id)}investigations/{investigation_id}/")

    def retry(self, user_id: str, investigation_id: str) -> CreateInvestigationResponse:
        r = self.owned(user_id, investigation_id)
        if r.status != InvestigationStatus.FAILED:
            raise ConflictError("Only failed investigations can be retried.")
        r.status, r.error, r.progress, r.status_message = "queued", None, 0, "Queued for retry"
        r.updated_at = utc_now_iso()
        self._repos.investigations.put(r)
        self._event(investigation_id, "queued", "Investigation re-queued", status="queued")
        self._queue.send(
            "investigations",
            {
                "job_type": "investigation",
                "job_id": investigation_id,
                "investigation_id": investigation_id,
                "user_id": user_id,
            },
        )
        return CreateInvestigationResponse(investigation_id=investigation_id, status="queued")

    def follow_up(self, user_id: str, investigation_id: str, req: FollowUpRequest) -> FollowUpResponse:
        r = self.owned(user_id, investigation_id)
        if r.status != InvestigationStatus.COMPLETED or r.result is None:
            raise ConflictError("Follow-up questions are available once the investigation is complete.")
        if any(f.status in ("queued", "running") for f in r.followups):
            raise ConflictError("Please wait for the current follow-up to finish.")
        attachments = self._uploads.attachments(user_id, req.upload_ids)
        followup = FollowUp(
            followup_id=new_id("fu"),
            question=" ".join(req.question.split()),
            upload_ids=[a.upload_id for a in attachments],
            created_at=utc_now_iso(),
        )
        known = {a.upload_id for a in r.attachments}
        r.attachments.extend(a for a in attachments if a.upload_id not in known)
        r.followups.append(followup)
        r.updated_at = utc_now_iso()
        self._repos.investigations.put(r)
        self._event(
            investigation_id,
            "followup_queued",
            "Follow-up question queued",
            metadata={"followup_id": followup.followup_id},
        )
        self._queue.send(
            "investigations",
            {
                "job_type": "followup",
                "job_id": followup.followup_id,
                "investigation_id": investigation_id,
                "followup_id": followup.followup_id,
                "user_id": user_id,
            },
        )
        return FollowUpResponse(followup_id=followup.followup_id, status="queued")

    def request_audio(self, user_id: str, investigation_id: str) -> MediaJobResponse:
        r = self.owned(user_id, investigation_id)
        if r.result is None:
            raise ConflictError("Audio can be generated once the investigation is complete.")
        if r.audio_status in ("ready", "pending"):
            return MediaJobResponse(status=r.audio_status)  # never regenerate unchanged audio
        r.audio_status = "pending"
        self._repos.investigations.put(r)
        self._queue.send(
            "investigations",
            {
                "job_type": "investigation_audio",
                "job_id": f"{investigation_id}:audio",
                "investigation_id": investigation_id,
                "user_id": user_id,
            },
        )
        return MediaJobResponse(status="pending")

    def request_infographic(self, user_id: str, investigation_id: str) -> MediaJobResponse:
        r = self.owned(user_id, investigation_id)
        if r.result is None:
            raise ConflictError("A visual brief can be generated once the investigation is complete.")
        if r.infographic_status in ("ready", "pending"):
            return MediaJobResponse(status=r.infographic_status)
        r.infographic_status = "pending"
        self._repos.investigations.put(r)
        self._queue.send(
            "investigations",
            {
                "job_type": "infographic",
                "job_id": f"{investigation_id}:infographic",
                "investigation_id": investigation_id,
                "user_id": user_id,
            },
        )
        return MediaJobResponse(status="pending")
