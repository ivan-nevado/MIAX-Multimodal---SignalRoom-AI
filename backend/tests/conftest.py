from __future__ import annotations

import os

# Must run before any app import: tests never use real keys or AWS.
os.environ.update(
    {
        "APP_ENV": "test",
        "BACKEND_MODE": "local",
        "AUTH_MODE": "local",
        "OPENROUTER_API_KEY": "",
        "OPEN_ROUTER_API_KEY": "",
        "OPENAI_API_KEY": "",
        "GEMINI_API_KEY": "",
        "ALPHAVANTAGE_API_KEY": "",
        "FRED_API_KEY": "",
        "GDELT_ENABLED": "false",
        "SECRETS_MANAGER_SECRET_ID": "",
        "LOG_LEVEL": "WARNING",
        "AWS_ACCESS_KEY_ID": "testing",
        "AWS_SECRET_ACCESS_KEY": "testing",
        "AWS_DEFAULT_REGION": "eu-west-1",
    }
)

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config.settings import Settings, get_settings
from app.container import Container, set_container
from app.integrations.macro.market_context import MarketContextProvider
from app.integrations.news.composite import CompositeNewsProvider
from tests.fakes import FakeFinancial, FakeGateway, FakeMarket, FakeNewsProvider

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_DATA = REPO_ROOT / "demo_data"


def make_settings(tmp_path: Path, **overrides: object) -> Settings:
    get_settings.cache_clear()
    return Settings(_env_file=None, local_data_dir=tmp_path, **overrides)  # type: ignore[call-arg]


def make_container(
    tmp_path: Path,
    *,
    ai: FakeGateway | None = None,
    market: FakeMarket | None = None,
    news_fail: bool = False,
    financial_fail: bool = False,
) -> Container:
    c = Container(make_settings(tmp_path))
    fake_market = market or FakeMarket()
    news_provider = FakeNewsProvider(fail=news_fail)
    c.__dict__.update(
        ai=ai or FakeGateway(),
        market=fake_market,
        news=CompositeNewsProvider([news_provider], news_provider),  # type: ignore[list-item]
        financial=FakeFinancial(fail=financial_fail),
        macro_providers=[MarketContextProvider(fake_market)],
    )
    return c


@pytest.fixture
def container(tmp_path: Path) -> Iterator[Container]:
    c = make_container(tmp_path)
    set_container(c)
    yield c
    set_container(None)


@pytest.fixture
def client(container: Container) -> Iterator[TestClient]:
    from app.main import create_app

    with TestClient(create_app()) as tc:
        yield tc


def signup(
    client: TestClient, email: str = "ana@example.com", password: str = "Sup3rSecret!"
) -> dict[str, str]:
    resp = client.post("/api/v1/auth/local/signup", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def auth(client: TestClient) -> dict[str, str]:
    return signup(client)
