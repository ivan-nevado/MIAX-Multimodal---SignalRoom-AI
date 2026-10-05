from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator

from app.schemas.agents import FinancialSnapshot, MarketMetrics, PricePoint
from app.schemas.common import Model

AssetType = Literal["equity", "etf", "index", "crypto", "fx", "commodity", "other"]


class AssetMatch(Model):
    symbol: str
    name: str
    asset_type: AssetType = "other"
    exchange: str | None = None
    source: Literal["alias", "provider"] = "provider"


class AssetQuote(Model):
    symbol: str
    name: str
    asset_type: AssetType
    currency: str | None = None
    last_price: float | None = None
    previous_close: float | None = None
    move_pct: float | None = None
    retrieved_at: str
    delayed_notice: str = "Market data may be delayed. Educational prototype."


class AssetDetail(Model):
    quote: AssetQuote
    metrics: MarketMetrics | None = None
    history: list[PricePoint] = Field(default_factory=list)
    range: str
    news: list[dict[str, object]] = Field(default_factory=list)
    financial: FinancialSnapshot | None = None
    recent_investigations: list[dict[str, object]] = Field(default_factory=list)


class WatchlistItem(Model):
    user_id: str
    symbol: str
    display_name: str
    asset_type: AssetType = "other"
    position: int = 0
    added_at: str


class WatchlistItemView(Model):
    symbol: str
    display_name: str
    asset_type: AssetType
    position: int
    added_at: str
    quote: AssetQuote | None = None


class AddWatchlistRequest(Model):
    symbol: str = Field(min_length=1, max_length=32)
    display_name: str | None = Field(default=None, max_length=80)

    @field_validator("symbol")
    @classmethod
    def _sym(cls, v: str) -> str:
        return v.strip()


class ReorderWatchlistRequest(Model):
    symbols: list[str] = Field(min_length=1, max_length=50)


class MarketOverview(Model):
    indices: list[AssetQuote]
    retrieved_at: str
    delayed_notice: str = "Market data may be delayed. Educational prototype."
