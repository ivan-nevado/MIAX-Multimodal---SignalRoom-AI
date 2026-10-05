from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from app.schemas.agents import NewsArticle, SeriesPoint


class NewsProviderError(Exception):
    pass


@dataclass
class NewsQuery:
    """What we are looking for. `terms` are entity names/tickers (no LLM-generated queries)."""

    terms: list[str]
    symbol: str | None = None
    days: int = 7
    max_records: int = 60
    extra: list[str] = field(default_factory=list)


@dataclass
class NewsTimelines:
    tone: list[SeriesPoint] = field(default_factory=list)
    volume: list[SeriesPoint] = field(default_factory=list)


class NewsProvider(Protocol):
    name: str

    async def search(self, query: NewsQuery) -> list[NewsArticle]: ...


class NewsTimelineProvider(Protocol):
    name: str

    async def timelines(self, query: NewsQuery) -> NewsTimelines: ...
