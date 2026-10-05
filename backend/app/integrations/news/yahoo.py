"""Yahoo Finance news headlines via yfinance's search endpoint (keyless, metadata only)."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from functools import partial
from typing import Any
from urllib.parse import urlparse

import yfinance as yf

from app.integrations.cache import TTL_NEWS, cache_key, cached
from app.integrations.news.base import NewsProviderError, NewsQuery
from app.repositories.base import CacheRepository
from app.schemas.agents import NewsArticle
from app.utils.ids import stable_id
from app.utils.time import utc_now_iso

logger = logging.getLogger(__name__)


class YahooNewsProvider:
    name = "yahoo_finance_news"

    def __init__(self, cache: CacheRepository | None = None) -> None:
        self._cache = cache

    async def search(self, query: NewsQuery) -> list[NewsArticle]:
        lookups = [t for t in [query.symbol, *query.terms[:1]] if t]
        if not lookups:
            raise NewsProviderError("No terms for Yahoo news")

        async def load(term: str) -> list[dict[str, Any]]:
            def _fetch() -> list[dict[str, Any]]:
                result = yf.Search(term, max_results=1, news_count=20)
                return list(result.news or [])

            try:
                return await asyncio.to_thread(_fetch)
            except Exception as exc:
                raise NewsProviderError(f"Yahoo news unavailable: {type(exc).__name__}") from exc

        items: list[dict[str, Any]] = []
        for term in dict.fromkeys(lookups):
            loader = partial(load, term)
            items.extend(
                await cached(self._cache, cache_key(self.name, "news", term, term), TTL_NEWS, loader)
            )
        cutoff = datetime.now(UTC).timestamp() - query.days * 86400
        retrieved = utc_now_iso()
        out: list[NewsArticle] = []
        for item in items:
            url, title = item.get("link"), (item.get("title") or "").strip()
            ts = item.get("providerPublishTime")
            if not url or not title or (ts and ts < cutoff):
                continue
            published = datetime.fromtimestamp(ts, tz=UTC).isoformat() if ts else None
            out.append(
                NewsArticle(
                    id=stable_id("yh", url),
                    title=title,
                    url=url,
                    publisher=item.get("publisher") or urlparse(url).netloc,
                    published_at=published,
                    retrieved_at=retrieved,
                    provider=self.name,
                    query=", ".join(lookups),
                )
            )
        return out
