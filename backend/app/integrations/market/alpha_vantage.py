"""Optional Alpha Vantage market data adapter (free tier endpoints only).

Free tier limits are small (≈25 requests/day), so this provider is used as a
fallback behind Yahoo Finance and everything is cached. If no key is set the
provider is simply not registered.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.integrations.cache import TTL_HISTORY, TTL_QUOTE, TTL_SEARCH, cache_key, cached
from app.integrations.market.base import HistoryRange, MarketDataError, Quote
from app.integrations.market.yahoo import infer_asset_type
from app.repositories.base import CacheRepository
from app.schemas.agents import PricePoint
from app.schemas.assets import AssetMatch
from app.utils.time import utc_now_iso

BASE_URL = "https://www.alphavantage.co/query"


class AlphaVantageMarketDataProvider:
    name = "alpha_vantage"

    def __init__(
        self,
        api_key: str,
        cache: CacheRepository | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._key = api_key
        self._cache = cache
        self._transport = transport

    async def _get(self, params: dict[str, str]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=20, transport=self._transport) as client:
            resp = await client.get(BASE_URL, params={**params, "apikey": self._key})
        if resp.status_code != 200:
            raise MarketDataError(f"Alpha Vantage HTTP {resp.status_code}")
        data: dict[str, Any] = resp.json()
        if "Note" in data or "Information" in data or "Error Message" in data:
            raise MarketDataError("Alpha Vantage limit reached or unsupported request")
        return data

    async def get_history(self, symbol: str, range_: HistoryRange = "6mo") -> list[PricePoint]:
        if range_ in ("1d", "5d"):
            raise MarketDataError("Intraday history requires premium Alpha Vantage endpoints")

        async def load() -> list[PricePoint]:
            data = await self._get(
                {"function": "TIME_SERIES_DAILY", "symbol": symbol, "outputsize": "compact"}
            )
            series = data.get("Time Series (Daily)") or {}
            points = [
                PricePoint(
                    time=day,
                    open=float(v["1. open"]),
                    high=float(v["2. high"]),
                    low=float(v["3. low"]),
                    close=float(v["4. close"]),
                    volume=float(v.get("5. volume", 0)),
                )
                for day, v in sorted(series.items())
            ]
            if not points:
                raise MarketDataError(f"No Alpha Vantage history for {symbol}")
            return points

        return await cached(
            self._cache,
            cache_key(self.name, "history", symbol, "daily", range_),
            TTL_HISTORY,
            load,
            encode=lambda pts: [p.model_dump() for p in pts],
            decode=lambda raw: [PricePoint.model_validate(p) for p in raw],
        )

    async def get_quote(self, symbol: str) -> Quote:
        async def load() -> dict[str, Any]:
            return await self._get({"function": "GLOBAL_QUOTE", "symbol": symbol})

        data = await cached(self._cache, cache_key(self.name, "quote", symbol), TTL_QUOTE, load)
        q = data.get("Global Quote") or {}
        if not q.get("05. price"):
            raise MarketDataError(f"No Alpha Vantage quote for {symbol}")
        return Quote(
            symbol=symbol,
            asset_type=infer_asset_type(symbol),
            last_price=float(q["05. price"]),
            previous_close=float(q.get("08. previous close") or 0) or None,
            retrieved_at=utc_now_iso(),
            provider=self.name,
        )

    async def search(self, query: str, limit: int = 8) -> list[AssetMatch]:
        async def load() -> dict[str, Any]:
            return await self._get({"function": "SYMBOL_SEARCH", "keywords": query})

        data = await cached(self._cache, cache_key(self.name, "search", "-", query), TTL_SEARCH, load)
        out = []
        for m in (data.get("bestMatches") or [])[:limit]:
            out.append(
                AssetMatch(
                    symbol=m.get("1. symbol", ""),
                    name=m.get("2. name", ""),
                    asset_type="etf" if m.get("3. type") == "ETF" else "equity",
                    exchange=m.get("4. region"),
                )
            )
        return out
