"""Read-through cache helper for external providers.

Cache keys always include provider, asset, query and time window, e.g.
`yahoo:history:NVDA:6mo:1d`. TTLs are chosen per data type (see constants).
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from app.repositories.base import CacheRepository

logger = logging.getLogger(__name__)

T = TypeVar("T")

TTL_QUOTE = 60
TTL_INTRADAY = 120
TTL_HISTORY = 15 * 60
TTL_NEWS = 10 * 60
TTL_SEARCH = 24 * 3600
TTL_PROFILE = 24 * 3600
TTL_SEC_FACTS = 12 * 3600
TTL_SEC_TICKERS = 24 * 3600
TTL_MACRO = 6 * 3600


def cache_key(provider: str, kind: str, asset: str = "-", query: str = "-", window: str = "-") -> str:
    return ":".join([provider, kind, asset.upper(), query.lower()[:120], window])


async def cached(
    cache: CacheRepository | None,
    key: str,
    ttl: int,
    loader: Callable[[], Awaitable[T]],
    *,
    encode: Callable[[T], Any] = lambda v: v,
    decode: Callable[[Any], T] = lambda v: v,
) -> T:
    if cache is not None:
        hit = cache.get(key)
        if hit is not None:
            try:
                return decode(hit)
            except Exception:  # corrupted/old cache entry → reload
                logger.warning("cache_decode_failed", extra={"cache_key": key})
    value = await loader()
    if cache is not None:
        try:
            cache.set(key, encode(value), ttl)
        except Exception:
            logger.warning("cache_write_failed", extra={"cache_key": key})
    return value
