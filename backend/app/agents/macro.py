"""Macro Agent — cross-asset context (keyless) plus optional FRED macro series."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.agents.base import AgentContext, AgentOutput, AgentSkipped
from app.agents.sources import macro_source
from app.schemas.agents import MacroFindings, MacroIndicator

logger = logging.getLogger(__name__)


class MacroAgent:
    name = "macro"
    label = "Macro Agent"

    async def run(self, state: dict[str, Any], ctx: AgentContext) -> AgentOutput:
        if not ctx.macro_providers:
            raise AgentSkipped("No macro providers configured")
        results = await asyncio.gather(*(p.indicators() for p in ctx.macro_providers), return_exceptions=True)
        indicators: list[MacroIndicator] = []
        notes: list[str] = []
        for provider, result in zip(ctx.macro_providers, results, strict=True):
            if isinstance(result, BaseException):
                notes.append(f"{provider.name} unavailable")
                continue
            indicators.extend(result)
        if not indicators:
            raise AgentSkipped("Macro data unavailable")
        if not any(i.provider == "fred" for i in indicators):
            notes.append("FRED macro series not configured (optional FRED_API_KEY).")
        # Keep the response compact for the UI and the LLM.
        for ind in indicators:
            ind.series = ind.series[-30:]
        sources = [macro_source(i) for i in indicators]
        return AgentOutput(
            {"macro": MacroFindings(indicators=indicators, notes=notes), "sources": sources},
            f"Collected {len(indicators)} market & macro indicators",
        )
