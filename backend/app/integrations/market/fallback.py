"""Chain of market data providers: the first one that answers wins."""

from __future__ import annotations

import logging
from collections.abc import Sequence

from app.integrations.market.base import HistoryRange, MarketDataError, MarketDataProvider, Quote
from app.schemas.agents import PricePoint
from app.schemas.assets import AssetMatch

logger = logging.getLogger(__name__)


class FallbackMarketDataProvider:
    def __init__(self, providers: Sequence[MarketDataProvider]) -> None:
        if not providers:
            raise ValueError("At least one market data provider is required")
        self._providers = list(providers)
        self.name = "+".join(p.name for p in self._providers)

    async def get_history(self, symbol: str, range_: HistoryRange = "6mo") -> list[PricePoint]:
        errors: list[str] = []
        for provider in self._providers:
            try:
                return await provider.get_history(symbol, range_)
            except MarketDataError as exc:
                errors.append(f"{provider.name}: {exc}")
                logger.info("market_provider_fallback", extra={"provider": provider.name, "op": "history"})
        raise MarketDataError("; ".join(errors))

    async def get_quote(self, symbol: str) -> Quote:
        errors: list[str] = []
        for provider in self._providers:
            try:
                return await provider.get_quote(symbol)
            except MarketDataError as exc:
                errors.append(f"{provider.name}: {exc}")
        raise MarketDataError("; ".join(errors))

    async def search(self, query: str, limit: int = 8) -> list[AssetMatch]:
        for provider in self._providers:
            try:
                results = await provider.search(query, limit)
            except MarketDataError:
                continue
            if results:
                return results
        return []
