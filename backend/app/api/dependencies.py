"""FastAPI dependencies: authentication and service construction (routes stay thin)."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from app.api.security import AuthError, TokenVerifier
from app.config.logging import user_ref_var
from app.container import Container, get_container
from app.schemas.users import AuthenticatedUser
from app.services.access import ensure_allowed
from app.services.asset_service import AssetService
from app.services.briefing_service import BriefingService
from app.services.investigation_service import InvestigationService
from app.services.local_auth import LocalAuthService
from app.services.search_index import SearchIndexService
from app.services.upload_service import UploadService
from app.services.user_service import UserService
from app.services.watchlist_service import WatchlistService
from app.utils.ids import user_ref


def container_dep() -> Container:
    return get_container()


def local_auth_service(c: Container) -> LocalAuthService:
    return LocalAuthService(
        c.repos.credentials,
        c.settings.local_jwt_secret.get_secret_value(),
        c.settings.local_token_ttl_minutes,
        c.settings.allowed_emails,
    )


def token_verifier(c: Container = Depends(container_dep)) -> TokenVerifier:
    """One verifier per container (keeps the Cognito JWKS cache warm). Tests may pre-seed it."""
    verifier = c.__dict__.get("verifier")
    if verifier is None:
        verifier = TokenVerifier(c.settings, local_auth_service(c))
        c.__dict__["verifier"] = verifier
    return verifier


def asset_service(c: Container = Depends(container_dep)) -> AssetService:
    return AssetService(c.market, c.news, c.repos.investigations, c.financial)


def watchlist_service(
    c: Container = Depends(container_dep), assets: AssetService = Depends(asset_service)
) -> WatchlistService:
    return WatchlistService(c.repos.watchlists, assets, c.settings.watchlist_max_size)


def user_service(
    c: Container = Depends(container_dep), watchlists: WatchlistService = Depends(watchlist_service)
) -> UserService:
    return UserService(c.repos, c.storage, watchlists)


def upload_service(c: Container = Depends(container_dep)) -> UploadService:
    return UploadService(c.repos.uploads, c.storage, c.settings)


def investigation_service(
    c: Container = Depends(container_dep),
    uploads: UploadService = Depends(upload_service),
    assets: AssetService = Depends(asset_service),
) -> InvestigationService:
    return InvestigationService(
        c.repos, c.queue, c.storage, uploads, assets.resolver, c.settings.max_investigations_per_day
    )


def search_service(c: Container = Depends(container_dep)) -> SearchIndexService:
    return c.search_index()


def briefing_service(c: Container = Depends(container_dep)) -> BriefingService:
    return BriefingService(c.repos, c.queue, c.storage, c.settings)


def _bearer(request: Request) -> str:
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Authentication required", headers={"WWW-Authenticate": "Bearer"}
        )
    return token.strip()


def current_user(
    request: Request,
    verifier: TokenVerifier = Depends(token_verifier),
    users: UserService = Depends(user_service),
    c: Container = Depends(container_dep),
) -> AuthenticatedUser:
    token = _bearer(request)
    try:
        auth = verifier.verify(token)
    except AuthError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Invalid or expired session", headers={"WWW-Authenticate": "Bearer"}
        ) from exc
    if c.settings.allowed_emails:
        email = auth.email
        if not email:  # access tokens carry no email: fall back to the stored profile
            stored = c.repos.users.get(auth.user_id)
            email = stored.email if stored else None
        ensure_allowed(email, c.settings.allowed_emails)
    users.get_or_create(auth)  # first request provisions the profile + demo watchlist
    request.state.user_id = auth.user_id
    user_ref_var.set(user_ref(auth.user_id))
    return auth
