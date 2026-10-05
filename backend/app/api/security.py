"""JWT validation. The user id ALWAYS comes from a verified token, never from the request body.

* Cognito (AWS): RS256 tokens verified against the user pool JWKS
  (https://cognito-idp.<region>.amazonaws.com/<pool>/.well-known/jwks.json), issuer,
  expiry, token_use and audience/client_id are all checked.
* Local (development only): HS256 tokens issued by LocalAuthService.
"""

from __future__ import annotations

import logging
from typing import Any

import jwt
from jwt import PyJWKClient

from app.config.settings import Settings
from app.schemas.users import AuthenticatedUser
from app.services.local_auth import LocalAuthService

logger = logging.getLogger(__name__)


class AuthError(Exception):
    pass


class CognitoVerifier:
    def __init__(
        self, region: str, user_pool_id: str, client_id: str, jwks_client: Any | None = None
    ) -> None:
        self.issuer = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}"
        self.client_id = client_id
        self._jwks = jwks_client or PyJWKClient(
            f"{self.issuer}/.well-known/jwks.json", cache_keys=True, lifespan=3600
        )

    def verify(self, token: str) -> AuthenticatedUser:
        try:
            signing_key = self._jwks.get_signing_key_from_jwt(token)
            claims: dict[str, Any] = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                issuer=self.issuer,
                options={"verify_aud": False, "require": ["exp", "iat", "sub", "token_use"]},
            )
        except jwt.PyJWTError as exc:
            raise AuthError(type(exc).__name__) from exc
        token_use = claims.get("token_use")
        if token_use == "id":
            if claims.get("aud") != self.client_id:
                raise AuthError("audience mismatch")
        elif token_use == "access":
            if claims.get("client_id") != self.client_id:
                raise AuthError("client mismatch")
        else:
            raise AuthError("unexpected token_use")
        return AuthenticatedUser(user_id=str(claims["sub"]), email=claims.get("email"))


class TokenVerifier:
    def __init__(
        self, settings: Settings, local_auth: LocalAuthService | None, cognito: CognitoVerifier | None = None
    ) -> None:
        self._mode = settings.auth_mode
        self._local = local_auth
        self._cognito = cognito
        if self._mode == "cognito" and self._cognito is None:
            self._cognito = CognitoVerifier(
                settings.effective_cognito_region,
                settings.cognito_user_pool_id or "",
                settings.cognito_app_client_id or "",
            )

    def verify(self, token: str) -> AuthenticatedUser:
        if self._mode == "cognito":
            assert self._cognito is not None
            return self._cognito.verify(token)
        if self._local is None:
            raise AuthError("local auth not configured")
        try:
            claims = self._local.verify(token)
        except jwt.PyJWTError as exc:
            raise AuthError(type(exc).__name__) from exc
        return AuthenticatedUser(user_id=claims["user_id"], email=claims["email"] or None)
