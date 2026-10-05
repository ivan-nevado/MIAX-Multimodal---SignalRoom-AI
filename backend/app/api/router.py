from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import (
    assets,
    auth,
    briefings,
    health,
    investigations,
    preferences,
    search,
    uploads,
    users,
    watchlists,
)

api_router = APIRouter(prefix="/api/v1")
for module in (
    health,
    auth,
    users,
    watchlists,
    assets,
    investigations,
    uploads,
    briefings,
    preferences,
    search,
):
    api_router.include_router(module.router)
