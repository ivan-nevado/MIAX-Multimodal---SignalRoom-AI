from __future__ import annotations

from typing import Literal, Protocol

from app.schemas.agents import PricePoint
from app.schemas.assets import AssetMatch, AssetType
from app.schemas.common import Model

HistoryRange = Literal["1d", "5d", "1mo", "6mo", "1y"]


class MarketDataError(Exception):
    pass


class Quote(Model):
    symbol: str
    name: str | None = None
    asset_type: AssetType = "other"
    currency: str | None = None
    last_price: float | None = None
    previous_close: float | None = None
    retrieved_at: str
    provider: str


class MarketDataProvider(Protocol):
    """Market data adapter. Agents depend on this interface, never on yfinance directly."""

    name: str

    async def get_history(self, symbol: str, range_: HistoryRange = "6mo") -> list[PricePoint]: ...
    async def get_quote(self, symbol: str) -> Quote: ...
    async def search(self, query: str, limit: int = 8) -> list[AssetMatch]: ...
