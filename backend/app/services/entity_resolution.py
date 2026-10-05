"""Deterministic entity resolution: alias table first, provider search second. Never the LLM."""

from __future__ import annotations

import re

from app.integrations.market.base import MarketDataProvider
from app.schemas.assets import AssetMatch, AssetType

_ALIASES: list[tuple[str, str, AssetType, list[str]]] = [
    ("NVDA", "NVIDIA Corporation", "equity", ["nvidia", "nvda"]),
    ("TSLA", "Tesla, Inc.", "equity", ["tesla", "tsla"]),
    ("AAPL", "Apple Inc.", "equity", ["apple", "aapl"]),
    ("MSFT", "Microsoft Corporation", "equity", ["microsoft", "msft"]),
    ("AMZN", "Amazon.com, Inc.", "equity", ["amazon", "amzn"]),
    ("GOOGL", "Alphabet Inc.", "equity", ["alphabet", "google", "googl", "goog"]),
    ("META", "Meta Platforms, Inc.", "equity", ["meta", "facebook"]),
    ("AMD", "Advanced Micro Devices, Inc.", "equity", ["amd", "advanced micro devices"]),
    ("NFLX", "Netflix, Inc.", "equity", ["netflix"]),
    ("JPM", "JPMorgan Chase & Co.", "equity", ["jpmorgan", "jp morgan", "jpm"]),
    ("BTC-USD", "Bitcoin", "crypto", ["bitcoin", "btc"]),
    ("ETH-USD", "Ethereum", "crypto", ["ethereum", "eth", "ether"]),
    ("^GSPC", "S&P 500", "index", ["s&p 500", "s&p500", "sp500", "s and p 500", "spx"]),
    ("^IXIC", "Nasdaq Composite", "index", ["nasdaq", "nasdaq composite"]),
    ("^DJI", "Dow Jones", "index", ["dow jones", "dow", "dow jones industrial average"]),
    ("^VIX", "VIX volatility", "index", ["vix", "volatility index"]),
    ("^TNX", "US 10Y yield", "index", ["10 year yield", "us 10y", "tnx"]),
    ("^IBEX", "IBEX 35", "index", ["ibex", "ibex 35"]),
    ("^STOXX50E", "Euro Stoxx 50", "index", ["euro stoxx 50", "eurostoxx"]),
    ("EURUSD=X", "EUR/USD", "fx", ["eur/usd", "eurusd", "euro dollar", "eur usd"]),
    ("GBPUSD=X", "GBP/USD", "fx", ["gbp/usd", "gbpusd"]),
    ("GC=F", "Gold", "commodity", ["gold", "oro"]),
    ("CL=F", "WTI Crude Oil", "commodity", ["oil", "crude", "wti", "petroleo", "petróleo"]),
    ("SAN.MC", "Banco Santander", "equity", ["santander"]),
    ("ITX.MC", "Inditex", "equity", ["inditex"]),
]

ALIAS_INDEX: dict[str, AssetMatch] = {}
for _symbol, _name, _type, _aliases in _ALIASES:
    _match = AssetMatch(symbol=_symbol, name=_name, asset_type=_type, source="alias")
    ALIAS_INDEX[_symbol.lower()] = _match
    for _alias in _aliases:
        ALIAS_INDEX[_alias] = _match

_SYMBOL_RE = re.compile(r"^[\^]?[A-Za-z0-9\.\-=]{1,15}$")


def normalise(query: str) -> str:
    return " ".join(query.strip().lower().split())


def resolve_alias(query: str) -> AssetMatch | None:
    return ALIAS_INDEX.get(normalise(query))


def find_alias_in_text(text: str) -> AssetMatch | None:
    """Find a known asset mentioned in free text (e.g. a voice command 'why did nvidia fall')."""
    lowered = f" {normalise(text)} "
    for alias in sorted(ALIAS_INDEX, key=len, reverse=True):
        if len(alias) >= 3 and re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", lowered):
            return ALIAS_INDEX[alias]
    return None


class EntityResolver:
    def __init__(self, market: MarketDataProvider) -> None:
        self._market = market

    async def search(self, query: str, limit: int = 8) -> list[AssetMatch]:
        query = query.strip()
        if not query:
            return []
        results: list[AssetMatch] = []
        alias = resolve_alias(query)
        if alias:
            results.append(alias)
        prefix = normalise(query)
        for key, match in ALIAS_INDEX.items():
            if key.startswith(prefix) and match not in results:
                results.append(match)
        for match in await self._market.search(query, limit):
            if all(m.symbol != match.symbol for m in results):
                results.append(match)
        return results[:limit]

    async def resolve(self, query: str) -> AssetMatch | None:
        alias = resolve_alias(query)
        if alias:
            return alias
        matches = await self._market.search(query, 5)
        upper = query.strip().upper()
        for m in matches:
            if m.symbol.upper() == upper:
                return m
        if matches:
            return matches[0]
        if _SYMBOL_RE.match(query.strip()):
            return AssetMatch(symbol=upper, name=upper, asset_type="other", source="provider")
        return None
