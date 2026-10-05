from __future__ import annotations

import logging

from app.integrations.storage.base import StorageBackend, user_prefix
from app.repositories.base import Repositories
from app.schemas.users import (
    AuthenticatedUser,
    BriefingPreferences,
    BriefingPreferencesPatch,
    UserPreferences,
    UserPreferencesPatch,
    UserRecord,
)
from app.services.watchlist_service import WatchlistService
from app.utils.time import utc_now_iso

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, repos: Repositories, storage: StorageBackend, watchlists: WatchlistService) -> None:
        self._repos = repos
        self._storage = storage
        self._watchlists = watchlists

    def get_or_create(self, auth: AuthenticatedUser) -> UserRecord:
        user = self._repos.users.get(auth.user_id)
        if user is None:
            user = UserRecord(user_id=auth.user_id, email=auth.email or "", created_at=utc_now_iso())
            self._repos.users.put(user)
            self._watchlists.seed_demo(auth.user_id)
        elif auth.email and user.email != auth.email:
            user.email = auth.email
            self._repos.users.put(user)
        return user

    def update_preferences(self, auth: AuthenticatedUser, patch: UserPreferencesPatch) -> UserPreferences:
        user = self.get_or_create(auth)
        data = user.preferences.model_dump()
        data.update(patch.model_dump(exclude_none=True))
        user.preferences = UserPreferences.model_validate(data)
        self._repos.users.put(user)
        return user.preferences

    def briefing_preferences(self, auth: AuthenticatedUser) -> BriefingPreferences:
        return self.get_or_create(auth).preferences.briefing

    def update_briefing_preferences(
        self, auth: AuthenticatedUser, patch: BriefingPreferencesPatch
    ) -> BriefingPreferences:
        user = self.get_or_create(auth)
        data = user.preferences.briefing.model_dump()
        data.update(patch.model_dump(exclude_none=True))
        user.preferences.briefing = BriefingPreferences.model_validate(data)
        self._repos.users.put(user)
        return user.preferences.briefing

    def delete_all_data(self, user_id: str) -> dict[str, int]:
        """Delete investigations, events, briefings, uploads, files, watchlist and profile."""
        counts = {"investigations": 0, "briefings": 0, "uploads": 0, "files": 0}
        for record in self._repos.investigations.list_by_user(user_id, 1000):
            self._repos.events.delete_for(record.investigation_id)
            self._repos.investigations.delete(record.investigation_id)
            counts["investigations"] += 1
        for briefing in self._repos.briefings.list_by_user(user_id, 1000):
            self._repos.briefings.delete(briefing.briefing_id)
            counts["briefings"] += 1
        for upload in self._repos.uploads.list_by_user(user_id):
            self._repos.uploads.delete(upload.upload_id)
            counts["uploads"] += 1
        counts["files"] = self._storage.delete_prefix(user_prefix(user_id))
        self._repos.watchlists.delete_all(user_id)
        self._repos.users.delete(user_id)
        logger.info("user_data_deleted", extra=counts)
        return counts
