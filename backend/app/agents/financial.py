"""Financial Agent — SEC fundamentals (deterministic). The Synthesis Agent explains them."""

from __future__ import annotations

from typing import Any

from app.agents.base import AgentContext, AgentOutput, AgentSkipped
from app.agents.sources import filing_source, sec_facts_source
from app.integrations.financial.base import FinancialDataError


class FinancialAgent:
    name = "financial"
    label = "Financial Agent"

    async def run(self, state: dict[str, Any], ctx: AgentContext) -> AgentOutput:
        symbol = state.get("symbol")
        if not symbol or ctx.financial is None:
            raise AgentSkipped("No financial data provider for this asset")
        try:
            snapshot = await ctx.financial.snapshot(symbol)
        except FinancialDataError as exc:
            raise AgentSkipped(f"Financial data unavailable: {exc}") from exc
        if not snapshot.applicable:
            return AgentOutput({"financial": snapshot}, snapshot.note or "Fundamentals not applicable")
        sources = []
        if snapshot.cik:
            sources.append(sec_facts_source(snapshot.cik, snapshot.entity_name))
            sources.extend(filing_source(snapshot.cik, f) for f in snapshot.recent_filings[:6])
        snapshot.source_ids = [s.id for s in sources]
        period = f" (period ending {snapshot.period_end})" if snapshot.period_end else ""
        if snapshot.revenue is None:
            summary = f"Reviewed SEC filings{period}; structured financials not available"
        else:
            summary = f"Analyzed latest available financial data{period}"
        return AgentOutput({"financial": snapshot, "sources": sources}, summary)
