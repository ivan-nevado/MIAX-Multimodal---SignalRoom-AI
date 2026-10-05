"""Briefing Agent — personalised editorial daily briefing from the user's watchlist.

Deterministic first (watchlist metrics, ranked/clustered headlines, cross-asset
context), then ONE model call writes the editorial text, citing provided source ids.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from app.agents.base import AgentContext
from app.agents.guardrails import clean_narrative, filter_ids
from app.agents.news import entity_terms
from app.agents.sources import macro_source, market_source, news_source
from app.analytics.clustering import cluster_articles, deduplicate, rank_articles
from app.analytics.metrics import compute_market_metrics
from app.integrations.ai.base import AIError
from app.integrations.market.base import MarketDataError
from app.integrations.news.base import NewsQuery
from app.prompts.loader import system_prompt
from app.schemas.agents import MacroIndicator
from app.schemas.briefings import BriefingLLMOutput, BriefingSection, WatchlistMove
from app.schemas.common import Source

logger = logging.getLogger(__name__)

TOP_MOVERS = 3


@dataclass
class BriefingDraft:
    output: BriefingLLMOutput
    moves: list[WatchlistMove]
    sources: list[Source]
    ai_narrative_available: bool
    warnings: list[str] = field(default_factory=list)


def speech_script(out: BriefingLLMOutput) -> str:
    parts = [out.greeting, out.headline + ".", out.summary]
    for idx, sec in enumerate(out.sections, start=1):
        parts.append(f"{idx}. {sec.title}. {sec.body} Why it matters: {sec.why_it_matters}")
    if out.risk_flags:
        parts.append("Risk flags: " + "; ".join(out.risk_flags[:3]) + ".")
    parts.append("That's your SignalRoom briefing. This is an educational prototype, not investment advice.")
    return "\n\n".join(p for p in parts if p)


def deterministic_briefing(moves: list[WatchlistMove], macro: list[MacroIndicator]) -> BriefingLLMOutput:
    movers = sorted(
        (m for m in moves if m.move_pct is not None), key=lambda m: abs(m.move_pct or 0), reverse=True
    )
    sections = [
        BriefingSection(
            title=f"{m.name or m.symbol} {'rose' if (m.move_pct or 0) > 0 else 'fell'} {abs(m.move_pct or 0):.2f}%",
            symbol=m.symbol,
            body=f"{m.symbol} moved {m.move_pct:+.2f}% in the latest session"
            + (
                f", with volume {m.volume_change_pct:+.0f}% vs its 20-session average."
                if m.volume_change_pct is not None
                else "."
            ),
            why_it_matters="Unusual session." if m.unusual_move else "Within its recent range.",
        )
        for m in movers[:TOP_MOVERS]
    ]
    return BriefingLLMOutput(
        headline="Your watchlist at a glance",
        summary="AI narrative unavailable — this briefing was generated from market data only.",
        sections=sections,
        macro_events=[f"{i.name}: {i.change:+.2f}%" for i in macro[:3] if i.change is not None],
    )


class BriefingAgent:
    name = "briefing"
    label = "Briefing Agent"

    async def run(self, watchlist: Sequence[tuple[str, str, str]], ctx: AgentContext) -> BriefingDraft:
        moves, market_sources = await self._moves(watchlist, ctx)
        sources: list[Source] = list(market_sources)
        warnings: list[str] = []

        movers = sorted(
            (m for m in moves if m.move_pct is not None), key=lambda m: abs(m.move_pct or 0), reverse=True
        )[:TOP_MOVERS]
        headlines: dict[str, list[dict[str, Any]]] = {}
        types = {s: t for s, _, t in watchlist}
        for m in movers:  # sequential: news providers are rate limited
            terms = entity_terms(m.symbol, m.name, types.get(m.symbol))
            if not terms:
                continue
            try:
                result = await asyncio.wait_for(
                    ctx.news.search_all(NewsQuery(terms=terms, symbol=m.symbol, days=3, max_records=40)), 45
                )
            except (TimeoutError, Exception):
                warnings.append(f"News unavailable for {m.symbol}")
                continue
            ranked = rank_articles(deduplicate(result.articles), terms)
            ranked = [a for a in ranked if a.relevance >= 0.45]
            clusters = cluster_articles(ranked, terms, max_clusters=2)
            by_id = {a.id: a for a in ranked}
            items = []
            for c in clusters:
                for aid in c.article_ids[:2]:
                    art = by_id[aid]
                    sources.append(news_source(art))
                    items.append(
                        {
                            "source_id": art.id,
                            "title": art.title,
                            "publisher": art.publisher,
                            "published_at": art.published_at,
                        }
                    )
            headlines[m.symbol] = items

        macro: list[MacroIndicator] = []
        for provider in ctx.macro_providers:
            try:
                macro.extend(await provider.indicators())
            except Exception:
                warnings.append(f"{provider.name} unavailable")
        sources.extend(macro_source(i) for i in macro)

        if not ctx.ai.available("reasoning"):
            return BriefingDraft(deterministic_briefing(moves, macro), moves, sources, False, warnings)

        payload = {
            "watchlist_moves": [m.model_dump() for m in moves],
            "top_movers": [m.symbol for m in movers],
            "headlines_by_symbol": headlines,
            "market_context": [
                {
                    "source_id": i.source_id,
                    "name": i.name,
                    "value": i.value,
                    "change_pct_or_pts": i.change,
                    "unit": i.unit,
                }
                for i in macro
            ],
        }
        try:
            out = await ctx.ai.structured(
                BriefingLLMOutput,
                system=system_prompt("briefing_agent", "briefing_writing", "market_analysis"),
                user=json.dumps(payload, default=str),
                agent=self.name,
                purpose="daily_briefing",
                max_tokens=2500,
                temperature=0.4,
            )
        except AIError as exc:
            logger.warning("briefing_llm_failed", extra={"error_type": type(exc).__name__})
            return BriefingDraft(
                deterministic_briefing(moves, macro),
                moves,
                sources,
                False,
                [*warnings, "AI narrative unavailable"],
            )

        known = {s.id for s in sources}
        out.headline = clean_narrative(out.headline)
        out.summary = clean_narrative(out.summary)
        for sec in out.sections:
            sec.body = clean_narrative(sec.body)
            sec.why_it_matters = clean_narrative(sec.why_it_matters)
            sec.source_ids = filter_ids(sec.source_ids, known)
        out.risk_flags = [clean_narrative(r) for r in out.risk_flags]
        return BriefingDraft(out, moves, sources, True, warnings)

    async def _moves(
        self, watchlist: Sequence[tuple[str, str, str]], ctx: AgentContext
    ) -> tuple[list[WatchlistMove], list[Source]]:
        async def one(symbol: str, name: str) -> tuple[WatchlistMove, Source | None]:
            try:
                history = await ctx.market.get_history(symbol, "6mo")
            except MarketDataError:
                return WatchlistMove(symbol=symbol, name=name), None
            m = compute_market_metrics(symbol, history)
            return (
                WatchlistMove(
                    symbol=symbol,
                    name=name,
                    last_price=m.last_price,
                    move_pct=m.move_pct,
                    return_5d_pct=m.return_5d_pct,
                    volume_change_pct=m.volume_change_pct,
                    unusual_move=m.unusual_move,
                ),
                market_source(symbol, ctx.market.name),
            )

        results = await asyncio.gather(*(one(s, n) for s, n, _ in watchlist))
        return [r[0] for r in results], [r[1] for r in results if r[1] is not None]
