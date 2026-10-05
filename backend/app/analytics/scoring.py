"""Evidence-weighted driver score — a transparent heuristic, NOT a probability or causal estimate.

For every candidate driver d (a news cluster, broad market pressure, or an uploaded disclosure):

    raw(d) = relevance(d) × source_support(d) × temporal_alignment(d) × sentiment_factor(d)

    relevance          ∈ [0,1]  mean deterministic relevance of the cluster's articles
                                (entity mention in headline, recency, finance keywords)
    source_support     ∈ [0,1]  1 − exp(−independent_publishers / 3)   (1 pub ≈ 0.28, 3 ≈ 0.63, 7 ≈ 0.90)
    temporal_alignment ∈ [0.2,1] 1.0 if first seen within 36h before (or 24h after) the latest session,
                                 then exponential decay exp(−Δh / 72)
    sentiment_factor   ∈ [0.75,1.25] 1 + 0.25 × alignment, alignment = sign(tone) agrees with
                                 sign(price move) × min(1, |tone| / 0.5)  (tone is the headline-tone label)

    contribution(d) = raw(d) / Σ raw × 100     (top 4 drivers, drivers < 5% dropped, then renormalised)

Market/sector pressure uses relevance = min(1, |benchmark move| / |asset move|) × 0.6 with
source_support = temporal_alignment = 1 when the benchmark moved in the same direction.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field

from app.schemas.agents import Driver, DriverComponents, MarketMetrics, NewsCluster
from app.utils.time import parse_iso

MIN_SHARE_PCT = 5.0
MAX_DRIVERS = 4


@dataclass
class DriverCandidate:
    driver_id: str
    name: str
    category: str
    relevance: float
    source_support: float
    temporal_alignment: float
    sentiment_factor: float
    evidence_ids: list[str] = field(default_factory=list)

    @property
    def raw(self) -> float:
        return self.relevance * self.source_support * self.temporal_alignment * self.sentiment_factor


def source_support(independent_publishers: int) -> float:
    return round(1.0 - math.exp(-max(independent_publishers, 0) / 3.0), 4)


def temporal_alignment(first_seen_iso: str | None, move_time_iso: str | None) -> float:
    first_seen, move_time = parse_iso(first_seen_iso), parse_iso(move_time_iso)
    if first_seen is None or move_time is None:
        return 0.6
    # Daily bars are stamped at midnight: treat the session as the whole day.
    delta_h = (move_time - first_seen).total_seconds() / 3600.0
    if -48.0 <= delta_h <= 36.0:
        return 1.0
    gap = abs(delta_h) - 36.0 if delta_h > 0 else abs(delta_h) - 48.0
    return round(max(math.exp(-gap / 72.0), 0.2), 4)


def sentiment_factor(tone: float | None, move_pct: float | None) -> float:
    if tone is None or move_pct is None or move_pct == 0 or tone == 0:
        return 1.0
    agrees = (tone > 0) == (move_pct > 0)
    magnitude = min(abs(tone) / 0.5, 1.0)
    alignment = magnitude if agrees else -magnitude
    return round(1.0 + 0.25 * alignment, 4)


def candidates_from_clusters(
    clusters: Sequence[NewsCluster],
    move_pct: float | None,
    move_time_iso: str | None,
    source_ids_by_cluster: dict[str, list[str]],
) -> list[DriverCandidate]:
    out: list[DriverCandidate] = []
    for c in clusters:
        out.append(
            DriverCandidate(
                driver_id=f"drv_{c.cluster_id}",
                name=c.theme,
                category=c.event_type,
                relevance=c.relevance,
                source_support=source_support(c.source_count),
                temporal_alignment=temporal_alignment(c.first_seen, move_time_iso),
                sentiment_factor=sentiment_factor(c.tone, move_pct),
                evidence_ids=source_ids_by_cluster.get(c.cluster_id, []),
            )
        )
    return out


def market_pressure_candidate(
    metrics: MarketMetrics | None, evidence_ids: list[str]
) -> DriverCandidate | None:
    if metrics is None or metrics.move_pct is None or metrics.benchmark_move_pct is None:
        return None
    if abs(metrics.move_pct) < 0.3 or metrics.move_pct * metrics.benchmark_move_pct <= 0:
        return None
    share = min(abs(metrics.benchmark_move_pct) / abs(metrics.move_pct), 1.0)
    return DriverCandidate(
        driver_id="drv_market_pressure",
        name="Broad market / sector pressure",
        category="sector_move",
        relevance=round(share * 0.6, 4),
        source_support=1.0,
        temporal_alignment=1.0,
        sentiment_factor=1.0,
        evidence_ids=evidence_ids,
    )


def score_drivers(candidates: Sequence[DriverCandidate]) -> list[Driver]:
    ranked = sorted((c for c in candidates if c.raw > 0), key=lambda c: c.raw, reverse=True)[:MAX_DRIVERS]
    total = sum(c.raw for c in ranked)
    if total <= 0:
        return []
    shares = [(c, c.raw / total * 100.0) for c in ranked]
    kept = [(c, s) for c, s in shares if s >= MIN_SHARE_PCT]
    total_kept = sum(c.raw for c, _ in kept)
    drivers: list[Driver] = []
    for c, _ in kept:
        drivers.append(
            Driver(
                driver_id=c.driver_id,
                name=c.name,
                category=c.category,
                contribution_score=round(c.raw / total_kept * 100.0, 1),
                raw_score=round(c.raw, 4),
                components=DriverComponents(
                    relevance=round(c.relevance, 3),
                    source_support=round(c.source_support, 3),
                    temporal_alignment=round(c.temporal_alignment, 3),
                    sentiment_shift=round((c.sentiment_factor - 0.75) / 0.5, 3),
                ),
                evidence_ids=c.evidence_ids,
            )
        )
    _fix_rounding(drivers)
    return drivers


def _fix_rounding(drivers: list[Driver]) -> None:
    """Make the displayed percentages add up to exactly 100.0."""
    if not drivers:
        return
    diff = round(100.0 - sum(d.contribution_score for d in drivers), 1)
    if diff:
        drivers[0].contribution_score = round(drivers[0].contribution_score + diff, 1)


def evidence_confidence(independent_sources: int, agreement: str = "aligned") -> tuple[str, str]:
    """Coverage/agreement based label — explicitly not a probability."""
    if independent_sources >= 5 and agreement in ("aligned", "unknown"):
        return "high", f"{independent_sources} independent relevant sources discuss the same events."
    if independent_sources >= 2:
        reason = f"{independent_sources} independent sources"
        if agreement in ("mixed", "divergent"):
            reason += f", with {agreement} tone across them"
        return "medium", reason + "."
    if independent_sources == 1:
        return "low", "Only one source supports this."
    return "low", "No supporting source was found."
