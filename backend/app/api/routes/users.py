from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import container_dep, current_user, user_service
from app.container import Container
from app.schemas.users import AuthenticatedUser, MeResponse, UserPreferences, UserPreferencesPatch
from app.services.user_service import UserService

router = APIRouter(prefix="/me", tags=["users"])


@router.get("", response_model=MeResponse)
async def me(
    auth: AuthenticatedUser = Depends(current_user),
    users: UserService = Depends(user_service),
    c: Container = Depends(container_dep),
) -> MeResponse:
    user = users.get_or_create(auth)
    return MeResponse(
        user_id=user.user_id,
        email=user.email,
        preferences=user.preferences,
        created_at=user.created_at,
        auth_mode=c.settings.auth_mode,
    )


@router.patch("/preferences", response_model=UserPreferences)
async def update_preferences(
    body: UserPreferencesPatch,
    auth: AuthenticatedUser = Depends(current_user),
    users: UserService = Depends(user_service),
) -> UserPreferences:
    return users.update_preferences(auth, body)


@router.delete("/data", summary="Delete all my investigations, briefings, uploads and profile data")
async def delete_my_data(
    auth: AuthenticatedUser = Depends(current_user), users: UserService = Depends(user_service)
) -> dict[str, int]:
    return users.delete_all_data(auth.user_id)
