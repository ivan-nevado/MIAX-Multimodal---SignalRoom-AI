from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import current_user, user_service
from app.schemas.users import AuthenticatedUser, BriefingPreferences, BriefingPreferencesPatch
from app.services.user_service import UserService

router = APIRouter(prefix="/preferences", tags=["preferences"])


@router.get("/briefing", response_model=BriefingPreferences)
async def get_briefing_preferences(
    auth: AuthenticatedUser = Depends(current_user), users: UserService = Depends(user_service)
) -> BriefingPreferences:
    return users.briefing_preferences(auth)


@router.patch("/briefing", response_model=BriefingPreferences)
async def update_briefing_preferences(
    body: BriefingPreferencesPatch,
    auth: AuthenticatedUser = Depends(current_user),
    users: UserService = Depends(user_service),
) -> BriefingPreferences:
    return users.update_briefing_preferences(auth, body)
