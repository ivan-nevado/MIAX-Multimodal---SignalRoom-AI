"""Assemble the final InvestigationResult from the graph state (deterministic data + validated narrative)."""

from __future__ import annotations

from typing import Any

from app.agents.synthesis import merge_claims, merge_drivers
from app.schemas.agents import EvidenceFindings, SynthesisOutput
from app.schemas.common import ModelUsage
from app.schemas.investigations import InvestigationResult
from app.utils.time import utc_now_iso


def build_result(state: dict[str, Any], usage: list[ModelUsage]) -> InvestigationResult:
    synthesis: SynthesisOutput | None = state.get("synthesis")
    evidence: EvidenceFindings = state.get("evidence") or EvidenceFindings()
    plan = state.get("plan")
    drivers = merge_drivers(evidence.drivers, synthesis)
    claims = merge_claims(evidence.claims, synthesis, state)
    cited = {e for d in drivers for e in d.evidence_ids} | {e for c in claims for e in c.evidence_ids}
    risks = state.get("risks")
    if risks is not None:
        cited |= {e for r in risks.items for e in r.evidence_ids}
    sources = sorted(
        state.get("sources") or [],
        key=lambda s: (s.id not in cited, s.source_type != "market_data", -s.relevance),
    )
    return InvestigationResult(
        symbol=state.get("symbol"),
        asset_name=state.get("asset_name"),
        question=state["question"],
        intent=plan.intent if plan else "general_research",
        executive_summary=synthesis.executive_summary if synthesis else "Not enough evidence available.",
        what_happened=synthesis.what_happened if synthesis else "",
        drivers=drivers,
        market_context=synthesis.market_context if synthesis else "",
        financial_context=synthesis.financial_context if synthesis else "",
        sentiment_summary=synthesis.sentiment_summary if synthesis else "",
        risk_summary=synthesis.risk_summary if synthesis else "",
        what_to_watch=synthesis.what_to_watch if synthesis else [],
        uncertainties=synthesis.uncertainties if synthesis else [],
        claims=claims,
        market=state.get("market"),
        news=state.get("news"),
        sentiment=state.get("sentiment"),
        events=state.get("events"),
        financial=state.get("financial"),
        macro=state.get("macro"),
        risks=risks,
        documents=state.get("documents") or [],
        images=state.get("images") or [],
        audio=state.get("audio") or [],
        videos=state.get("videos") or [],
        sources=sources,
        agent_runs=state.get("agent_runs") or [],
        model_usage=usage,
        warnings=list(dict.fromkeys(state.get("warnings") or [])),
        ai_narrative_available=state.get("ai_narrative_available", True) is not False
        and synthesis is not None,
        generated_at=utc_now_iso(),
    )
