"""Optional Alpha Vantage NEWS_SENTIMENT adapter (free tier; requires ALPHAVANTAGE_API_KEY)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx

from app.integrations.cache import TTL_NEWS, cache_key, cached
from app.integrations.news.base import NewsProviderError, NewsQuery
from app.repositories.base import CacheRepository
from app.schemas.agents import NewsArticle
from app.utils.ids import stable_id
from app.utils.time import utc_now_iso

BASE_URL = "https://www.alphavantage.co/query"


class AlphaVantageNewsProvider:
    name = "alpha_vantage_news"

    def __init__(
        self,
        api_key: str,
        cache: CacheRepository | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._key = api_key
        self._cache = cache
        self._transport = transport

    async def search(self, query: NewsQuery) -> list[NewsArticle]:
        if not query.symbol or query.symbol.startswith("^") or "=" in query.symbol:
            raise NewsProviderError("Alpha Vantage news needs an equity/crypto ticker")
        ticker = query.symbol.replace("-USD", "")
        if query.symbol.endswith("-USD"):
            ticker = f"CRYPTO:{ticker}"

        async def load() -> dict[str, Any]:
            async with httpx.AsyncClient(timeout=20, transport=self._transport) as client:
                resp = await client.get(
                    BASE_URL,
                    params={
                        "function": "NEWS_SENTIMENT",
                        "tickers": ticker,
                        "limit": "50",
                        "apikey": self._key,
                    },
                )
            if resp.status_code != 200:
                raise NewsProviderError(f"Alpha Vantage HTTP {resp.status_code}")
            data: dict[str, Any] = resp.json()
            if "feed" not in data:
                raise NewsProviderError("Alpha Vantage limit reached or unsupported ticker")
            return data

        data = await cached(self._cache, cache_key(self.name, "news", ticker), TTL_NEWS, load)
        retrieved = utc_now_iso()
        out: list[NewsArticle] = []
        for item in data.get("feed", []):
            url, title = item.get("url"), (item.get("title") or "").strip()
            if not url or not title:
                continue
            tone = None
            for ts in item.get("ticker_sentiment", []):
                if ts.get("ticker") == ticker:
                    try:
                        tone = float(ts.get("ticker_sentiment_score"))
                    except (TypeError, ValueError):
                        tone = None
            published = None
            if item.get("time_published"):
                try:
                    published = (
                        datetime.strptime(item["time_published"], "%Y%m%dT%H%M%S")
                        .replace(tzinfo=UTC)
                        .isoformat()
                    )
                except ValueError:
                    published = None
            out.append(
                NewsArticle(
                    id=stable_id("av", url),
                    title=title,
                    url=url,
                    publisher=item.get("source") or "unknown",
                    published_at=published,
                    retrieved_at=retrieved,
                    provider=self.name,
                    tone=tone,
                    query=ticker,
                )
            )
        return out
