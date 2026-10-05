"""Auth endpoints. In AWS, sign-up/login/verification/forgot-password are handled by Cognito
directly from the browser; these local endpoints exist only when AUTH_MODE=local."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import container_dep, local_auth_service
from app.container import Container
from app.schemas.users import LocalAuthRequest, LocalAuthResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/config", summary="Public auth configuration for the SPA")
async def auth_config(c: Container = Depends(container_dep)) -> dict[str, Any]:
    s = c.settings
    return {
        "mode": s.auth_mode,
        "invite_only": bool(s.allowed_emails.strip()),
        "cognito": {
            "region": s.effective_cognito_region,
            "user_pool_id": s.cognito_user_pool_id,
            "client_id": s.cognito_app_client_id,
        }
        if s.auth_mode == "cognito"
        else None,
    }


def _require_local(c: Container) -> None:
    if c.settings.auth_mode != "local":
        raise HTTPException(404, "Not found")


@router.post("/local/signup", response_model=LocalAuthResponse, summary="Local development sign-up")
async def local_signup(body: LocalAuthRequest, c: Container = Depends(container_dep)) -> LocalAuthResponse:
    _require_local(c)
    token, user_id, ttl = local_auth_service(c).signup(body.email, body.password)
    return LocalAuthResponse(access_token=token, expires_in=ttl, user_id=user_id, email=body.email)


@router.post("/local/login", response_model=LocalAuthResponse, summary="Local development login")
async def local_login(body: LocalAuthRequest, c: Container = Depends(container_dep)) -> LocalAuthResponse:
    _require_local(c)
    token, user_id, ttl = local_auth_service(c).login(body.email, body.password)
    return LocalAuthResponse(access_token=token, expires_in=ttl, user_id=user_id, email=body.email)
