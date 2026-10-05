"""Synthesis Agent — the "investment committee": reconciles specialist outputs into the final brief.

The model writes narrative only. Numbers, driver scores and sources come from the
deterministic agents; unknown evidence ids are stripped and unsupported factual
claims are dropped (interpretations without evidence become hypotheses).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.agents.base import AgentContext, AgentOutput
from app.agents.evidence_pack import build_evidence_pack, known_evidence_ids
from app.agents.guardrails import clean_narrative, filter_ids
from app.integrations.ai.base import AIError
from app.prompts.loader import system_prompt
from app.schemas.agents import Claim, Driver, EvidenceFindings, SynthesisOutput
from app.utils.ids import stable_id

logger = logging.getLogger(__name__)


def deterministic_synthesis(state: dict[str, Any]) -> SynthesisOutput:
    """Used when no LLM is available: factual, template-based, clearly labelled by the caller."""
    market = state.get("market")
    evidence: EvidenceFindings | None = state.get("evidence")
    obs = market.metrics.observations if market is not None else []
    drivers = evidence.drivers if evidence else []
    names = ", ".join(f"{d.name} ({d.contribution_score:.0f}%)" for d in drivers[:3])
    summary = " ".join(obs[:2]) or "Not enough market data available."
    if names:
        summary += f" Evidence-weighted likely drivers: {names}."
    return SynthesisOutput(
        executive_summary=summary,
        what_happened=" ".join(obs) or "Not enough evidence available.",
        market_context="",
        what_to_watch=[],
        uncertainties=[
            "AI narrative unavailable: this summary was generated from deterministic metrics only."
        ],
    )


class SynthesisAgent:
    name = "synthesis"
    label = "Synthesis Agent"

    async def run(self, state: dict[str, Any], ctx: AgentContext) -> AgentOutput:
        evidence: EvidenceFindings = state.get("evidence") or EvidenceFindings()
        if not ctx.ai.available("reasoning"):
            return AgentOutput(
                {"synthesis": deterministic_synthesis(state), "ai_narrative_available": False},
                "Generated deterministic summary (AI narrative unavailable)",
            )
        payload = {
            "question": state["question"],
            "asset": {
                "symbol": state.get("symbol"),
                "name": state.get("asset_name"),
                "type": state.get("asset_type"),
            },
            "intent": state["plan"].intent if state.get("plan") else None,
            "drivers": [
                {
                    "driver_id": d.driver_id,
                    "name": d.name,
                    "category": d.category,
                    "evidence_weighted_contribution_pct": d.contribution_score,
                    "evidence_ids": d.evidence_ids,
                }
                for d in evidence.drivers
            ],
            "evidence": build_evidence_pack(state),
            "risks": [r.model_dump() for r in (state["risks"].items if state.get("risks") else [])],
            "events": [
                e.model_dump(include={"timestamp", "title", "event_type"})
                for e in (state["events"].events if state.get("events") else [])
            ][-10:],
            "baseline_claims": [
                c.model_dump(include={"claim_id", "claim", "claim_type", "evidence_ids"})
                for c in evidence.claims[:12]
            ],
            "warnings": state.get("warnings", []),
        }
        try:
            out = await ctx.ai.structured(
                SynthesisOutput,
                system=system_prompt("synthesis_agent", "market_analysis", "financial_analysis"),
                user=json.dumps(payload, default=str),
                agent=self.name,
                purpose="synthesis",
                max_tokens=3500,
                temperature=0.25,
            )
        except AIError as exc:
            logger.error("synthesis_failed", extra={"error_type": type(exc).__name__})
            return AgentOutput(
                {"synthesis": deterministic_synthesis(state), "ai_narrative_available": False},
                "Synthesis model unavailable — generated deterministic summary",
                ["AI narrative unavailable for this investigation."],
            )
        return AgentOutput({"synthesis": self._guard(out)}, "Generated final explanation")

    @staticmethod
    def _guard(out: SynthesisOutput) -> SynthesisOutput:
        for field in (
            "executive_summary",
            "what_happened",
            "market_context",
            "financial_context",
            "sentiment_summary",
            "risk_summary",
        ):
            setattr(out, field, clean_narrative(getattr(out, field)))
        out.what_to_watch = [clean_narrative(w) for w in out.what_to_watch if w.strip()][:5]
        out.uncertainties = [clean_narrative(u) for u in out.uncertainties if u.strip()][:6]
        for d in out.drivers:
            d.explanation = clean_narrative(d.explanation)
        return out


def merge_drivers(drivers: list[Driver], synthesis: SynthesisOutput | None) -> list[Driver]:
    """Attach model explanations to deterministic drivers (scores are never taken from the model)."""
    explanations = {d.driver_id: d.explanation for d in (synthesis.drivers if synthesis else [])}
    return [
        d.model_copy(update={"explanation": explanations.get(d.driver_id, d.explanation)}) for d in drivers
    ]


def merge_claims(
    baseline: list[Claim], synthesis: SynthesisOutput | None, state: dict[str, Any]
) -> list[Claim]:
    """Combine deterministic claims with validated model claims (no unsupported factual claims)."""
    known = known_evidence_ids(state)
    news = state.get("news")
    cluster_map = {c.cluster_id: c.article_ids[:4] for c in news.clusters} if news is not None else {}
    merged = list(baseline)
    for i, c in enumerate(synthesis.claims if synthesis else []):
        expanded: list[str] = []
        for eid in c.evidence_ids:
            expanded.extend(cluster_map.get(eid, [eid]))
        ids = filter_ids(expanded, known)
        claim_type = c.claim_type
        if not ids:
            if claim_type in ("observed_fact", "derived_metric"):
                continue  # unsupported factual claim → dropped
            claim_type = "hypothesis"
        merged.append(
            Claim(
                claim_id=stable_id("cs", str(i), c.claim),
                claim=clean_narrative(c.claim),
                claim_type=claim_type,
                evidence_ids=ids,
                source_count=len(ids),
                evidence_confidence="high" if len(ids) >= 5 else "medium" if len(ids) >= 2 else "low",
            )
        )
    return merged
