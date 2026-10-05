"""Invite-only access and daily usage limits (budget protection for the public demo)."""

from __future__ import annotations

import time

import jwt
from fastapi.testclient import TestClient

from app.container import Container
from app.services.access import is_email_allowed, parse_allowlist
from tests.conftest import signup


def test_allowlist_parsing_and_matching() -> None:
    raw = " Ana@Gmail.com, @miax.es ;luis@x.io "
    assert parse_allowlist(raw) == ["ana@gmail.com", "@miax.es", "luis@x.io"]
    assert is_email_allowed("ana@gmail.com", raw)
    assert is_email_allowed("someone@miax.es", raw)
    assert not is_email_allowed("someone@evil-miax.es.com", raw)
    assert not is_email_allowed("eve@gmail.com", raw)
    assert not is_email_allowed(None, raw)
    assert is_email_allowed("anyone@anything.com", "")  # empty list = open sign-up


def test_signup_rejected_when_not_invited(client: TestClient, container: Container) -> None:
    container.settings.allowed_emails = "ana@example.com,@team.io"
    assert client.get("/api/v1/auth/config").json()["invite_only"] is True
    resp = client.post(
        "/api/v1/auth/local/signup", json={"email": "eve@example.com", "password": "Sup3rSecret!"}
    )
    assert resp.status_code == 403 and resp.json()["error"] == "not_invited"
    assert signup(client, "bob@team.io")  # domain entry allowed
    assert signup(client, "ana@example.com")


def test_api_rejects_tokens_of_users_removed_from_the_list(client: TestClient, container: Container) -> None:
    headers = signup(client, "carol@example.com")
    assert client.get("/api/v1/me", headers=headers).status_code == 200
    container.settings.allowed_emails = "ana@example.com"  # Carol removed from the invite list
    resp = client.get("/api/v1/watchlist", headers=headers)
    assert resp.status_code == 403 and resp.json()["error"] == "not_invited"


def test_access_token_without_email_uses_stored_profile(client: TestClient, container: Container) -> None:
    first = signup(client, "dave@example.com")
    client.get("/api/v1/me", headers=first)  # first request (ID token with email) stores the profile
    user_id = container.repos.credentials.get("dave@example.com")["user_id"]  # type: ignore[index]
    secret = container.settings.local_jwt_secret.get_secret_value()
    now = int(time.time())
    token = jwt.encode(
        {"sub": user_id, "iss": "signalroom-local", "iat": now, "exp": now + 60}, secret, algorithm="HS256"
    )
    container.settings.allowed_emails = "dave@example.com"
    assert client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200


def test_daily_limits(client: TestClient, auth: dict[str, str], container: Container) -> None:
    container.settings.max_investigations_per_day = 2
    for _ in range(2):
        assert (
            client.post(
                "/api/v1/investigations", json={"asset": "NVDA", "question": "Why did it move?"}, headers=auth
            ).status_code
            == 202
        )
    resp = client.post(
        "/api/v1/investigations", json={"asset": "NVDA", "question": "Why did it move?"}, headers=auth
    )
    assert resp.status_code == 429 and "Daily limit of 2" in resp.json()["message"]

    container.settings.max_briefings_per_day = 1
    assert client.post("/api/v1/briefings/generate", json={}, headers=auth).status_code == 202
    container.repos.briefings.put(
        container.repos.briefings.list_by_user(client.get("/api/v1/me", headers=auth).json()["user_id"])[
            0
        ].model_copy(update={"status": "completed"})
    )
    resp = client.post("/api/v1/briefings/generate", json={}, headers=auth)
    assert resp.status_code == 429


def test_cognito_pre_signup_lambda(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import importlib.util

    import pytest

    from tests.conftest import REPO_ROOT

    spec = importlib.util.spec_from_file_location(
        "pre_signup", REPO_ROOT / "terraform/modules/cognito/lambda/pre_signup.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    event = lambda email: {"request": {"userAttributes": {"email": email}}}  # noqa: E731
    monkeypatch.setenv("ALLOWED_EMAILS", "ana@gmail.com,@miax.es")
    assert module.handler(event("ANA@gmail.com"), None)["request"]
    assert module.handler(event("prof@miax.es"), None)
    with pytest.raises(Exception, match="invite-only"):
        module.handler(event("eve@gmail.com"), None)
    monkeypatch.setenv("ALLOWED_EMAILS", "")
    assert module.handler(event("anyone@x.com"), None)
