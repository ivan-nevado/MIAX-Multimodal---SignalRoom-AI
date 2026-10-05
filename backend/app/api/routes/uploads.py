from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile

from app.api.dependencies import container_dep, current_user, upload_service
from app.container import Container
from app.integrations.ai.base import AIError, AudioInput
from app.prompts.loader import system_prompt
from app.schemas.agents import Transcript
from app.schemas.uploads import (
    CompleteUploadRequest,
    PresignRequest,
    PresignResponse,
    UploadView,
    VoiceCommandResponse,
)
from app.schemas.users import AuthenticatedUser
from app.services.entity_resolution import find_alias_in_text
from app.services.errors import UpstreamUnavailable, ValidationFailed
from app.services.upload_service import UploadService

router = APIRouter(tags=["uploads"])


@router.post(
    "/uploads/presign",
    response_model=PresignResponse,
    summary="Presigned URL for a direct browser → storage upload",
)
async def presign_upload(
    body: PresignRequest,
    auth: AuthenticatedUser = Depends(current_user),
    svc: UploadService = Depends(upload_service),
) -> PresignResponse:
    return svc.presign(auth.user_id, body)


@router.post(
    "/uploads/complete",
    response_model=UploadView,
    summary="Validate an uploaded object (size, type, ownership)",
)
async def complete_upload(
    body: CompleteUploadRequest,
    auth: AuthenticatedUser = Depends(current_user),
    svc: UploadService = Depends(upload_service),
) -> UploadView:
    return await asyncio.to_thread(svc.complete, auth.user_id, body.upload_id)


@router.delete("/uploads/{upload_id}", status_code=204)
async def delete_upload(
    upload_id: str,
    auth: AuthenticatedUser = Depends(current_user),
    svc: UploadService = Depends(upload_service),
) -> Response:
    svc.delete(auth.user_id, upload_id)
    return Response(status_code=204)


@router.post(
    "/voice/transcribe",
    response_model=VoiceCommandResponse,
    summary="Short voice command → text (≤ 4 MB WAV)",
)
async def transcribe_voice_command(
    file: UploadFile = File(...),
    auth: AuthenticatedUser = Depends(current_user),
    c: Container = Depends(container_dep),
) -> VoiceCommandResponse:
    # Voice commands are tiny (a few seconds), so a synchronous call is acceptable here;
    # uploaded recordings (earnings calls) always go through S3 + the worker instead.
    data = await file.read(c.settings.max_voice_command_mb * 1024 * 1024 + 1)
    if len(data) > c.settings.max_voice_command_mb * 1024 * 1024:
        raise ValidationFailed("Voice command too long.")
    if not data.startswith(b"RIFF"):
        raise ValidationFailed("Voice commands must be WAV audio.")
    if not c.ai.available("transcription"):
        raise UpstreamUnavailable("Voice input is not available: no transcription model configured.")
    try:
        transcript = await c.ai.structured(
            Transcript,
            system=system_prompt("transcription"),
            user="Transcribe this short voice command from a user of a financial research app.",
            audio=[AudioInput(data, "audio/wav")],
            role="transcription",
            agent="voice_command",
            purpose="voice_command",
            max_tokens=800,
            temperature=0.0,
        )
    except AIError as exc:
        raise UpstreamUnavailable("Could not transcribe the voice command. Please try again.") from exc
    text = " ".join(s.text for s in transcript.segments).strip()
    match = find_alias_in_text(text)
    return VoiceCommandResponse(
        text=text,
        language=transcript.language,
        resolved_symbol=match.symbol if match else None,
        resolved_name=match.name if match else None,
    )


# ---------------------------------------------------------------- local development storage
@router.put("/local-storage/{token}", include_in_schema=False)
async def local_storage_put(token: str, request: Request, c: Container = Depends(container_dep)) -> Response:
    from app.integrations.storage.local import InvalidStorageToken, LocalStorage

    storage = c.storage
    if not isinstance(storage, LocalStorage):
        raise HTTPException(404, "Not found")
    try:
        claims = storage.verify_token(token, "PUT")
    except InvalidStorageToken as exc:
        raise HTTPException(403, "Invalid or expired upload URL") from exc
    if request.headers.get("content-type", "").split(";")[0] != claims["ct"]:
        raise HTTPException(400, "Content-Type does not match the presigned type")
    body = await request.body()
    if len(body) > int(claims["max"]) * 1.05 + 1024:
        raise HTTPException(413, "File larger than declared")
    await asyncio.to_thread(storage.put_bytes, claims["k"], body, claims["ct"])
    return Response(status_code=200)


@router.get("/local-storage/{token}", include_in_schema=False)
async def local_storage_get(token: str, c: Container = Depends(container_dep)) -> Response:
    from app.integrations.storage.local import InvalidStorageToken, LocalStorage

    storage = c.storage
    if not isinstance(storage, LocalStorage):
        raise HTTPException(404, "Not found")
    try:
        claims = storage.verify_token(token, "GET")
    except InvalidStorageToken as exc:
        raise HTTPException(403, "Invalid or expired URL") from exc
    try:
        data = await asyncio.to_thread(storage.get_bytes, claims["k"])
    except FileNotFoundError as exc:
        raise HTTPException(404, "Not found") from exc
    headers = {"Cache-Control": "private, max-age=3600"}
    if claims.get("fn"):
        headers["Content-Disposition"] = f'inline; filename="{claims["fn"]}"'
    return Response(data, media_type=storage.content_type(claims["k"]), headers=headers)
