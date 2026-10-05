from __future__ import annotations

from typing import Protocol


class StorageBackend(Protocol):
    name: str

    def put_bytes(self, key: str, data: bytes, content_type: str) -> None: ...
    def get_bytes(self, key: str) -> bytes: ...
    def read_head(self, key: str, length: int = 16) -> bytes: ...
    def size(self, key: str) -> int | None: ...
    def delete(self, key: str) -> None: ...
    def delete_prefix(self, prefix: str) -> int: ...
    def presign_put(
        self, key: str, content_type: str, size_bytes: int, expires: int = 900
    ) -> tuple[str, dict[str, str]]: ...
    def presign_get(self, key: str, expires: int = 3600, filename: str | None = None) -> str: ...


def user_prefix(user_id: str) -> str:
    return f"users/{user_id}/"


def upload_key(user_id: str, kind: str, upload_id: str, filename: str) -> str:
    folder = {"document": "documents", "image": "images", "audio": "audio", "video": "videos"}[kind]
    return f"{user_prefix(user_id)}uploads/{folder}/{upload_id}/{filename}"


def investigation_output_key(user_id: str, investigation_id: str, category: str, filename: str) -> str:
    return f"{user_prefix(user_id)}investigations/{investigation_id}/output/{category}/{filename}"


def briefing_output_key(user_id: str, briefing_id: str, filename: str) -> str:
    return f"{user_prefix(user_id)}briefings/{briefing_id}/output/{filename}"


def key_belongs_to(key: str, user_id: str) -> bool:
    return key.startswith(user_prefix(user_id)) and ".." not in key
