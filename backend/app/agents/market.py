"""Market Agent — price, returns, volume, volatility, drawdown and unusual-move detection.

All numbers are computed in Python (app.analytics.metrics). No LLM call here: the
Synthesis Agent interprets these structured metrics.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.agents.base import AgentContext, AgentOutput, AgentSkipped
from app.agents.sources import market_source
from app.analytics.metrics import compute_market_metrics
from app.integrations.market.base import MarketDataError
from app.schemas.agents import MarketFindings


def benchmark_for(symbol: str, asset_type: str | None) -> str | None:
    if asset_type in ("equity", "etf", None) and not symbol.startswith("^"):
        return "^GSPC"
    if asset_type == "crypto" and symbol.upper() != "BTC-USD":
        return "BTC-USD"
    return None


class MarketAgent:
    name = "market"
    label = "Market Agent"

    async def run(self, state: dict[str, Any], ctx: AgentContext) -> AgentOutput:
        symbol: str | None = state.get("symbol")
        if not symbol:
            raise AgentSkipped("No asset selected")
        asset_type = state.get("asset_type")
        bench = benchmark_for(symbol, asset_type)

        async def safe(coro: Any) -> Any:
            try:
                return await coro
            except MarketDataError:
                return None

        history, intraday, bench_history, quote = await asyncio.gather(
            ctx.market.get_history(symbol, "6mo"),
            safe(ctx.market.get_history(symbol, "1d")),
            safe(ctx.market.get_history(bench, "6mo")) if bench else asyncio.sleep(0, result=None),
            safe(ctx.market.get_quote(symbol)),
        )
        metrics = compute_market_metrics(
            symbol,
            history,
            currency=quote.currency if quote else None,
            benchmark_symbol=bench if bench_history else None,
            benchmark_history=bench_history,
        )
        sources = [market_source(symbol, ctx.market.name)]
        if bench and bench_history:
            sources.append(market_source(bench, ctx.market.name, f"{bench} benchmark history"))
        findings = MarketFindings(
            metrics=metrics,
            history=history[-130:],
            intraday=intraday or [],
            source_ids=[s.id for s in sources],
        )
        update = {"market": findings, "sources": sources}
        if quote and quote.name and not state.get("asset_name"):
            update["asset_name"] = quote.name
        move = f"{metrics.move_pct:+.2f}%" if metrics.move_pct is not None else "n/a"
        flag = " — unusual session" if metrics.unusual_move else ""
        return AgentOutput(update, f"Analyzed price, volatility and volume ({symbol} {move}{flag})")
