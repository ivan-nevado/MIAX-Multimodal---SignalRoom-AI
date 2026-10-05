from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import asset_service, current_user
from app.schemas.assets import AssetDetail, AssetMatch, MarketOverview
from app.schemas.users import AuthenticatedUser
from app.services.asset_service import AssetService

router = APIRouter(tags=["assets"])


@router.get("/assets/search", response_model=list[AssetMatch])
async def search_assets(
    q: str = Query(min_length=1, max_length=64),
    auth: AuthenticatedUser = Depends(current_user),
    svc: AssetService = Depends(asset_service),
) -> list[AssetMatch]:
    return await svc.search(q)


@router.get("/assets/{symbol}", response_model=AssetDetail)
async def get_asset(
    symbol: str,
    range: Literal["1d", "5d", "1mo", "6mo", "1y"] = "1mo",
    auth: AuthenticatedUser = Depends(current_user),
    svc: AssetService = Depends(asset_service),
) -> AssetDetail:
    return await svc.detail(symbol, range, auth.user_id)


@router.get("/market/overview", response_model=MarketOverview)
async def market_overview(
    auth: AuthenticatedUser = Depends(current_user), svc: AssetService = Depends(asset_service)
) -> MarketOverview:
    return await svc.overview()
