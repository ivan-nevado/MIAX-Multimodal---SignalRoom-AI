from __future__ import annotations

import math

import pytest

from app.analytics import metrics as m
from tests.fakes import make_history


def test_percentage_change_and_log_return() -> None:
    assert m.percentage_change(100, 94) == pytest.approx(-6.0)
    assert m.percentage_change(0, 5) is None
    assert m.percentage_change(None, 5) is None
    assert m.log_return(100, 110) == pytest.approx(math.log(1.1))
    assert m.log_return(-1, 2) is None


def test_rolling_volatility_constant_growth_is_zero() -> None:
    closes = [100 * 1.01**i for i in range(30)]
    assert m.rolling_volatility(closes, 20) == pytest.approx(0.0, abs=1e-12)
    assert m.rolling_volatility(closes[:5], 20) is None


def test_rolling_volatility_annualised() -> None:
    closes = [100.0]
    for i in range(40):
        closes.append(closes[-1] * (1.02 if i % 2 else 0.98))
    daily = m.rolling_volatility(closes, 20, annualize=False)
    annual = m.rolling_volatility(closes, 20)
    assert daily is not None and annual is not None
    assert annual == pytest.approx(daily * math.sqrt(252))


def test_maximum_drawdown() -> None:
    assert m.maximum_drawdown([100, 120, 90, 110]) == pytest.approx(-25.0)
    assert m.maximum_drawdown([1, 2, 3]) == pytest.approx(0.0)
    assert m.maximum_drawdown([5]) is None


def test_volume_change_and_zscore_and_ma() -> None:
    vols = [100.0] * 20 + [300.0]
    assert m.volume_change(vols) == pytest.approx(200.0)
    assert m.volume_change([1.0, 2.0]) is None
    assert m.z_score(10, [1, 2, 3, 4, 5]) == pytest.approx((10 - 3) / 1.5811, rel=1e-3)
    assert m.z_score(1, [2, 2, 2, 2, 2]) is None
    assert m.moving_average([1, 2, 3, 4], 2) == pytest.approx(3.5)
    assert m.moving_average([1], 2) is None


def test_relative_and_sentiment_and_news_volume() -> None:
    assert m.relative_performance(-6.2, -1.2) == pytest.approx(-5.0)
    assert m.relative_performance(None, 1) is None
    recent, prior, change = m.sentiment_change([0.2, 0.2, 0.2, -0.4, -0.6], recent=2)
    assert recent == pytest.approx(-0.5) and prior == pytest.approx(0.2) and change == pytest.approx(-0.7)
    assert m.news_volume_change([10, 10, 10, 30]) == pytest.approx(200.0)


def test_anomaly_score_bounds() -> None:
    assert m.anomaly_score(None, 100) is None
    assert m.anomaly_score(6, 1000) == pytest.approx(1.0)
    assert 0 <= (m.anomaly_score(1, -50) or 0) <= 1


def test_compute_market_metrics_detects_unusual_move() -> None:
    history = make_history(last_move=-0.062, last_volume_mult=2.8)
    bench = make_history(last_move=-0.012, last_volume_mult=1.0, start=5000)
    metrics = m.compute_market_metrics(
        "NVDA", history, currency="USD", benchmark_symbol="^GSPC", benchmark_history=bench
    )
    assert metrics.move_pct == pytest.approx(-6.2, abs=0.01)
    assert metrics.volume_change_pct is not None and metrics.volume_change_pct > 100
    assert metrics.unusual_move is True
    assert metrics.relative_performance_pct == pytest.approx(-5.0, abs=0.05)
    assert metrics.volatility_20d is not None and metrics.volatility_20d > 0
    assert metrics.anomaly_score is not None and 0 <= metrics.anomaly_score <= 1
    assert any("fell" in o for o in metrics.observations)


def test_compute_market_metrics_insufficient_history() -> None:
    metrics = m.compute_market_metrics("X", make_history(days=1))
    assert metrics.move_pct is None
    assert metrics.observations
