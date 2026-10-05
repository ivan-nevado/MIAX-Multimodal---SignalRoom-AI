from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from app.api.dependencies import current_user, watchlist_service
from app.schemas.assets import AddWatchlistRequest, ReorderWatchlistRequest, WatchlistItemView
from app.schemas.users import AuthenticatedUser
from app.services.watchlist_service import WatchlistService

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("", response_model=list[WatchlistItemView])
async def get_watchlist(
    auth: AuthenticatedUser = Depends(current_user), svc: WatchlistService = Depends(watchlist_service)
) -> list[WatchlistItemView]:
    return await svc.list_items(auth.user_id)


@router.post("", response_model=WatchlistItemView, status_code=201)
async def add_to_watchlist(
    body: AddWatchlistRequest,
    auth: AuthenticatedUser = Depends(current_user),
    svc: WatchlistService = Depends(watchlist_service),
) -> WatchlistItemView:
    return await svc.add(auth.user_id, body.symbol, body.display_name)


@router.put("/order", status_code=204)
async def reorder_watchlist(
    body: ReorderWatchlistRequest,
    auth: AuthenticatedUser = Depends(current_user),
    svc: WatchlistService = Depends(watchlist_service),
) -> Response:
    svc.reorder(auth.user_id, body.symbols)
    return Response(status_code=204)


@router.delete("/{symbol}", status_code=204)
async def remove_from_watchlist(
    symbol: str,
    auth: AuthenticatedUser = Depends(current_user),
    svc: WatchlistService = Depends(watchlist_service),
) -> Response:
    svc.remove(auth.user_id, symbol)
    return Response(status_code=204)
