from __future__ import annotations

from datetime import timedelta

import pytest

from app.analytics import scoring as s
from app.schemas.agents import MarketMetrics, NewsCluster
from tests.fakes import NOW


def test_source_support_saturates() -> None:
    assert s.source_support(0) == 0
    assert s.source_support(1) == pytest.approx(0.2835, abs=1e-3)
    assert s.source_support(7) > 0.89
    assert s.source_support(20) < 1


def test_temporal_alignment_window_and_decay() -> None:
    move = NOW.isoformat()
    assert s.temporal_alignment((NOW - timedelta(hours=10)).isoformat(), move) == 1.0
    assert s.temporal_alignment((NOW + timedelta(hours=20)).isoformat(), move) == 1.0
    old = s.temporal_alignment((NOW - timedelta(days=10)).isoformat(), move)
    assert 0.2 <= old < 1.0
    assert s.temporal_alignment(None, move) == 0.6


def test_sentiment_factor_alignment() -> None:
    assert s.sentiment_factor(-0.8, -6) == pytest.approx(1.25)
    assert s.sentiment_factor(0.8, -6) == pytest.approx(0.75)
    assert s.sentiment_factor(None, -6) == 1.0
    assert s.sentiment_factor(-0.25, -1) == pytest.approx(1.125)


def _cluster(cid: str, sources: int, rel: float, tone: float) -> NewsCluster:
    return NewsCluster(
        cluster_id=cid,
        theme=cid,
        relevance=rel,
        tone=tone,
        source_count=sources,
        first_seen=(NOW - timedelta(hours=5)).isoformat(),
        article_ids=[f"{cid}_a"],
    )


def test_score_drivers_sums_to_100_and_ranks_by_evidence() -> None:
    clusters = [
        _cluster("export", 5, 0.9, -0.7),
        _cluster("valuation", 2, 0.8, -0.3),
        _cluster("noise", 1, 0.2, 0.1),
    ]
    candidates = s.candidates_from_clusters(
        clusters, -6.2, NOW.isoformat(), {c.cluster_id: c.article_ids for c in clusters}
    )
    drivers = s.score_drivers(candidates)
    assert drivers[0].name == "export"
    assert sum(d.contribution_score for d in drivers) == pytest.approx(100.0)
    assert all(d.components is not None for d in drivers)
    assert all(d.contribution_score >= s.MIN_SHARE_PCT for d in drivers)


def test_score_drivers_empty() -> None:
    assert s.score_drivers([]) == []


def test_market_pressure_only_when_same_direction() -> None:
    same = MarketMetrics(symbol="NVDA", move_pct=-6.0, benchmark_move_pct=-1.5)
    opposite = MarketMetrics(symbol="NVDA", move_pct=-6.0, benchmark_move_pct=1.5)
    cand = s.market_pressure_candidate(same, ["src"])
    assert cand is not None and cand.relevance == pytest.approx(0.15)
    assert s.market_pressure_candidate(opposite, ["src"]) is None
    assert s.market_pressure_candidate(None, []) is None


def test_evidence_confidence_is_coverage_based() -> None:
    assert s.evidence_confidence(7)[0] == "high"
    assert s.evidence_confidence(7, "divergent")[0] == "medium"
    assert s.evidence_confidence(1)[0] == "low"
    assert "No supporting source" in s.evidence_confidence(0)[1]
