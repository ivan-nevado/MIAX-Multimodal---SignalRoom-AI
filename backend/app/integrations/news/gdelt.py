"""GDELT DOC 2.0 API — keyless global news discovery, volume and tone timelines.

GDELT asks for at most one request every 5 seconds, so every request goes
through a process-wide rate limiter, results are cached, and 429 responses are
retried with exponential backoff. We store only metadata (title, URL, domain,
seen time, query) and always link to the original publisher.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from datetime import UTC, datetime
from typing import Any

import httpx

from app.integrations.cache import TTL_NEWS, cache_key, cached
from app.integrations.news.base import NewsProviderError, NewsQuery, NewsTimelines
from app.repositories.base import CacheRepository
from app.schemas.agents import NewsArticle, SeriesPoint
from app.utils.ids import stable_id
from app.utils.time import utc_now_iso

logger = logging.getLogger(__name__)

BASE_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
_rate_lock = threading.Lock()
_last_request = 0.0
# Circuit breaker: after GDELT keeps rate-limiting us, skip it for a while instead of
# slowing every investigation down (Yahoo/Alpha Vantage news still answer).
_cooldown_until = 0.0
COOLDOWN_SECONDS = 120.0


def build_gdelt_query(query: NewsQuery) -> str:
    terms: list[str] = []
    for term in query.terms:
        term = term.strip().replace('"', "")
        if len(term) >= 3 and term.lower() not in {t.lower().strip('"') for t in terms}:
            terms.append(f'"{term}"' if " " in term or not term.isalnum() else term)
    if not terms:
        raise NewsProviderError("No usable search terms for GDELT")
    core = terms[0] if len(terms) == 1 else "(" + " OR ".join(terms[:4]) + ")"
    return f"{core} sourcelang:english"


def parse_seendate(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC).isoformat()
    except ValueError:
        return None


class GdeltNewsProvider:
    name = "gdelt"

    def __init__(
        self,
        cache: CacheRepository | None = None,
        *,
        min_interval: float = 5.5,
        max_retries: int = 1,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._cache = cache
        self._min_interval = min_interval
        self._max_retries = max_retries
        self._transport = transport

    async def _wait_turn(self) -> None:
        global _last_request
        with _rate_lock:
            now = time.monotonic()
            wait = max(0.0, _last_request + self._min_interval - now)
            _last_request = now + wait
        if wait:
            await asyncio.sleep(wait)

    async def _request(self, params: dict[str, Any]) -> dict[str, Any]:
        global _cooldown_until
        if time.monotonic() < _cooldown_until:
            raise NewsProviderError("GDELT temporarily skipped after repeated rate limiting")
        for attempt in range(self._max_retries + 1):
            await self._wait_turn()
            try:
                async with httpx.AsyncClient(timeout=15, transport=self._transport) as client:
                    resp = await client.get(BASE_URL, params={**params, "format": "json"})
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                # A slow/unreachable GDELT should not slow every investigation down.
                _cooldown_until = time.monotonic() + COOLDOWN_SECONDS
                raise NewsProviderError(f"GDELT unreachable: {type(exc).__name__}") from exc
            if resp.status_code == 429:
                if attempt < self._max_retries:
                    await asyncio.sleep(self._min_interval)
                    continue
                _cooldown_until = time.monotonic() + COOLDOWN_SECONDS
                raise NewsProviderError("GDELT rate limited")
            if resp.status_code != 200:
                raise NewsProviderError(f"GDELT HTTP {resp.status_code}")
            text = resp.text.strip()
            if not text or not text.startswith("{"):
                # GDELT returns plain-text errors (e.g. query too short/complex)
                raise NewsProviderError("GDELT returned a non-JSON response")
            try:
                data: dict[str, Any] = resp.json()
            except ValueError as exc:
                raise NewsProviderError("GDELT returned invalid JSON") from exc
            return data
        raise NewsProviderError("GDELT rate limited")

    async def search(self, query: NewsQuery) -> list[NewsArticle]:
        q = build_gdelt_query(query)
        timespan = f"{query.days}d"

        async def load() -> list[dict[str, Any]]:
            data = await self._request(
                {
                    "query": q,
                    "mode": "artlist",
                    "maxrecords": min(query.max_records, 250),
                    "timespan": timespan,
                    "sort": "hybridrel",
                }
            )
            articles: list[dict[str, Any]] = data.get("articles") or []
            return articles

        raw = await cached(
            self._cache, cache_key(self.name, "artlist", query.symbol or "-", q, timespan), TTL_NEWS, load
        )
        retrieved = utc_now_iso()
        out: list[NewsArticle] = []
        for item in raw:
            url, title = item.get("url"), (item.get("title") or "").strip()
            if not url or not title:
                continue
            out.append(
                NewsArticle(
                    id=stable_id("gd", url),
                    title=title,
                    url=url,
                    publisher=item.get("domain") or "unknown",
                    published_at=parse_seendate(item.get("seendate")),
                    retrieved_at=retrieved,
                    provider=self.name,
                    query=q,
                )
            )
        return out

    async def timelines(self, query: NewsQuery) -> NewsTimelines:
        q = build_gdelt_query(query)
        timespan = f"{query.days}d"

        async def load_mode(mode: str) -> list[dict[str, Any]]:
            data = await self._request({"query": q, "mode": mode, "timespan": timespan})
            timeline = data.get("timeline") or []
            series: list[dict[str, Any]] = timeline[0].get("data", []) if timeline else []
            return series

        result = NewsTimelines()
        for mode, target in (("timelinetone", "tone"), ("timelinevolraw", "volume")):
            try:
                series = await cached(
                    self._cache,
                    cache_key(self.name, mode, query.symbol or "-", q, timespan),
                    TTL_NEWS,
                    lambda mode=mode: load_mode(mode),  # type: ignore[misc]
                )
            except NewsProviderError as exc:
                logger.info("gdelt_timeline_unavailable", extra={"mode": mode, "error": str(exc)})
                continue
            points = [
                SeriesPoint(
                    date=parse_seendate(p.get("date")) or p.get("date", ""), value=float(p.get("value", 0))
                )
                for p in series
                if p.get("value") is not None
            ]
            setattr(result, target, points)
        return result
