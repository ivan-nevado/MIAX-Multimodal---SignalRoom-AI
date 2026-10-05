from __future__ import annotations

import httpx
import pandas as pd
import pytest
import respx

from app.integrations.financial import sec as sec_mod
from app.integrations.financial.sec import SecFinancialDataProvider
from app.integrations.macro.fred import FredMacroProvider, _transform
from app.integrations.macro.market_context import MarketContextProvider
from app.integrations.market.alpha_vantage import AlphaVantageMarketDataProvider
from app.integrations.market.base import MarketDataError
from app.integrations.market.fallback import FallbackMarketDataProvider
from app.integrations.market.yahoo import frame_to_points, infer_asset_type
from app.integrations.news import gdelt as gdelt_mod
from app.integrations.news.alpha_vantage import AlphaVantageNewsProvider
from app.integrations.news.base import NewsQuery
from app.integrations.news.composite import CompositeNewsProvider
from app.integrations.news.gdelt import GdeltNewsProvider, build_gdelt_query, parse_seendate
from app.repositories.local import MemoryCacheRepository
from tests.fakes import FakeMarket, FakeNewsProvider


def test_yahoo_frame_to_points_and_types() -> None:
    idx = pd.to_datetime(["2026-10-01", "2026-10-02"])
    frame = pd.DataFrame(
        {
            "Open": [1.0, 2.0],
            "High": [2.0, 3.0],
            "Low": [0.5, 1.5],
            "Close": [1.5, float("nan")],
            "Volume": [10, 20],
        },
        index=idx,
    )
    pts = frame_to_points(frame, intraday=False)
    assert len(pts) == 1 and pts[0].time == "2026-10-01"
    assert infer_asset_type("^GSPC") == "index" and infer_asset_type("EURUSD=X") == "fx"
    assert infer_asset_type("BTC-USD") == "crypto" and infer_asset_type("GC=F") == "commodity"


async def test_fallback_market_provider() -> None:
    failing, ok = FakeMarket(fail={"*"}), FakeMarket()
    chain = FallbackMarketDataProvider([failing, ok])
    assert len(await chain.get_history("NVDA")) > 100
    with pytest.raises(MarketDataError):
        await FallbackMarketDataProvider([failing]).get_quote("NVDA")


@respx.mock
async def test_alpha_vantage_market_and_news() -> None:
    respx.get("https://www.alphavantage.co/query", params={"function": "TIME_SERIES_DAILY"}).mock(
        return_value=httpx.Response(
            200,
            json={
                "Time Series (Daily)": {
                    "2026-10-02": {
                        "1. open": "1",
                        "2. high": "2",
                        "3. low": "0.5",
                        "4. close": "1.5",
                        "5. volume": "100",
                    }
                }
            },
        )
    )
    respx.get("https://www.alphavantage.co/query", params={"function": "NEWS_SENTIMENT"}).mock(
        return_value=httpx.Response(
            200,
            json={
                "feed": [
                    {
                        "title": "NVDA rises",
                        "url": "https://x.com/a",
                        "source": "X",
                        "time_published": "20261002T120000",
                        "ticker_sentiment": [{"ticker": "NVDA", "ticker_sentiment_score": "0.4"}],
                    }
                ]
            },
        )
    )
    hist = await AlphaVantageMarketDataProvider("k").get_history("NVDA", "6mo")
    assert hist[0].close == 1.5
    with pytest.raises(MarketDataError):
        await AlphaVantageMarketDataProvider("k").get_history("NVDA", "1d")
    news = await AlphaVantageNewsProvider("k").search(NewsQuery(terms=["NVIDIA"], symbol="NVDA"))
    assert news[0].tone == 0.4 and news[0].published_at.startswith("2026-10-02")


def test_gdelt_query_and_dates() -> None:
    assert build_gdelt_query(NewsQuery(terms=["NVIDIA", "NVDA"])) == "(NVIDIA OR NVDA) sourcelang:english"
    assert build_gdelt_query(NewsQuery(terms=["Banco Santander"])) == '"Banco Santander" sourcelang:english'
    assert parse_seendate("20261002T090000Z") == "2026-10-02T09:00:00+00:00"


