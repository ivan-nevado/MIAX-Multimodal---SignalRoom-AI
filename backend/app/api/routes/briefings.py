from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse

from app.api.dependencies import briefing_service, current_user
from app.schemas.briefings import (
    BriefingSummary,
    BriefingView,
    GenerateBriefingRequest,
    GenerateBriefingResponse,
)
from app.schemas.users import AuthenticatedUser
from app.services.briefing_service import BriefingService

router = APIRouter(prefix="/briefings", tags=["briefings"])


@router.get("", response_model=list[BriefingSummary])
async def list_briefings(
    limit: int = Query(20, ge=1, le=100),
    auth: AuthenticatedUser = Depends(current_user),
    svc: BriefingService = Depends(briefing_service),
) -> list[BriefingSummary]:
    return svc.list_summaries(auth.user_id, limit)


@router.post("/generate", response_model=GenerateBriefingResponse, status_code=202)
async def generate_briefing(
    body: GenerateBriefingRequest,
    auth: AuthenticatedUser = Depends(current_user),
    svc: BriefingService = Depends(briefing_service),
) -> GenerateBriefingResponse:
    return svc.generate(auth.user_id, body)


@router.get("/{briefing_id}", response_model=BriefingView)
async def get_briefing(
    briefing_id: str,
    auth: AuthenticatedUser = Depends(current_user),
    svc: BriefingService = Depends(briefing_service),
) -> BriefingView:
    return svc.view(auth.user_id, briefing_id)


@router.get(
    "/{briefing_id}/email-preview",
    response_class=HTMLResponse,
    summary="Rendered daily briefing email (HTML)",
)
async def email_preview(
    briefing_id: str,
    auth: AuthenticatedUser = Depends(current_user),
    svc: BriefingService = Depends(briefing_service),
) -> HTMLResponse:
    return HTMLResponse(svc.email_preview(auth.user_id, briefing_id))
