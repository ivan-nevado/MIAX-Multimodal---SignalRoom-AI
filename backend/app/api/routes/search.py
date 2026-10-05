from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, UploadFile

from app.api.dependencies import current_user, search_service
from app.schemas.users import AuthenticatedUser
from app.services.errors import ValidationFailed
from app.services.search_index import SearchIndexService, SearchModality, SearchResponse

router = APIRouter(tags=["search"])

MAX_QUERY_IMAGE_BYTES = 5 * 1024 * 1024
IMAGE_SIGNATURES = {"image/png": b"\x89PNG", "image/jpeg": b"\xff\xd8\xff", "image/webp": b"RIFF"}


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str = Query(min_length=2, max_length=300),
    modality: SearchModality = "all",
    limit: int = Query(default=20, ge=1, le=50),
    auth: AuthenticatedUser = Depends(current_user),
    svc: SearchIndexService = Depends(search_service),
) -> SearchResponse:
    """Semantic search across the user's investigations: summaries, news, PDFs, calls, videos, images."""
    return await svc.search(auth.user_id, q, modality, limit)


@router.post("/search/by-image", response_model=SearchResponse)
async def search_by_image(
    file: UploadFile = File(...),
    modality: SearchModality = "all",
    auth: AuthenticatedUser = Depends(current_user),
    svc: SearchIndexService = Depends(search_service),
) -> SearchResponse:
    """Find passages and images similar to a query image (e.g. a chart screenshot)."""
    data = await file.read(MAX_QUERY_IMAGE_BYTES + 1)
    if len(data) > MAX_QUERY_IMAGE_BYTES:
        raise ValidationFailed("Query image too large (max 5 MB).")
    mime = next((m for m, sig in IMAGE_SIGNATURES.items() if data.startswith(sig)), None)
    if mime is None or (mime == "image/webp" and data[8:12] != b"WEBP"):
        raise ValidationFailed("Upload a PNG, JPEG or WebP image.")
    return await svc.search_by_image(auth.user_id, data, mime, modality)
