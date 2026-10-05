"""Keyless cross-asset market context (indices, volatility, rates, dollar, oil, gold) via the market provider."""

from __future__ import annotations

import asyncio

from app.analytics.metrics import percentage_change
from app.integrations.market.base import MarketDataError, MarketDataProvider
from app.schemas.agents import MacroIndicator, SeriesPoint

CONTEXT_SYMBOLS: list[tuple[str, str, str]] = [
    ("^GSPC", "S&P 500", "pts"),
    ("^IXIC", "Nasdaq Composite", "pts"),
    ("^VIX", "VIX volatility index", "pts"),
    ("^TNX", "US 10Y yield", "%"),
    ("DX-Y.NYB", "US Dollar index", "pts"),
    ("CL=F", "WTI crude oil", "USD"),
    ("GC=F", "Gold", "USD"),
]


class MarketContextProvider:
    name = "yahoo_market_context"

    def __init__(self, market: MarketDataProvider) -> None:
        self._market = market

    async def indicators(self) -> list[MacroIndicator]:
        async def one(symbol: str, name: str, unit: str) -> MacroIndicator | None:
            try:
                history = await self._market.get_history(symbol, "1mo")
            except MarketDataError:
                return None
            if len(history) < 2:
                return None
            last, prev = history[-1], history[-2]
            return MacroIndicator(
                id=symbol,
                name=name,
                value=round(last.close, 3),
                change=round(percentage_change(prev.close, last.close) or 0.0, 2),
                unit=unit,
                as_of=last.time,
                provider=self._market.name,
                series=[SeriesPoint(date=p.time, value=p.close) for p in history],
                source_id=f"src_mkt_{symbol.lower().replace('^', '').replace('=', '').replace('.', '')}",
            )

        results = await asyncio.gather(*(one(*s) for s in CONTEXT_SYMBOLS))
        return [r for r in results if r is not None]
