from __future__ import annotations

from app.repositories.base import WatchlistRepository
from app.schemas.assets import WatchlistItem, WatchlistItemView
from app.services.asset_service import AssetService
from app.services.errors import ConflictError, NotFoundError, ValidationFailed
from app.utils.time import utc_now_iso

DEMO_WATCHLIST = [
    ("NVDA", "NVIDIA", "equity"),
    ("TSLA", "Tesla", "equity"),
    ("BTC-USD", "Bitcoin", "crypto"),
    ("^GSPC", "S&P 500", "index"),
    ("EURUSD=X", "EUR/USD", "fx"),
]


class WatchlistService:
    def __init__(self, repo: WatchlistRepository, assets: AssetService, max_size: int) -> None:
        self._repo = repo
        self._assets = assets
        self._max = max_size

    def seed_demo(self, user_id: str) -> None:
        if self._repo.list(user_id):
            return
        now = utc_now_iso()
        for idx, (symbol, name, kind) in enumerate(DEMO_WATCHLIST):
            self._repo.put(
                WatchlistItem(
                    user_id=user_id,
                    symbol=symbol,
                    display_name=name,
                    asset_type=kind,
                    position=idx,
                    added_at=now,
                )
            )

    async def list_items(self, user_id: str, with_quotes: bool = True) -> list[WatchlistItemView]:
        items = self._repo.list(user_id)
        quotes = await self._assets.quotes([i.symbol for i in items]) if with_quotes and items else {}
        return [
            WatchlistItemView(
                symbol=i.symbol,
                display_name=i.display_name,
                asset_type=i.asset_type,
                position=i.position,
                added_at=i.added_at,
                quote=quotes.get(i.symbol),
            )
            for i in items
        ]

    def symbols(self, user_id: str) -> list[str]:
        return [i.symbol for i in self._repo.list(user_id)]

    async def add(self, user_id: str, query: str, display_name: str | None = None) -> WatchlistItemView:
        items = self._repo.list(user_id)
        if len(items) >= self._max:
            raise ValidationFailed(f"Your watchlist can hold up to {self._max} assets in this MVP.")
        match = await self._assets.resolver.resolve(query)
        if match is None:
            raise NotFoundError(f"Could not find an asset matching '{query}'.")
        if any(i.symbol == match.symbol for i in items):
            raise ConflictError(f"{match.symbol} is already in your watchlist.")
        item = WatchlistItem(
            user_id=user_id,
            symbol=match.symbol,
            display_name=display_name or match.name,
            asset_type=match.asset_type,
            position=max((i.position for i in items), default=-1) + 1,
            added_at=utc_now_iso(),
        )
        self._repo.put(item)
        quote = await self._assets.quote(item.symbol)
        return WatchlistItemView(**item.model_dump(exclude={"user_id"}), quote=quote)

    def remove(self, user_id: str, symbol: str) -> None:
        if not self._repo.delete(user_id, symbol):
            raise NotFoundError(f"{symbol} is not in your watchlist.")

    def reorder(self, user_id: str, symbols: list[str]) -> None:
        items = {i.symbol: i for i in self._repo.list(user_id)}
        if set(symbols) != set(items):
            raise ValidationFailed("Reorder must include exactly the symbols in your watchlist.")
        for position, symbol in enumerate(symbols):
            self._repo.put(items[symbol].model_copy(update={"position": position}))
