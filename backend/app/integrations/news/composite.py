"""Runs several news providers and merges their results. One failing provider never fails the search."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from dataclasses import dataclass, field

from app.integrations.news.base import NewsProvider, NewsQuery, NewsTimelineProvider, NewsTimelines
from app.schemas.agents import NewsArticle

logger = logging.getLogger(__name__)


@dataclass
class NewsSearchResult:
    articles: list[NewsArticle] = field(default_factory=list)
    providers_used: list[str] = field(default_factory=list)
    providers_failed: list[str] = field(default_factory=list)


class CompositeNewsProvider:
    def __init__(
        self, providers: Sequence[NewsProvider], timeline_provider: NewsTimelineProvider | None = None
    ) -> None:
        self._providers = list(providers)
        self._timeline = timeline_provider
        self.name = "+".join(p.name for p in self._providers)

    @property
    def provider_names(self) -> list[str]:
        return [p.name for p in self._providers]

    async def search_all(self, query: NewsQuery) -> NewsSearchResult:
        result = NewsSearchResult()
        outcomes = await asyncio.gather(*(p.search(query) for p in self._providers), return_exceptions=True)
        for provider, outcome in zip(self._providers, outcomes, strict=True):
            if isinstance(outcome, BaseException):
                logger.info(
                    "news_provider_failed",
                    extra={"provider": provider.name, "error_type": type(outcome).__name__},
                )
                result.providers_failed.append(provider.name)
                continue
            result.providers_used.append(provider.name)
            result.articles.extend(outcome)
        return result

    async def timelines(self, query: NewsQuery) -> NewsTimelines:
        if self._timeline is None:
            return NewsTimelines()
        try:
            return await self._timeline.timelines(query)
        except Exception as exc:
            logger.info("news_timeline_failed", extra={"error_type": type(exc).__name__})
            return NewsTimelines()
