from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.analytics.clustering import deduplicate, rank_articles
from app.analytics.metrics import compute_market_metrics, percentage_change
from app.integrations.financial.base import FinancialDataProvider
from app.integrations.market.base import HistoryRange, MarketDataError, MarketDataProvider, Quote
from app.integrations.market.yahoo import infer_asset_type
from app.integrations.news.base import NewsQuery
from app.integrations.news.composite import CompositeNewsProvider
from app.repositories.base import InvestigationRepository
from app.schemas.agents import FinancialSnapshot
from app.schemas.assets import AssetDetail, AssetMatch, AssetQuote, MarketOverview
from app.services.entity_resolution import EntityResolver, resolve_alias
from app.services.errors import NotFoundError, UpstreamUnavailable
from app.utils.time import utc_now_iso

logger = logging.getLogger(__name__)

OVERVIEW_SYMBOLS = ["^GSPC", "^IXIC", "^DJI", "^VIX", "BTC-USD", "EURUSD=X", "GC=F", "^TNX"]


def quote_to_view(q: Quote, fallback_name: str | None = None) -> AssetQuote:
    return AssetQuote(
        symbol=q.symbol,
        name=q.name or fallback_name or q.symbol,
        asset_type=q.asset_type,
        currency=q.currency,
        last_price=q.last_price,
        previous_close=q.previous_close,
        move_pct=round(percentage_change(q.previous_close, q.last_price) or 0.0, 2)
        if q.previous_close
        else None,
        retrieved_at=q.retrieved_at,
    )


class AssetService:
    def __init__(
        self,
        market: MarketDataProvider,
        news: CompositeNewsProvider,
        investigations: InvestigationRepository,
        financial: FinancialDataProvider | None = None,
    ) -> None:
        self._market = market
        self._news = news
        self._investigations = investigations
        self._financial = financial
        self.resolver = EntityResolver(market)

    async def search(self, query: str) -> list[AssetMatch]:
        return await self.resolver.search(query)

    async def quote(self, symbol: str) -> AssetQuote | None:
        alias = resolve_alias(symbol)
        try:
            q = await self._market.get_quote(symbol)
        except MarketDataError:
            return None
        view = quote_to_view(q, alias.name if alias else None)
        if alias:  # curated short names read better than provider long names
            view.name = alias.name
            view.asset_type = alias.asset_type
        return view

    async def quotes(self, symbols: list[str]) -> dict[str, AssetQuote | None]:
        results = await asyncio.gather(*(self.quote(s) for s in symbols))
        return dict(zip(symbols, results, strict=True))

    async def overview(self) -> MarketOverview:
        quotes = await self.quotes(OVERVIEW_SYMBOLS)
        return MarketOverview(
            indices=[q for q in quotes.values() if q is not None], retrieved_at=utc_now_iso()
        )

    async def detail(self, symbol: str, range_: HistoryRange, user_id: str) -> AssetDetail:
        symbol = symbol.strip()
        alias = resolve_alias(symbol)
        if alias:
            symbol = alias.symbol
        try:
            history, daily, quote = await asyncio.gather(
                self._market.get_history(symbol, range_),
                self._market.get_history(symbol, "6mo"),
                self._market.get_quote(symbol),
            )
        except MarketDataError as exc:
            logger.info("asset_detail_unavailable", extra={"symbol": symbol})
            raise NotFoundError(f"No market data available for {symbol}.") from exc
        view = quote_to_view(quote, alias.name if alias else None)
        if alias:
            view.asset_type = alias.asset_type
        elif view.asset_type == "other":
            view.asset_type = infer_asset_type(symbol)
        metrics = compute_market_metrics(symbol, daily, currency=quote.currency)
        news, financial = await asyncio.gather(
            self._headlines(symbol, view.name, view.asset_type), self._fundamentals(symbol, view.asset_type)
        )
        recent = [
            {
                "investigation_id": r.investigation_id,
                "question": r.question,
                "status": r.status,
                "created_at": r.created_at,
                "summary": r.summary,
            }
            for r in self._investigations.list_by_user(user_id, 50)
            if r.symbol == symbol
        ][:5]
        return AssetDetail(
            quote=view,
            metrics=metrics,
            history=history,
            range=range_,
            news=news,
            financial=financial,
            recent_investigations=recent,
        )

    async def _fundamentals(self, symbol: str, asset_type: str) -> FinancialSnapshot | None:
        if self._financial is None or asset_type not in ("equity", "etf", "other"):
            return None
        try:
            snap = await asyncio.wait_for(self._financial.snapshot(symbol), timeout=20)
        except Exception:
            return None
        return snap if snap.applicable else None

    async def _headlines(self, symbol: str, name: str, asset_type: str) -> list[dict[str, Any]]:
        from app.agents.news import entity_terms

        terms = entity_terms(symbol, name, asset_type)
        if not terms:
            return []
        try:
            result = await asyncio.wait_for(
                self._news.search_all(NewsQuery(terms=terms, symbol=symbol, days=7)), timeout=12
            )
        except (TimeoutError, Exception):
            return []
        ranked = rank_articles(deduplicate(result.articles), terms)
        return [
            {
                "id": a.id,
                "title": a.title,
                "url": a.url,
                "publisher": a.publisher,
                "published_at": a.published_at,
                "relevance": a.relevance,
            }
            for a in ranked
            if a.relevance >= 0.45
        ][:8]


def require_market_data(view: AssetQuote | None, symbol: str) -> AssetQuote:
    if view is None:
        raise UpstreamUnavailable(f"Market data for {symbol} is temporarily unavailable.")
    return view
