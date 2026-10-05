"""Yahoo Finance market data via the unofficial open-source `yfinance` package.

yfinance is intended for personal/research use: SignalRoom treats it as an
academic prototype data source (possibly delayed), never as a licensed feed.
All calls are cached and run in a worker thread (yfinance is synchronous).
"""

from __future__ import annotations

import asyncio
import logging
import math
from typing import Any

import pandas as pd
import yfinance as yf

from app.integrations.cache import (
    TTL_HISTORY,
    TTL_INTRADAY,
    TTL_PROFILE,
    TTL_QUOTE,
    TTL_SEARCH,
    cache_key,
    cached,
)
from app.integrations.market.base import HistoryRange, MarketDataError, Quote
from app.repositories.base import CacheRepository
from app.schemas.agents import PricePoint
from app.schemas.assets import AssetMatch, AssetType
from app.utils.time import utc_now_iso

logger = logging.getLogger(__name__)

_RANGE_TO_ARGS: dict[str, tuple[str, str]] = {
    "1d": ("1d", "5m"),
    "5d": ("5d", "30m"),
    "1mo": ("1mo", "1d"),
    "6mo": ("6mo", "1d"),
    "1y": ("1y", "1d"),
}

QUOTE_TYPE_MAP: dict[str, AssetType] = {
    "EQUITY": "equity",
    "ETF": "etf",
    "INDEX": "index",
    "CRYPTOCURRENCY": "crypto",
    "CURRENCY": "fx",
    "FUTURE": "commodity",
    "MUTUALFUND": "other",
}


def infer_asset_type(symbol: str) -> AssetType:
    s = symbol.upper()
    if s.startswith("^"):
        return "index"
    if s.endswith("=X"):
        return "fx"
    if s.endswith("=F"):
        return "commodity"
    if s.endswith("-USD") or s.endswith("-EUR"):
        return "crypto"
    return "equity"


def frame_to_points(frame: pd.DataFrame, intraday: bool) -> list[PricePoint]:
    points: list[PricePoint] = []
    if frame is None or frame.empty:
        return points
    for idx, row in frame.iterrows():
        ts = pd.Timestamp(str(idx))
        if intraday:
            ts = ts.tz_convert("UTC") if ts.tzinfo else ts.tz_localize("UTC")
            time_str = ts.isoformat()
        else:
            time_str = ts.strftime("%Y-%m-%d")
        values: list[Any] = [row.get("Open"), row.get("High"), row.get("Low"), row.get("Close")]
        if any(v is None or (isinstance(v, float) and math.isnan(v)) for v in values):
            continue
        volume = row.get("Volume")
        points.append(
            PricePoint(
                time=time_str,
                open=round(float(values[0]), 6),
                high=round(float(values[1]), 6),
                low=round(float(values[2]), 6),
                close=round(float(values[3]), 6),
                volume=None
                if volume is None or (isinstance(volume, float) and math.isnan(volume))
                else float(volume),
            )
        )
    return points


class YahooMarketDataProvider:
    name = "yahoo_finance"

    def __init__(self, cache: CacheRepository | None = None) -> None:
        self._cache = cache

    async def get_history(self, symbol: str, range_: HistoryRange = "6mo") -> list[PricePoint]:
        period, interval = _RANGE_TO_ARGS[range_]
        intraday = interval.endswith("m")

        async def load() -> list[PricePoint]:
            def _fetch() -> list[PricePoint]:
                frame = yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=False)
                return frame_to_points(frame, intraday)

            try:
                points = await asyncio.to_thread(_fetch)
            except Exception as exc:
                raise MarketDataError(f"Yahoo history unavailable for {symbol}") from exc
            if not points:
                raise MarketDataError(f"No price history for {symbol}")
            return points

        return await cached(
            self._cache,
            cache_key(self.name, "history", symbol, period, interval),
            TTL_INTRADAY if intraday else TTL_HISTORY,
            load,
            encode=lambda pts: [p.model_dump() for p in pts],
            decode=lambda raw: [PricePoint.model_validate(p) for p in raw],
        )

    async def _profile(self, symbol: str) -> dict[str, Any]:
        async def load() -> dict[str, Any]:
            def _fetch() -> dict[str, Any]:
                try:
                    info = yf.Ticker(symbol).get_info() or {}
                except Exception:
                    info = {}
                return {
                    "name": info.get("longName") or info.get("shortName"),
                    "quote_type": info.get("quoteType"),
                    "currency": info.get("currency"),
                    "sector": info.get("sector"),
                    "industry": info.get("industry"),
                }

            return await asyncio.to_thread(_fetch)

        return await cached(self._cache, cache_key(self.name, "profile", symbol), TTL_PROFILE, load)

    async def get_quote(self, symbol: str) -> Quote:
        async def load() -> dict[str, Any]:
            def _fetch() -> dict[str, Any]:
                fi = yf.Ticker(symbol).fast_info
                last = fi.get("lastPrice")
                prev = fi.get("previousClose") or fi.get("regularMarketPreviousClose")
                return {"last": last, "prev": prev, "currency": fi.get("currency"), "qt": fi.get("quoteType")}

            try:
                return await asyncio.to_thread(_fetch)
            except Exception as exc:
                raise MarketDataError(f"Yahoo quote unavailable for {symbol}") from exc

        raw = await cached(self._cache, cache_key(self.name, "quote", symbol), TTL_QUOTE, load)
        if raw.get("last") is None:
            raise MarketDataError(f"No quote for {symbol}")
        profile = await self._profile(symbol)
        asset_type = QUOTE_TYPE_MAP.get(
            str(profile.get("quote_type") or raw.get("qt") or "").upper()
        ) or infer_asset_type(symbol)
        return Quote(
            symbol=symbol,
            name=profile.get("name"),
            asset_type=asset_type,
            currency=raw.get("currency") or profile.get("currency"),
            last_price=_num(raw.get("last")),
            previous_close=_num(raw.get("prev")),
            retrieved_at=utc_now_iso(),
            provider=self.name,
        )

    async def search(self, query: str, limit: int = 8) -> list[AssetMatch]:
        async def load() -> list[dict[str, Any]]:
            def _fetch() -> list[dict[str, Any]]:
                result = yf.Search(query, max_results=limit, news_count=0, enable_fuzzy_query=True)
                return list(result.quotes or [])

            try:
                return await asyncio.to_thread(_fetch)
            except Exception as exc:
                logger.warning("yahoo_search_failed", extra={"error_type": type(exc).__name__})
                return []

        quotes = await cached(self._cache, cache_key(self.name, "search", "-", query), TTL_SEARCH, load)
        matches: list[AssetMatch] = []
        for q in quotes:
            symbol = q.get("symbol")
            if not symbol:
                continue
            matches.append(
                AssetMatch(
                    symbol=symbol,
                    name=q.get("longname") or q.get("shortname") or symbol,
                    asset_type=QUOTE_TYPE_MAP.get(str(q.get("quoteType", "")).upper(), "other"),
                    exchange=q.get("exchDisp") or q.get("exchange"),
                    source="provider",
                )
            )
        return matches[:limit]


def _num(value: Any) -> float | None:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else round(f, 6)