@respx.mock
async def test_gdelt_articles_and_circuit_breaker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gdelt_mod, "_cooldown_until", 0.0)
    monkeypatch.setattr(gdelt_mod, "_last_request", 0.0)
    route = respx.get(gdelt_mod.BASE_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "articles": [
                    {
                        "url": "https://reuters.com/a",
                        "title": "NVIDIA export rules",
                        "domain": "reuters.com",
                        "seendate": "20261002T090000Z",
                    }
                ]
            },
        )
    )
    provider = GdeltNewsProvider(MemoryCacheRepository(), min_interval=0.0)
    arts = await provider.search(NewsQuery(terms=["NVIDIA"], symbol="NVDA"))
    assert arts[0].publisher == "reuters.com" and arts[0].provider == "gdelt"
    await provider.search(NewsQuery(terms=["NVIDIA"], symbol="NVDA"))
    assert route.call_count == 1  # cached

    route.mock(return_value=httpx.Response(429, text="Please limit requests"))
    with pytest.raises(gdelt_mod.NewsProviderError):
        await provider.search(NewsQuery(terms=["Tesla"], symbol="TSLA"))
    calls = route.call_count
    with pytest.raises(gdelt_mod.NewsProviderError, match="skipped"):
        await provider.search(NewsQuery(terms=["Apple"], symbol="AAPL"))
    assert route.call_count == calls  # circuit open: no further requests
    monkeypatch.setattr(gdelt_mod, "_cooldown_until", 0.0)


async def test_composite_news_survives_provider_failure() -> None:
    composite = CompositeNewsProvider([FakeNewsProvider(fail=True), FakeNewsProvider()])  # type: ignore[list-item]
    result = await composite.search_all(NewsQuery(terms=["NVIDIA"]))
    assert result.providers_failed == ["fake_news"] and len(result.articles) > 5


@respx.mock
async def test_sec_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sec_mod, "_ticker_map", {})
    respx.get(sec_mod.TICKERS_URL).mock(
        return_value=httpx.Response(
            200, json={"0": {"cik_str": 1045810, "ticker": "NVDA", "title": "NVIDIA CORP"}}
        )
    )
    respx.get("https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json").mock(
        return_value=httpx.Response(
            200,
            json={
                "entityName": "NVIDIA CORP",
                "facts": {
                    "us-gaap": {
                        "Revenues": {
                            "units": {
                                "USD": [
                                    {
                                        "start": "2026-04-28",
                                        "end": "2026-07-27",
                                        "val": 46.7e9,
                                        "filed": "2026-08-27",
                                    },
                                    {
                                        "start": "2025-04-28",
                                        "end": "2025-07-27",
                                        "val": 30.0e9,
                                        "filed": "2025-08-27",
                                    },
                                ]
                            }
                        }
                    }
                },
            },
        )
    )
    respx.get("https://data.sec.gov/submissions/CIK0001045810.json").mock(
        return_value=httpx.Response(
            200,
            json={
                "filings": {
                    "recent": {
                        "form": ["4", "10-Q"],
                        "filingDate": ["2026-09-01", "2026-08-27"],
                        "accessionNumber": ["0001-1", "0001-26-000123"],
                        "primaryDocument": ["a.xml", "nvda-q2.htm"],
                        "primaryDocDescription": ["", "10-Q"],
                    }
                }
            },
        )
    )
    provider = SecFinancialDataProvider("SignalRoom test test@example.com", MemoryCacheRepository())
    snap = await provider.snapshot("NVDA")
    assert snap.cik == "0001045810" and snap.revenue == 46.7e9
    assert snap.revenue_growth_yoy == pytest.approx(0.5567, abs=1e-3)
    assert [f.form for f in snap.recent_filings] == ["10-Q"]  # Form 4 filtered out
    assert snap.recent_filings[0].url and snap.recent_filings[0].url.endswith("nvda-q2.htm")
    crypto = await provider.snapshot("BTC-USD")
    assert crypto.applicable is False
    unknown = await provider.snapshot("ZZZZ")
    assert unknown.applicable is False and "not an SEC registrant" in (unknown.note or "")


def test_sec_requires_user_agent() -> None:
    with pytest.raises(ValueError):
        SecFinancialDataProvider("")


@respx.mock
async def test_fred_indicators() -> None:
    obs = [{"date": f"2025-{m:02d}-01", "value": str(300 + m)} for m in range(1, 13)] + [
        {"date": "2026-01-01", "value": "330"}
    ]
    respx.get("https://api.stlouisfed.org/fred/series/observations").mock(
        return_value=httpx.Response(200, json={"observations": obs})
    )
    indicators = await FredMacroProvider("k").indicators()
    cpi = next(i for i in indicators if i.id == "CPIAUCSL")
    assert cpi.value == pytest.approx((330 / 301 - 1) * 100, abs=0.01)
    assert _transform([{"date": "2026-01-01", "value": "."}], "level") == []


async def test_market_context_provider() -> None:
    indicators = await MarketContextProvider(FakeMarket()).indicators()
    assert {i.id for i in indicators} >= {"^GSPC", "^VIX"}
    assert all(i.source_id for i in indicators)
