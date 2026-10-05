"""FRED (St. Louis Fed) macro data — optional, requires a free FRED_API_KEY. Cached for hours."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.integrations.cache import TTL_MACRO, cache_key, cached
from app.integrations.macro.base import MacroDataError
from app.repositories.base import CacheRepository
from app.schemas.agents import MacroIndicator, SeriesPoint

BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

# Small curated set: (series_id, display name, unit, transform)
SERIES: list[tuple[str, str, str, str]] = [
    ("FEDFUNDS", "Fed Funds Rate", "%", "level"),
    ("CPIAUCSL", "CPI inflation (YoY)", "%", "yoy"),
    ("UNRATE", "Unemployment rate", "%", "level"),
    ("A191RL1Q225SBEA", "Real GDP growth (QoQ annualised)", "%", "level"),
    ("DGS10", "10-Year Treasury yield", "%", "level"),
]


def _transform(observations: list[dict[str, Any]], transform: str) -> list[SeriesPoint]:
    values = [(o["date"], float(o["value"])) for o in observations if o.get("value") not in (None, ".")]
    values.sort()
    if transform == "yoy":
        out = []
        for i in range(12, len(values)):
            prior = values[i - 12][1]
            if prior:
                out.append(SeriesPoint(date=values[i][0], value=round((values[i][1] / prior - 1) * 100, 2)))
        return out
    return [SeriesPoint(date=d, value=round(v, 3)) for d, v in values]


class FredMacroProvider:
    name = "fred"

    def __init__(
        self,
        api_key: str,
        cache: CacheRepository | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._key = api_key
        self._cache = cache
        self._transport = transport

    async def _series(self, series_id: str) -> list[dict[str, Any]]:
        async def load() -> list[dict[str, Any]]:
            async with httpx.AsyncClient(timeout=20, transport=self._transport) as client:
                resp = await client.get(
                    BASE_URL,
                    params={
                        "series_id": series_id,
                        "api_key": self._key,
                        "file_type": "json",
                        "sort_order": "desc",
                        "limit": "40",
                    },
                )
            if resp.status_code != 200:
                raise MacroDataError(f"FRED HTTP {resp.status_code}")
            observations: list[dict[str, Any]] = resp.json().get("observations", [])
            return observations

        return await cached(self._cache, cache_key(self.name, "series", series_id), TTL_MACRO, load)

    async def indicators(self) -> list[MacroIndicator]:
        results = await asyncio.gather(*(self._series(s[0]) for s in SERIES), return_exceptions=True)
        out: list[MacroIndicator] = []
        for (series_id, name, unit, transform), obs in zip(SERIES, results, strict=True):
            if isinstance(obs, BaseException):
                continue
            points = _transform(obs, transform)
            if not points:
                continue
            last = points[-1]
            prev = points[-2] if len(points) > 1 else None
            out.append(
                MacroIndicator(
                    id=series_id,
                    name=name,
                    value=last.value,
                    change=round(last.value - prev.value, 3) if prev else None,
                    unit=unit,
                    as_of=last.date,
                    provider=self.name,
                    series=points[-24:],
                    source_id=f"src_fred_{series_id.lower()}",
                )
            )
        if not out:
            raise MacroDataError("FRED returned no data")
        return out
