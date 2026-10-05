"""Local file storage that mimics S3 presigned URLs with HMAC-signed tokens (development only)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import shutil
import time
from pathlib import Path
from typing import Any


class InvalidStorageToken(Exception):
    pass


class LocalStorage:
    name = "local"

    def __init__(self, root: Path, *, signing_secret: str, public_base_url: str) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)
        self._secret = signing_secret.encode("utf-8")
        self._base_url = public_base_url.rstrip("/")

    def _path(self, key: str) -> Path:
        if ".." in key or key.startswith("/"):
            raise ValueError("Invalid storage key")
        return self._root / key

    def put_bytes(self, key: str, data: bytes, content_type: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        path.with_name(path.name + ".meta").write_text(json.dumps({"content_type": content_type}))

    def get_bytes(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def read_head(self, key: str, length: int = 16) -> bytes:
        with self._path(key).open("rb") as fh:
            return fh.read(length)

    def content_type(self, key: str) -> str:
        meta = self._path(key).with_name(self._path(key).name + ".meta")
        if meta.exists():
            ct: str = json.loads(meta.read_text()).get("content_type", "application/octet-stream")
            return ct
        return "application/octet-stream"

    def size(self, key: str) -> int | None:
        path = self._path(key)
        return path.stat().st_size if path.exists() else None

    def delete(self, key: str) -> None:
        path = self._path(key)
        for p in (path, path.with_name(path.name + ".meta")):
            if p.exists():
                p.unlink()

    def delete_prefix(self, prefix: str) -> int:
        path = self._path(prefix.rstrip("/"))
        if not path.exists():
            return 0
        count = sum(1 for p in path.rglob("*") if p.is_file() and not p.name.endswith(".meta"))
        shutil.rmtree(path)
        return count

    # ------------------------------------------------------------------ signed tokens
    def _sign(self, payload: dict[str, Any]) -> str:
        body = (
            base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
        )
        sig = hmac.new(self._secret, body.encode(), hashlib.sha256).hexdigest()
        return f"{body}.{sig}"

    def verify_token(self, token: str, method: str) -> dict[str, Any]:
        try:
            body, sig = token.rsplit(".", 1)
        except ValueError as exc:
            raise InvalidStorageToken("malformed") from exc
        expected = hmac.new(self._secret, body.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            raise InvalidStorageToken("bad signature")
        payload: dict[str, Any] = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        if payload.get("m") != method or payload.get("exp", 0) < time.time():
            raise InvalidStorageToken("expired or wrong method")
        return payload

    def presign_put(
        self, key: str, content_type: str, size_bytes: int, expires: int = 900
    ) -> tuple[str, dict[str, str]]:
        token = self._sign(
            {"k": key, "m": "PUT", "ct": content_type, "max": size_bytes, "exp": int(time.time()) + expires}
        )
        return f"{self._base_url}/api/v1/local-storage/{token}", {"Content-Type": content_type}

    def presign_get(self, key: str, expires: int = 3600, filename: str | None = None) -> str:
        token = self._sign({"k": key, "m": "GET", "exp": int(time.time()) + expires, "fn": filename})
        return f"{self._base_url}/api/v1/local-storage/{token}"
