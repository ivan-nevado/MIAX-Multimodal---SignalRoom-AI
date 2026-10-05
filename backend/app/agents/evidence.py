"""Research / Evidence Agent — scores likely drivers and links every claim to evidence.

Deterministic: driver contributions follow the documented formula in
app.analytics.scoring and are never produced by a model.
"""

from __future__ import annotations

from typing import Any

from app.agents.base import AgentContext, AgentOutput
from app.analytics.scoring import (
    DriverCandidate,
    candidates_from_clusters,
    evidence_confidence,
    market_pressure_candidate,
    score_drivers,
)
from app.schemas.agents import Claim, EvidenceFindings
from app.utils.ids import stable_id


def _confidence(n: int) -> str:
    return evidence_confidence(n)[0]


def build_claims(state: dict[str, Any]) -> list[Claim]:
    claims: list[Claim] = []
    market = state.get("market")
    if market is not None and market.metrics.move_pct is not None:
        m = market.metrics
        sid = market.source_ids[:1]
        direction = "rose" if m.move_pct and m.move_pct > 0 else "fell"
        claims.append(
            Claim(
                claim_id="c_move",
                claim=f"{m.symbol} {direction} {abs(m.move_pct or 0):.2f}% in the latest session ({m.as_of}).",
                claim_type="observed_fact",
                evidence_ids=sid,
                source_count=1,
                evidence_confidence="high",
            )
        )
        if m.volume_change_pct is not None:
            claims.append(
                Claim(
                    claim_id="c_volume",
                    claim=f"Volume was {m.volume_change_pct:+.0f}% versus its 20-session average.",
                    claim_type="derived_metric",
                    evidence_ids=sid,
                    source_count=1,
                    evidence_confidence="high",
                )
            )
        if m.zscore_move is not None:
            claims.append(
                Claim(
                    claim_id="c_zscore",
                    claim=f"The move is {m.zscore_move:+.1f} standard deviations versus the prior 60 sessions.",
                    claim_type="derived_metric",
                    evidence_ids=sid,
                    source_count=1,
                    evidence_confidence="high",
                )
            )
    news = state.get("news")
    if news is not None:
        for c in news.clusters:
            claims.append(
                Claim(
                    claim_id=stable_id("c", c.cluster_id),
                    claim=f"{c.theme}: {c.summary}" if c.summary else c.theme,
                    claim_type="interpretation",
                    evidence_ids=c.article_ids[:6],
                    source_count=c.source_count,
                    evidence_confidence=_confidence(c.source_count),
                )
            )
    for doc in state.get("documents") or []:
        for i, fact in enumerate(doc.key_facts[:5]):
            claims.append(
                Claim(
                    claim_id=stable_id("c", doc.upload_id, str(i)),
                    claim=f"{fact.fact}: {fact.value}" + (f" (page {fact.page})" if fact.page else ""),
                    claim_type="observed_fact",
                    evidence_ids=[doc.source_id] if doc.source_id else [],
                    source_count=1,
                    evidence_confidence="medium",
                )
            )
    for clip in state.get("audio") or []:
        if clip.analysis:
            for i, point in enumerate(clip.analysis.key_points[:3]):
                claims.append(
                    Claim(
                        claim_id=stable_id("c", clip.upload_id, str(i)),
                        claim=point,
                        claim_type="observed_fact",
                        evidence_ids=[clip.source_id] if clip.source_id else [],
                        source_count=1,
                        evidence_confidence="medium",
                    )
                )
    for vid in state.get("videos") or []:
        for i, point in enumerate(vid.key_points[:3]):
            claims.append(
                Claim(
                    claim_id=stable_id("c", vid.upload_id, str(i)),
                    claim=point,
                    claim_type="observed_fact",
                    evidence_ids=[vid.source_id] if vid.source_id else [],
                    source_count=1,
                    evidence_confidence="medium",
                )
            )
    return claims


class EvidenceAgent:
    name = "evidence"
    label = "Evidence Agent"

    async def run(self, state: dict[str, Any], ctx: AgentContext) -> AgentOutput:
        market = state.get("market")
        news = state.get("news")
        metrics = market.metrics if market is not None else None
        candidates: list[DriverCandidate] = []
        if news is not None and news.clusters:
            candidates += candidates_from_clusters(
                news.clusters,
                metrics.move_pct if metrics else None,
                metrics.as_of if metrics else None,
                {c.cluster_id: c.article_ids[:6] for c in news.clusters},
            )
        pressure = market_pressure_candidate(metrics, market.source_ids if market else [])
        if pressure:
            candidates.append(pressure)
        for doc in state.get("documents") or []:
            candidates.append(
                DriverCandidate(
                    driver_id=f"drv_doc_{doc.upload_id}",
                    name=f"Company disclosure ({doc.filename})",
                    category="filing",
                    relevance=0.8,
                    source_support=0.5,
                    temporal_alignment=0.8,
                    sentiment_factor=1.0,
                    evidence_ids=[doc.source_id] if doc.source_id else [],
                )
            )
        for clip in state.get("audio") or []:
            if clip.analysis:
                candidates.append(
                    DriverCandidate(
                        driver_id=f"drv_audio_{clip.upload_id}",
                        name=f"Management commentary ({clip.filename})",
                        category="earnings",
                        relevance=0.8,
                        source_support=0.5,
                        temporal_alignment=0.8,
                        sentiment_factor=1.0,
                        evidence_ids=[clip.source_id] if clip.source_id else [],
                    )
                )
        for vid in state.get("videos") or []:
            if vid.key_points or vid.guidance:
                candidates.append(
                    DriverCandidate(
                        driver_id=f"drv_video_{vid.upload_id}",
                        name=f"Management presentation ({vid.filename})",
                        category="earnings",
                        relevance=0.8,
                        source_support=0.5,
                        temporal_alignment=0.8,
                        sentiment_factor=1.0,
                        evidence_ids=[vid.source_id] if vid.source_id else [],
                    )
                )
        drivers = score_drivers(candidates)
        claims = build_claims(state)
        independent = len({a.publisher for a in news.articles}) if news is not None else 0
        independent += (
            len(state.get("documents") or []) + len(state.get("audio") or []) + len(state.get("videos") or [])
        )
        cross_checked = len({e for c in claims for e in c.evidence_ids})
        return AgentOutput(
            {"evidence": EvidenceFindings(drivers=drivers, claims=claims, independent_sources=independent)},
            f"Cross-checked {cross_checked} supporting sources; scored {len(drivers)} likely drivers",
        )
