"""Orchestrator Agent — decides the minimal set of agents for a question.

The LLM proposes a plan; deterministic rules then enforce hard constraints
(attachments must be analysed, evidence+synthesis always run, agents that cannot
apply to the asset type are removed). Without an LLM the rule-based plan is used.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.agents.base import AgentContext, AgentOutput
from app.integrations.ai.base import AIError
from app.prompts.loader import system_prompt
from app.schemas.agents import AgentPlan

logger = logging.getLogger(__name__)

PLANNABLE = [
    "market",
    "news",
    "financial",
    "macro",
    "document",
    "vision",
    "audio",
    "video",
    "sentiment",
    "event_detection",
    "risk",
    "evidence",
    "synthesis",
]
NON_FUNDAMENTAL_TYPES = {"crypto", "fx", "commodity", "index"}

# Minimum team per intent: the LLM may add agents but cannot drop these (core product quality).
INTENT_MINIMUM: dict[str, tuple[str, ...]] = {
    "why_move": ("market", "news", "financial", "macro", "sentiment", "event_detection", "risk"),
    "earnings_review": ("market", "financial", "sentiment", "event_detection", "risk"),
    "document_review": ("market", "financial", "risk"),
    "chart_review": ("market",),
    "general_research": ("market", "news", "financial", "risk"),
}

_EARNINGS_RE = re.compile(r"earnings|results|guidance|call|thesis|quarter|report", re.I)
_CHART_RE = re.compile(r"chart|screenshot|image|graph|technical", re.I)
_DOC_RE = re.compile(r"pdf|document|filing|annual report|10-k|10-q|presentation", re.I)


def rule_based_plan(question: str, asset_type: str | None, has_symbol: bool, kinds: set[str]) -> AgentPlan:
    if "audio" in kinds or "video" in kinds or ("document" in kinds and _EARNINGS_RE.search(question)):
        intent = "earnings_review"
    elif "image" in kinds and (_CHART_RE.search(question) or not has_symbol):
        intent = "chart_review"
    elif "document" in kinds and _DOC_RE.search(question):
        intent = "document_review"
    elif has_symbol:
        intent = "why_move"
    else:
        intent = "general_research"

    agents = list(INTENT_MINIMUM[intent])
    plan = AgentPlan(intent=intent, agents=agents, rationale="Rule-based plan.", time_window_days=7)
    return enforce_constraints(plan, asset_type, has_symbol, kinds)


def enforce_constraints(
    plan: AgentPlan, asset_type: str | None, has_symbol: bool, kinds: set[str]
) -> AgentPlan:
    agents = [a for a in plan.agents if a in PLANNABLE]
    agents += [a for a in INTENT_MINIMUM.get(plan.intent, ()) if a not in agents]
    for kind, agent in (
        ("document", "document"),
        ("image", "vision"),
        ("audio", "audio"),
        ("video", "video"),
    ):
        if kind in kinds and agent not in agents:
            agents.append(agent)
        if kind not in kinds and agent in agents:
            agents.remove(agent)
    if not has_symbol:
        agents = [a for a in agents if a not in ("market", "financial", "news", "macro")]
    if asset_type in NON_FUNDAMENTAL_TYPES and "financial" in agents:
        agents.remove("financial")
    if (
        "sentiment" in agents
        and "news" not in agents
        and "audio" not in agents
        and "video" not in agents
        and "document" not in agents
    ):
        agents.remove("sentiment")
    for required in ("evidence", "synthesis"):
        if required not in agents:
            agents.append(required)
    ordered = [a for a in PLANNABLE if a in agents]
    return plan.model_copy(update={"agents": ordered})


class OrchestratorAgent:
    name = "orchestrator"
    label = "Orchestrator"

    async def run(self, state: dict[str, Any], ctx: AgentContext) -> AgentOutput:
        kinds = {a.kind for a in state.get("attachments", [])}
        has_symbol = bool(state.get("symbol"))
        asset_type = state.get("asset_type")
        fallback = rule_based_plan(state["question"], asset_type, has_symbol, kinds)
        if not ctx.ai.available("reasoning"):
            return AgentOutput({"plan": fallback}, f"Planned {len(fallback.agents)} agents (rule-based)")
        payload = {
            "asset": {"symbol": state.get("symbol"), "name": state.get("asset_name"), "type": asset_type},
            "question": state["question"],
            "attachments": sorted(kinds),
        }
        try:
            proposed = await ctx.ai.structured(
                AgentPlan,
                system=system_prompt("orchestrator"),
                user=json.dumps(payload),
                agent=self.name,
                purpose="plan",
                max_tokens=600,
            )
            plan = enforce_constraints(proposed, asset_type, has_symbol, kinds)
        except AIError as exc:
            logger.warning("orchestrator_llm_failed", extra={"error_type": type(exc).__name__})
            plan = fallback
        names = ", ".join(a for a in plan.agents if a not in ("evidence", "synthesis"))
        return AgentOutput({"plan": plan}, f"Assembled research team: {names or 'synthesis only'}")
