"""Risk Agent — qualitative LOW/MEDIUM/HIGH risks grounded in cited evidence ids."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.agents.base import AgentContext, AgentOutput
from app.agents.evidence_pack import build_evidence_pack, known_evidence_ids
from app.agents.guardrails import clean_narrative, filter_ids
from app.integrations.ai.base import AIError
from app.prompts.loader import system_prompt
from app.schemas.agents import RiskFindings, RiskItem, RiskLLMOutput
from app.skills.loader import load_reference

logger = logging.getLogger(__name__)


def cluster_to_source_ids(state: dict[str, Any]) -> dict[str, list[str]]:
    news = state.get("news")
    return {c.cluster_id: c.article_ids[:4] for c in news.clusters} if news is not None else {}


def rule_based_risks(state: dict[str, Any]) -> list[RiskItem]:
    """Deterministic fallback following references/risk-framework.md (market row)."""
    risks: list[RiskItem] = []
    market = state.get("market")
    if market is not None:
        m = market.metrics
        sid = market.source_ids[:1]
        vol = m.volatility_20d or 0
        z = abs(m.zscore_move or 0)
        if vol > 0.6 or z >= 3:
            risks.append(
                RiskItem(
                    risk="market",
                    level="HIGH",
                    reason=f"20-day annualised volatility is {vol:.0%} and the latest move is {z:.1f}σ.",
                    evidence_ids=sid,
                )
            )
        elif vol > 0.35 or z >= 2:
            risks.append(
                RiskItem(
                    risk="market",
                    level="MEDIUM",
                    reason=f"20-day annualised volatility is {vol:.0%}.",
                    evidence_ids=sid,
                )
            )
        else:
            risks.append(
                RiskItem(
                    risk="market",
                    level="LOW",
                    reason="Volatility and the latest move are within normal ranges.",
                    evidence_ids=sid,
                )
            )
    news = state.get("news")
    if news is not None:
        for c in news.clusters:
            if c.event_type in ("regulation", "lawsuit") and c.source_count >= 2:
                risks.append(
                    RiskItem(
                        risk="regulatory" if c.event_type == "regulation" else "governance",
                        level="HIGH" if c.source_count >= 4 else "MEDIUM",
                        reason=f"{c.source_count} publishers report: {c.theme}.",
                        evidence_ids=c.article_ids[:3],
                    )
                )
    return risks


class RiskAgent:
    name = "risk"
    label = "Risk Agent"

    async def run(self, state: dict[str, Any], ctx: AgentContext) -> AgentOutput:
        items: list[RiskItem]
        if ctx.ai.available("reasoning"):
            pack = build_evidence_pack(state)
            try:
                out = await ctx.ai.structured(
                    RiskLLMOutput,
                    system=system_prompt("risk_agent", "risk_analysis")
                    + "\n\n"
                    + load_reference("risk_analysis", "risk-framework.md"),
                    user=json.dumps(
                        {"asset": state.get("symbol"), "question": state["question"], "evidence": pack},
                        default=str,
                    ),
                    agent=self.name,
                    purpose="risk_assessment",
                    max_tokens=1600,
                )
                items = self._validate(out.items, state)
            except AIError as exc:
                logger.warning("risk_llm_failed", extra={"error_type": type(exc).__name__})
                items = rule_based_risks(state)
        else:
            items = rule_based_risks(state)
        order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        items.sort(key=lambda r: order[r.level])
        high = sum(1 for r in items if r.level == "HIGH")
        return AgentOutput(
            {"risks": RiskFindings(items=items)},
            f"Identified {len(items)} risk themes ({high} high)",
        )

    @staticmethod
    def _validate(items: list[RiskItem], state: dict[str, Any]) -> list[RiskItem]:
        known = known_evidence_ids(state)
        clusters = cluster_to_source_ids(state)
        valid: list[RiskItem] = []
        for item in items:
            # A cluster id expands to its article source ids so the UI can open real links.
            expanded: list[str] = []
            for eid in item.evidence_ids:
                expanded.extend(clusters.get(eid, [eid]))
            ids = filter_ids(expanded, known)
            if not ids:
                continue  # unsupported risk → dropped
            valid.append(
                item.model_copy(update={"evidence_ids": ids, "reason": clean_narrative(item.reason)})
            )
        return valid[:6]
