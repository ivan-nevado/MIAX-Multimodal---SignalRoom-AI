"""Direct-to-storage uploads: presign → browser PUT → complete (validated) → used by investigations."""

from __future__ import annotations

from pathlib import PurePosixPath

from app.config.settings import Settings
from app.integrations.storage.base import StorageBackend, key_belongs_to, upload_key
from app.repositories.base import UploadRepository
from app.schemas.investigations import AttachmentRef
from app.schemas.uploads import (
    ALLOWED_TYPES,
    MIME_ALIASES,
    PresignRequest,
    PresignResponse,
    UploadRecord,
    UploadView,
)
from app.services.errors import ForbiddenError, NotFoundError, ValidationFailed
from app.utils.ids import new_id
from app.utils.images import sniff_image_mime
from app.utils.time import utc_now_iso

PRESIGN_TTL = 900


def normalise_mime(content_type: str) -> str:
    base = content_type.split(";")[0].strip().lower()
    return MIME_ALIASES.get(base, base)


def validate_file(kind: str, filename: str, content_type: str, size_bytes: int, settings: Settings) -> str:
    ext = PurePosixPath(filename.lower()).suffix
    allowed = ALLOWED_TYPES[kind]
    if ext not in allowed:
        raise ValidationFailed(
            f"Unsupported {kind} type '{ext or 'none'}'. Allowed: {', '.join(sorted(allowed))}."
        )
    mime = normalise_mime(content_type)
    if mime != allowed[ext]:
        raise ValidationFailed(f"MIME type {content_type} does not match the {ext} extension.")
    limit_mb = {
        "document": settings.max_document_mb,
        "image": settings.max_image_mb,
        "audio": settings.max_audio_mb,
        "video": settings.max_video_mb,
    }[kind]
    if size_bytes > limit_mb * 1024 * 1024:
        raise ValidationFailed(f"File is too large. Maximum size for {kind}s is {limit_mb} MB.")
    return mime


def validate_content(kind: str, mime: str, head: bytes) -> None:
    """Magic-byte check after upload: the declared type must match the actual bytes."""
    if kind == "document" and not head.startswith(b"%PDF"):
        raise ValidationFailed("The uploaded file is not a valid PDF.")
    if kind == "video":
        is_mp4 = head[4:8] == b"ftyp"  # MP4 / QuickTime
        is_webm = head[:4] == b"\x1aE\xdf\xa3"  # EBML header
        if not (is_mp4 or is_webm):
            raise ValidationFailed("The uploaded file is not a valid MP4, MOV or WebM video.")
    if kind == "image":
        sniffed = sniff_image_mime(head)
        if sniffed is None or sniffed != mime:
            raise ValidationFailed("The uploaded file is not a valid image of the declared type.")


class UploadService:
    def __init__(self, repo: UploadRepository, storage: StorageBackend, settings: Settings) -> None:
        self._repo = repo
        self._storage = storage
        self._settings = settings

    def presign(self, user_id: str, req: PresignRequest) -> PresignResponse:
        mime = validate_file(req.kind, req.filename, req.content_type, req.size_bytes, self._settings)
        upload_id = new_id("up")
        key = upload_key(user_id, req.kind, upload_id, req.filename)
        url, headers = self._storage.presign_put(key, mime, req.size_bytes, PRESIGN_TTL)
        self._repo.put(
            UploadRecord(
                upload_id=upload_id,
                user_id=user_id,
                kind=req.kind,
                filename=req.filename,
                content_type=mime,
                size_bytes=req.size_bytes,
                storage_key=key,
                created_at=utc_now_iso(),
            )
        )
        return PresignResponse(upload_id=upload_id, upload_url=url, headers=headers, expires_in=PRESIGN_TTL)

    def _owned(self, user_id: str, upload_id: str) -> UploadRecord:
        record = self._repo.get(upload_id)
        if record is None or record.status == "deleted":
            raise NotFoundError("Upload not found.")
        if record.user_id != user_id or not key_belongs_to(record.storage_key, user_id):
            raise ForbiddenError("You do not have access to this upload.")
        return record

    def complete(self, user_id: str, upload_id: str) -> UploadView:
        record = self._owned(user_id, upload_id)
        size = self._storage.size(record.storage_key)
        if size is None:
            raise ValidationFailed("The file has not been uploaded yet.")
        limit = {
            "document": self._settings.max_document_mb,
            "image": self._settings.max_image_mb,
            "audio": self._settings.max_audio_mb,
            "video": self._settings.max_video_mb,
        }[record.kind]
        if size > limit * 1024 * 1024:
            self._storage.delete(record.storage_key)
            raise ValidationFailed("Uploaded file exceeds the size limit.")
        if record.kind != "audio":
            validate_content(
                record.kind, record.content_type, self._storage.read_head(record.storage_key, 16)
            )
        record.status = "uploaded"
        record.size_bytes = size
        record.completed_at = utc_now_iso()
        self._repo.put(record)
        return self.view(record)

    def attachments(self, user_id: str, upload_ids: list[str]) -> list[AttachmentRef]:
        refs = []
        for upload_id in dict.fromkeys(upload_ids):
            record = self._owned(user_id, upload_id)
            if record.status != "uploaded":
                raise ValidationFailed(f"{record.filename} has not finished uploading.")
            refs.append(
                AttachmentRef(
                    upload_id=record.upload_id,
                    kind=record.kind,
                    filename=record.filename,
                    content_type=record.content_type,
                    storage_key=record.storage_key,
                    size_bytes=record.size_bytes,
                )
            )
        return refs

    def delete(self, user_id: str, upload_id: str) -> None:
        record = self._owned(user_id, upload_id)
        self._storage.delete(record.storage_key)
        self._repo.delete(upload_id)

    @staticmethod
    def view(record: UploadRecord) -> UploadView:
        return UploadView(**record.model_dump(include=set(UploadView.model_fields)))
