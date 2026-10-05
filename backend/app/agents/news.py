"""News Agent — retrieve → deduplicate → rank → cluster → LLM labels clusters (headlines only)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.agents.base import AgentContext, AgentOutput, AgentSkipped
from app.agents.sources import news_source
from app.analytics.clustering import cluster_articles, deduplicate, rank_articles
from app.integrations.ai.base import AIError
from app.integrations.news.base import NewsProviderError, NewsQuery
from app.prompts.loader import system_prompt
from app.schemas.agents import ClusterLabels, NewsCluster, NewsFindings

logger = logging.getLogger(__name__)

_SUFFIX_RE = re.compile(
    r"\b(corporation|corp\.?|incorporated|inc\.?|holdings?|plc|ltd\.?|limited|company|co\.?|s\.a\.?|ag|n\.v\.?|class [a-z])\b",
    re.I,
)
MAX_ARTICLES = 40
LABEL_CLUSTERS = 5
HEADLINES_PER_CLUSTER = 4
MIN_LLM_RELEVANCE = 0.25


def entity_terms(symbol: str | None, name: str | None, asset_type: str | None) -> list[str]:
    terms: list[str] = []
    if name:
        core = _SUFFIX_RE.sub("", name).replace(",", " ").strip()
        core = " ".join(core.split())
        if core:
            terms.append(core)
    if symbol and asset_type in ("equity", "etf", None) and symbol.isalpha() and len(symbol) >= 3:
        terms.append(symbol.upper())
    if symbol and asset_type == "crypto":
        terms.append(symbol.split("-")[0])
    return terms


class NewsAgent:
    name = "news"
    label = "News Agent"

    async def run(self, state: dict[str, Any], ctx: AgentContext) -> AgentOutput:
        terms = entity_terms(state.get("symbol"), state.get("asset_name"), state.get("asset_type"))
        if not terms:
            raise AgentSkipped("No entity to search news for")
        plan = state.get("plan")
        days = min(max(plan.time_window_days if plan else 7, 2), 30)
        query = NewsQuery(terms=terms, symbol=state.get("symbol"), days=days)

        search = await ctx.news.search_all(query)
        if not search.providers_used:
            raise NewsProviderError("All news providers are unavailable")
        timelines = await ctx.news.timelines(query)
        reviewed = len(search.articles)
        articles = rank_articles(deduplicate(search.articles), terms)[:MAX_ARTICLES]
        clusters = cluster_articles(articles, terms)
        warnings = [f"News provider unavailable: {p}" for p in search.providers_failed]

        by_id = {a.id: a for a in articles}
        clusters = await self._label(clusters, by_id, state, ctx)
        kept_ids = {aid for c in clusters for aid in c.article_ids}
        kept_articles = [a for a in articles if a.id in kept_ids]
        findings = NewsFindings(
            query=" OR ".join(terms),
            articles_reviewed=reviewed,
            articles=kept_articles,
            clusters=clusters,
            tone_timeline=timelines.tone,
            volume_timeline=timelines.volume,
            providers_used=search.providers_used,
        )
        sources = [news_source(a) for a in kept_articles]
        publishers = len({a.publisher for a in kept_articles})
        if not kept_articles:
            summary = "No relevant recent news found"
        else:
            summary = f"Reviewed {reviewed} articles; {len(clusters)} themes from {publishers} publishers"
        return AgentOutput({"news": findings, "sources": sources}, summary, warnings)

    async def _label(
        self, clusters: list[NewsCluster], by_id: dict[str, Any], state: dict[str, Any], ctx: AgentContext
    ) -> list[NewsCluster]:
        if not clusters or not ctx.ai.available("reasoning"):
            return clusters
        top = clusters[:LABEL_CLUSTERS]
        payload = {
            "asset": {"symbol": state.get("symbol"), "name": state.get("asset_name")},
            "clusters": [
                {
                    "cluster_id": c.cluster_id,
                    "headlines": [
                        {
                            "title": by_id[a].title,
                            "publisher": by_id[a].publisher,
                            "published_at": by_id[a].published_at,
                        }
                        for a in c.article_ids[:HEADLINES_PER_CLUSTER]
                    ],
                }
                for c in top
            ],
        }
        try:
            labels = await ctx.ai.structured(
                ClusterLabels,
                system=system_prompt("news_agent", "news_research"),
                user=json.dumps(payload),
                agent=self.name,
                purpose="label_clusters",
                max_tokens=1800,
            )
        except AIError as exc:
            logger.warning("news_labeling_failed", extra={"error_type": type(exc).__name__})
            return top
        by_cluster = {lbl.cluster_id: lbl for lbl in labels.clusters}
        labelled: list[NewsCluster] = []
        for c in top:
            lbl = by_cluster.get(c.cluster_id)
            if lbl is None:
                labelled.append(c)
                continue
            if lbl.relevance < MIN_LLM_RELEVANCE:
                continue  # generic market commentary that merely mentions the asset
            labelled.append(
                c.model_copy(
                    update={
                        "theme": lbl.theme,
                        "summary": lbl.summary,
                        "event_type": lbl.event_type,
                        "tone": lbl.tone,
                    }
                )
            )
        return labelled
