from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator

from app.schemas.common import Model

UploadKind = Literal["document", "image", "audio", "video"]

# Allow-list: kind -> {extension: mime}
ALLOWED_TYPES: dict[str, dict[str, str]] = {
    "document": {".pdf": "application/pdf"},
    "image": {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"},
    "audio": {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".ogg": "audio/ogg",
        ".flac": "audio/flac",
    },
    "video": {".mp4": "video/mp4", ".webm": "video/webm", ".mov": "video/quicktime"},
}

MIME_ALIASES = {
    "audio/x-wav": "audio/wav",
    "audio/wave": "audio/wav",
    "audio/mp3": "audio/mpeg",
    "audio/x-m4a": "audio/mp4",
    "audio/m4a": "audio/mp4",
    "image/jpg": "image/jpeg",
    "audio/x-flac": "audio/flac",
}


class PresignRequest(Model):
    filename: str = Field(min_length=1, max_length=200)
    content_type: str = Field(max_length=100)
    size_bytes: int = Field(gt=0)
    kind: UploadKind

    @field_validator("filename")
    @classmethod
    def _safe_name(cls, v: str) -> str:
        name = v.replace("\\", "/").split("/")[-1].strip()
        if not name or name.startswith("."):
            raise ValueError("Invalid filename")
        return name


class PresignResponse(Model):
    upload_id: str
    upload_url: str
    method: Literal["PUT"] = "PUT"
    headers: dict[str, str]
    expires_in: int


class CompleteUploadRequest(Model):
    upload_id: str


class UploadRecord(Model):
    upload_id: str
    user_id: str
    kind: UploadKind
    filename: str
    content_type: str
    size_bytes: int
    storage_key: str
    status: Literal["pending", "uploaded", "deleted"] = "pending"
    created_at: str
    completed_at: str | None = None


class UploadView(Model):
    upload_id: str
    kind: UploadKind
    filename: str
    content_type: str
    size_bytes: int
    status: str
    created_at: str


class VoiceCommandResponse(Model):
    text: str
    language: str | None = None
    resolved_symbol: str | None = None
    resolved_name: str | None = None
