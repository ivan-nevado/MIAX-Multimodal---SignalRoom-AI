"""Authentication & authorization: JWT validation and strict per-user isolation."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.api.security import AuthError, CognitoVerifier
from app.container import Container
from app.workers.sqs_worker import Worker
from tests.conftest import signup

POOL = "eu-west-1_TESTPOOL"
CLIENT = "spa-client-id"
ISSUER = f"https://cognito-idp.eu-west-1.amazonaws.com/{POOL}"


class StaticJWKS:
    def __init__(self, key: Any) -> None:
        self.key = key

    def get_signing_key_from_jwt(self, token: str) -> Any:
        return type("K", (), {"key": self.key})()


@pytest.fixture(scope="module")
def rsa_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def cognito_token(key: rsa.RSAPrivateKey, **overrides: Any) -> str:
    now = int(time.time())
    claims = {
        "sub": "cog-user-1",
        "email": "c@example.com",
        "iss": ISSUER,
        "aud": CLIENT,
        "token_use": "id",
        "iat": now,
        "exp": now + 600,
    }
    claims.update(overrides)
    return jwt.encode(claims, key, algorithm="RS256")


def test_cognito_verifier_accepts_valid_tokens(rsa_key: rsa.RSAPrivateKey) -> None:
    verifier = CognitoVerifier("eu-west-1", POOL, CLIENT, jwks_client=StaticJWKS(rsa_key.public_key()))
    user = verifier.verify(cognito_token(rsa_key))
    assert user.user_id == "cog-user-1" and user.email == "c@example.com"
    access = cognito_token(rsa_key, token_use="access", aud=None, client_id=CLIENT)
    assert verifier.verify(access).user_id == "cog-user-1"


@pytest.mark.parametrize(
    "overrides",
    [
        {"aud": "another-client"},
        {"iss": "https://evil.example.com"},
        {"exp": int(time.time()) - 10},
        {"token_use": "refresh"},
        {"token_use": "access", "client_id": "other"},
    ],
)
def test_cognito_verifier_rejects_bad_tokens(rsa_key: rsa.RSAPrivateKey, overrides: dict[str, Any]) -> None:
    verifier = CognitoVerifier("eu-west-1", POOL, CLIENT, jwks_client=StaticJWKS(rsa_key.public_key()))
    with pytest.raises(AuthError):
        verifier.verify(cognito_token(rsa_key, **overrides))


def test_cognito_verifier_rejects_wrong_signature(rsa_key: rsa.RSAPrivateKey) -> None:
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    verifier = CognitoVerifier("eu-west-1", POOL, CLIENT, jwks_client=StaticJWKS(rsa_key.public_key()))
    with pytest.raises(AuthError):
        verifier.verify(cognito_token(other))


def test_protected_routes_require_token(client: TestClient) -> None:
    for path in ("/api/v1/me", "/api/v1/watchlist", "/api/v1/investigations", "/api/v1/briefings"):
        assert client.get(path).status_code == 401
    resp = client.get("/api/v1/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert resp.status_code == 401 and resp.json()["message"] == "Invalid or expired session"


def test_local_signup_login_and_me(client: TestClient) -> None:
    headers = signup(client, "bob@example.com")
    assert (
        client.post(
            "/api/v1/auth/local/signup", json={"email": "bob@example.com", "password": "Sup3rSecret!"}
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/v1/auth/local/login", json={"email": "bob@example.com", "password": "wrong-pass"}
        ).status_code
        == 401
    )
    login = client.post(
        "/api/v1/auth/local/login", json={"email": "BOB@example.com", "password": "Sup3rSecret!"}
    )
    assert login.status_code == 200
    me = client.get("/api/v1/me", headers=headers).json()
    assert me["email"] == "bob@example.com" and me["auth_mode"] == "local"
    assert client.get("/api/v1/auth/config").json()["mode"] == "local"


def test_user_id_comes_from_token_not_body(
    client: TestClient, auth: dict[str, str], container: Container
) -> None:
    resp = client.post(
        "/api/v1/investigations",
        json={"asset": "NVDA", "question": "Why?", "user_id": "someone-else"},
        headers=auth,
    )
    assert resp.status_code == 202
    record = container.repos.investigations.get(resp.json()["investigation_id"])
    me = client.get("/api/v1/me", headers=auth).json()
    assert record is not None and record.user_id == me["user_id"]


def test_users_cannot_access_each_others_data(client: TestClient, container: Container) -> None:
    alice = signup(client, "alice@example.com")
    mallory = signup(client, "mallory@example.com")
    inv = client.post(
        "/api/v1/investigations", json={"asset": "NVDA", "question": "Why did NVIDIA fall?"}, headers=alice
    ).json()["investigation_id"]
    asyncio.run(Worker(container, wait_seconds=0).process_one("investigations"))

    for method, path in (
        ("get", f"/api/v1/investigations/{inv}"),
        ("get", f"/api/v1/investigations/{inv}/events?format=json"),
        ("delete", f"/api/v1/investigations/{inv}"),
        ("post", f"/api/v1/investigations/{inv}/audio"),
        ("get", f"/api/v1/investigations/{inv}/transcripts/up_x"),
    ):
        assert getattr(client, method)(path, headers=mallory).status_code == 404, path
    assert client.get(f"/api/v1/investigations/{inv}", headers=alice).status_code == 200
    assert client.get("/api/v1/investigations", headers=mallory).json() == []

    up = client.post(
        "/api/v1/uploads/presign",
        json={"filename": "a.pdf", "content_type": "application/pdf", "size_bytes": 100, "kind": "document"},
        headers=alice,
    ).json()
    assert (
        client.post(
            "/api/v1/uploads/complete", json={"upload_id": up["upload_id"]}, headers=mallory
        ).status_code
        == 403
    )
    assert client.delete(f"/api/v1/uploads/{up['upload_id']}", headers=mallory).status_code == 403
    bad = client.post(
        "/api/v1/investigations",
        json={"asset": "NVDA", "question": "Use her file", "upload_ids": [up["upload_id"]]},
        headers=mallory,
    )
    assert bad.status_code == 403

    client.delete("/api/v1/watchlist/NVDA", headers=mallory)
    assert any(i["symbol"] == "NVDA" for i in client.get("/api/v1/watchlist", headers=alice).json())
    client.patch("/api/v1/preferences/briefing", json={"enabled": True}, headers=mallory)
    assert client.get("/api/v1/preferences/briefing", headers=alice).json()["enabled"] is False


def test_local_storage_token_cannot_be_forged(client: TestClient, auth: dict[str, str]) -> None:
    up = client.post(
        "/api/v1/uploads/presign",
        json={"filename": "a.png", "content_type": "image/png", "size_bytes": 50, "kind": "image"},
        headers=auth,
    ).json()
    token = up["upload_url"].rsplit("/", 1)[1]
    body, sig = token.rsplit(".", 1)
    forged = f"{body}.{'0' * len(sig)}"
    assert (
        client.put(
            f"/api/v1/local-storage/{forged}", content=b"x", headers={"Content-Type": "image/png"}
        ).status_code
        == 403
    )
    assert client.get(f"/api/v1/local-storage/{token}").status_code == 403  # PUT token cannot be used to read
