from __future__ import annotations

import hashlib
import secrets


def new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(8)}"


def stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def user_ref(user_id: str) -> str:
    """Short non-reversible reference to a user for logs (never log raw IDs/emails)."""
    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:12]
