"""Local development authentication (AUTH_MODE=local).

Mirrors the Cognito flow closely enough for development and the professor's
local demo: email + password, HS256 JWT. In AWS, Cognito User Pools replace this.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
import uuid

import jwt

from app.repositories.base import CredentialRepository
from app.services.access import ensure_allowed
from app.services.errors import ConflictError, ServiceError

LOCAL_ISSUER = "signalroom-local"


class InvalidCredentials(ServiceError):
    status_code = 401
    code = "invalid_credentials"


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt_b64, digest_b64 = stored.split("$")
    except ValueError:
        return False
    expected = hash_password(password, base64.b64decode(salt_b64))
    return hmac.compare_digest(expected.split("$")[2], digest_b64)


class LocalAuthService:
    def __init__(
        self, credentials: CredentialRepository, secret: str, ttl_minutes: int, allowed_emails: str = ""
    ) -> None:
        self._allowed = allowed_emails
        self._credentials = credentials
        self._secret = secret
        self._ttl = ttl_minutes * 60

    def signup(self, email: str, password: str) -> tuple[str, str, int]:
        ensure_allowed(email, self._allowed)
        if self._credentials.get(email):
            raise ConflictError("An account with this email already exists.")
        user_id = str(uuid.uuid4())
        self._credentials.put(
            email, {"user_id": user_id, "email": email, "password": hash_password(password)}
        )
        return self.issue(user_id, email)

    def login(self, email: str, password: str) -> tuple[str, str, int]:
        record = self._credentials.get(email)
        if not record or not verify_password(password, record["password"]):
            raise InvalidCredentials("Incorrect email or password.")
        return self.issue(record["user_id"], email)

    def issue(self, user_id: str, email: str) -> tuple[str, str, int]:
        now = int(time.time())
        token = jwt.encode(
            {
                "sub": user_id,
                "email": email,
                "iss": LOCAL_ISSUER,
                "token_use": "access",
                "iat": now,
                "exp": now + self._ttl,
            },
            self._secret,
            algorithm="HS256",
        )
        return token, user_id, self._ttl

    def verify(self, token: str) -> dict[str, str]:
        claims = jwt.decode(
            token,
            self._secret,
            algorithms=["HS256"],
            issuer=LOCAL_ISSUER,
            options={"require": ["exp", "sub"]},
        )
        return {"user_id": str(claims["sub"]), "email": str(claims.get("email") or "")}
