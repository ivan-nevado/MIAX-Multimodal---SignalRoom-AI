from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Header, Query, Response
from fastapi.responses import StreamingResponse

from app.api.dependencies import current_user, investigation_service
from app.models.status import TERMINAL_STATUSES
from app.schemas.agents import Transcript
from app.schemas.investigations import (
    CreateInvestigationRequest,
    CreateInvestigationResponse,
    FollowUpRequest,
    FollowUpResponse,
    InvestigationEvent,
    InvestigationSummary,
    InvestigationView,
    MediaJobResponse,
)
from app.schemas.users import AuthenticatedUser
from app.services.investigation_service import InvestigationService

router = APIRouter(prefix="/investigations", tags=["investigations"])

SSE_MAX_SECONDS = 50  # CloudFront/ALB friendly; the client reconnects with Last-Event-ID
SSE_POLL_SECONDS = 1.0
SSE_KEEPALIVE_SECONDS = 15


@router.post(
    "",
    response_model=CreateInvestigationResponse,
    status_code=202,
    summary="Queue an investigation (returns immediately)",
)
async def create_investigation(
    body: CreateInvestigationRequest,
    auth: AuthenticatedUser = Depends(current_user),
    svc: InvestigationService = Depends(investigation_service),
) -> CreateInvestigationResponse:
    return await svc.create(auth.user_id, body)


@router.get("", response_model=list[InvestigationSummary])
async def list_investigations(
    limit: int = Query(20, ge=1, le=100),
    auth: AuthenticatedUser = Depends(current_user),
    svc: InvestigationService = Depends(investigation_service),
) -> list[InvestigationSummary]:
    return svc.list_summaries(auth.user_id, limit)


@router.get("/{investigation_id}", response_model=InvestigationView)
async def get_investigation(
    investigation_id: str,
    auth: AuthenticatedUser = Depends(current_user),
    svc: InvestigationService = Depends(investigation_service),
) -> InvestigationView:
    return svc.view(auth.user_id, investigation_id)


@router.get(
    "/{investigation_id}/events", summary="Progress as Server-Sent Events (JSON list with ?format=json)"
)
async def investigation_events(
    investigation_id: str,
    after: int = Query(0, ge=0),
    format: str = Query("sse", pattern="^(sse|json)$"),
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    auth: AuthenticatedUser = Depends(current_user),
    svc: InvestigationService = Depends(investigation_service),
) -> Response:
    start_after = int(last_event_id) if last_event_id and last_event_id.isdigit() else after
    if format == "json":  # polling fallback
        events = svc.events(auth.user_id, investigation_id, start_after)
        return Response(json.dumps([e.model_dump() for e in events]), media_type="application/json")
    svc.owned(auth.user_id, investigation_id)  # 404 before opening the stream

    async def stream() -> AsyncIterator[str]:
        last = start_after
        started = last_ping = time.monotonic()
        yield "retry: 2000\n\n"
        while time.monotonic() - started < SSE_MAX_SECONDS:
            events: list[InvestigationEvent] = await asyncio.to_thread(
                svc.events, auth.user_id, investigation_id, last
            )
            for event in events:
                last = event.seq
                yield f"id: {event.seq}\nevent: progress\ndata: {event.model_dump_json()}\n\n"
            record = await asyncio.to_thread(svc.owned, auth.user_id, investigation_id)
            busy = (
                any(f.status in ("queued", "running") for f in record.followups)
                or record.audio_status == "pending"
                or record.infographic_status == "pending"
            )
            if record.status in TERMINAL_STATUSES and not busy:
                yield f"event: end\ndata: {json.dumps({'status': record.status})}\n\n"
                return
            if time.monotonic() - last_ping > SSE_KEEPALIVE_SECONDS:
                last_ping = time.monotonic()
                yield ": keep-alive\n\n"
            await asyncio.sleep(SSE_POLL_SECONDS)
        yield "event: reconnect\ndata: {}\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.delete("/{investigation_id}", status_code=204)
async def delete_investigation(
    investigation_id: str,
    auth: AuthenticatedUser = Depends(current_user),
    svc: InvestigationService = Depends(investigation_service),
) -> Response:
    svc.delete(auth.user_id, investigation_id)
    return Response(status_code=204)


@router.post("/{investigation_id}/retry", response_model=CreateInvestigationResponse, status_code=202)
async def retry_investigation(
    investigation_id: str,
    auth: AuthenticatedUser = Depends(current_user),
    svc: InvestigationService = Depends(investigation_service),
) -> CreateInvestigationResponse:
    return svc.retry(auth.user_id, investigation_id)


@router.post("/{investigation_id}/followups", response_model=FollowUpResponse, status_code=202)
async def ask_followup(
    investigation_id: str,
    body: FollowUpRequest,
    auth: AuthenticatedUser = Depends(current_user),
    svc: InvestigationService = Depends(investigation_service),
) -> FollowUpResponse:
    return svc.follow_up(auth.user_id, investigation_id, body)


@router.post(
    "/{investigation_id}/audio",
    response_model=MediaJobResponse,
    status_code=202,
    summary="Generate the audio briefing (TTS)",
)
async def request_audio(
    investigation_id: str,
    auth: AuthenticatedUser = Depends(current_user),
    svc: InvestigationService = Depends(investigation_service),
) -> MediaJobResponse:
    return svc.request_audio(auth.user_id, investigation_id)


@router.post(
    "/{investigation_id}/infographic",
    response_model=MediaJobResponse,
    status_code=202,
    summary="Generate the visual brief (text-to-image)",
)
async def request_infographic(
    investigation_id: str,
    auth: AuthenticatedUser = Depends(current_user),
    svc: InvestigationService = Depends(investigation_service),
) -> MediaJobResponse:
    return svc.request_infographic(auth.user_id, investigation_id)


@router.get("/{investigation_id}/transcripts/{upload_id}", response_model=Transcript)
async def get_transcript(
    investigation_id: str,
    upload_id: str,
    auth: AuthenticatedUser = Depends(current_user),
    svc: InvestigationService = Depends(investigation_service),
) -> Transcript:
    return svc.transcript(auth.user_id, investigation_id, upload_id)
