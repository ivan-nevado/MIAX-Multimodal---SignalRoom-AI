from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Depends

from app.api.dependencies import container_dep
from app.container import Container
from app.utils.time import utc_now_iso

router = APIRouter(tags=["health"])
VERSION = "0.1.0"


@router.get("/health/live", summary="Liveness probe (ALB target group)")
async def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health", summary="Readiness: database, storage and provider configuration")
async def health(c: Container = Depends(container_dep)) -> dict[str, Any]:
    checks: dict[str, str] = {"api": "ok"}

    def db_check() -> None:
        c.repos.users.get("__healthcheck__")

    def storage_check() -> None:
        c.storage.size("__healthcheck__/probe")

    for name, fn in (("database", db_check), ("storage", storage_check)):
        try:
            await asyncio.wait_for(asyncio.to_thread(fn), timeout=5)
            checks[name] = "ok"
        except Exception as exc:
            checks[name] = f"error: {type(exc).__name__}"
    # Optional providers never make the service unhealthy — they are reported, not required.
    status = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {
        "status": status,
        "version": VERSION,
        "time": utc_now_iso(),
        "backend": c.settings.backend_mode,
        "auth": c.settings.auth_mode,
        "checks": checks,
        "providers": c.settings.provider_status(),
        "ai_models": c.ai.describe(),
    }
