"""Deterministic financial calculations.

The LLM never computes statistics: it only interprets the structured output of
these functions. All functions are pure and unit tested.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np
import pandas as pd

from app.schemas.agents import MarketMetrics, PricePoint

TRADING_DAYS = 252


def _clean(values: Sequence[float | None] | np.ndarray) -> np.ndarray:
    arr = np.array([np.nan if v is None else float(v) for v in values], dtype=float)
    return arr[~np.isnan(arr)]


def percentage_change(old: float | None, new: float | None) -> float | None:
    if old is None or new is None or old == 0 or math.isnan(old) or math.isnan(new):
        return None
    return (new - old) / abs(old) * 100.0


def log_return(old: float | None, new: float | None) -> float | None:
    if old is None or new is None or old <= 0 or new <= 0:
        return None
    return math.log(new / old)


def daily_log_returns(closes: Sequence[float]) -> np.ndarray:
    arr = _clean(closes)
    if arr.size < 2 or np.any(arr <= 0):
        return np.array([], dtype=float)
    return np.diff(np.log(arr))


def rolling_volatility(closes: Sequence[float], window: int = 20, annualize: bool = True) -> float | None:
    """Standard deviation of the last `window` daily log returns (annualised by sqrt(252))."""
    rets = daily_log_returns(closes)
    if rets.size < max(2, window):
        return None
    vol = float(np.std(rets[-window:], ddof=1))
    return vol * math.sqrt(TRADING_DAYS) if annualize else vol


def maximum_drawdown(closes: Sequence[float]) -> float | None:
    """Most negative peak-to-trough decline, in percent (e.g. -8.4)."""
    arr = _clean(closes)
    if arr.size < 2:
        return None
    running_max = np.maximum.accumulate(arr)
    drawdowns = (arr - running_max) / running_max
    return float(drawdowns.min() * 100.0)


def volume_change(volumes: Sequence[float | None], window: int = 20) -> float | None:
    """Last volume vs the average of the previous `window` sessions, in percent."""
    arr = _clean(volumes)
    if arr.size < window + 1:
        return None
    baseline = float(np.mean(arr[-window - 1 : -1]))
    if baseline <= 0:
        return None
    return (float(arr[-1]) - baseline) / baseline * 100.0


def z_score(value: float | None, sample: Sequence[float] | np.ndarray) -> float | None:
    arr = _clean(sample)
    if value is None or arr.size < 5:
        return None
    std = float(np.std(arr, ddof=1))
    if std == 0:
        return None
    return (value - float(np.mean(arr))) / std


def moving_average(values: Sequence[float], window: int) -> float | None:
    arr = _clean(values)
    if arr.size < window:
        return None
    return float(np.mean(arr[-window:]))


def relative_performance(asset_move_pct: float | None, benchmark_move_pct: float | None) -> float | None:
    if asset_move_pct is None or benchmark_move_pct is None:
        return None
    return asset_move_pct - benchmark_move_pct


def sentiment_change(
    tones: Sequence[float], recent: int = 2
) -> tuple[float | None, float | None, float | None]:
    """Return (recent_mean, prior_mean, change) for a tone series ordered oldest→newest."""
    arr = _clean(tones)
    if arr.size < recent + 1:
        return (float(np.mean(arr)) if arr.size else None, None, None)
    recent_mean = float(np.mean(arr[-recent:]))
    prior_mean = float(np.mean(arr[:-recent]))
    return recent_mean, prior_mean, recent_mean - prior_mean


def news_volume_change(volumes: Sequence[float], recent: int = 1) -> float | None:
    arr = _clean(volumes)
    if arr.size < recent + 2:
        return None
    baseline = float(np.mean(arr[:-recent]))
    if baseline <= 0:
        return None
    return (float(np.mean(arr[-recent:])) - baseline) / baseline * 100.0


def anomaly_score(zscore_move: float | None, volume_change_pct: float | None) -> float | None:
    """Heuristic 0-1 score: how unusual today's session is (price z-score blended with volume)."""
    if zscore_move is None:
        return None
    price_part = min(abs(zscore_move) / 3.0, 1.0)
    volume_part = 0.0 if volume_change_pct is None else min(max(volume_change_pct, 0.0) / 200.0, 1.0)
    return round(0.7 * price_part + 0.3 * volume_part, 3)


def history_to_frame(points: Sequence[PricePoint]) -> pd.DataFrame:
    frame = pd.DataFrame([p.model_dump() for p in points])
    if frame.empty:
        return frame
    return frame.sort_values("time").reset_index(drop=True)


def _r(value: float | None, digits: int = 2) -> float | None:
    return None if value is None or math.isnan(value) else round(value, digits)


def compute_market_metrics(
    symbol: str,
    history: Sequence[PricePoint],
    *,
    currency: str | None = None,
    benchmark_symbol: str | None = None,
    benchmark_history: Sequence[PricePoint] | None = None,
) -> MarketMetrics:
    """Compute every market metric the Market Agent reports from daily OHLCV bars."""
    closes = [p.close for p in history]
    volumes = [p.volume for p in history]
    metrics = MarketMetrics(symbol=symbol, currency=currency, benchmark_symbol=benchmark_symbol)
    if len(closes) < 2:
        metrics.observations.append("Not enough price history to compute metrics.")
        return metrics

    last, prev = closes[-1], closes[-2]
    metrics.as_of = history[-1].time
    metrics.last_price = _r(last, 4)
    metrics.previous_close = _r(prev, 4)
    metrics.day_high = _r(history[-1].high, 4)
    metrics.day_low = _r(history[-1].low, 4)
    metrics.volume = volumes[-1]
    metrics.move_pct = _r(percentage_change(prev, last))
    if len(closes) > 5:
        metrics.return_5d_pct = _r(percentage_change(closes[-6], last))
    if len(closes) > 21:
        metrics.return_1m_pct = _r(percentage_change(closes[-22], last))
    vol_values = [v for v in volumes if v is not None]
    if vol_values and len(vol_values) > 20:
        metrics.avg_volume_20d = _r(float(np.mean(vol_values[-21:-1])), 0)
    metrics.volume_change_pct = _r(volume_change(volumes))
    metrics.volatility_20d = _r(rolling_volatility(closes, 20), 4)
    metrics.drawdown_30d = _r(maximum_drawdown(closes[-30:]))
    metrics.ma_20 = _r(moving_average(closes, 20), 4)
    metrics.ma_50 = _r(moving_average(closes, 50), 4)

    rets = daily_log_returns(closes)
    if rets.size > 10:
        metrics.zscore_move = _r(z_score(float(rets[-1]), rets[-61:-1]))
    metrics.anomaly_score = anomaly_score(metrics.zscore_move, metrics.volume_change_pct)
    metrics.unusual_move = bool(
        (metrics.zscore_move is not None and abs(metrics.zscore_move) >= 2.0)
        or (metrics.volume_change_pct is not None and metrics.volume_change_pct >= 100)
    )

    if benchmark_history and len(benchmark_history) >= 2:
        bench_move = percentage_change(benchmark_history[-2].close, benchmark_history[-1].close)
        metrics.benchmark_move_pct = _r(bench_move)
        metrics.relative_performance_pct = _r(relative_performance(metrics.move_pct, bench_move))

    metrics.observations = describe_metrics(metrics)
    return metrics


def describe_metrics(m: MarketMetrics) -> list[str]:
    """Rule-based, factual observations derived from the metrics (no LLM)."""
    obs: list[str] = []
    if m.move_pct is not None:
        direction = "rose" if m.move_pct > 0 else "fell" if m.move_pct < 0 else "was flat"
        obs.append(f"{m.symbol} {direction} {abs(m.move_pct):.2f}% in the latest session.")
    if m.zscore_move is not None and abs(m.zscore_move) >= 2:
        obs.append(
            f"The move is {abs(m.zscore_move):.1f} standard deviations from its recent average — unusual."
        )
    if m.volume_change_pct is not None and abs(m.volume_change_pct) >= 50:
        word = "above" if m.volume_change_pct > 0 else "below"
        obs.append(f"Volume was {abs(m.volume_change_pct):.0f}% {word} its 20-session average.")
    if m.relative_performance_pct is not None and m.benchmark_symbol:
        word = "outperformed" if m.relative_performance_pct > 0 else "underperformed"
        obs.append(
            f"It {word} its benchmark ({m.benchmark_symbol}) by {abs(m.relative_performance_pct):.2f} pp."
        )
    if m.ma_50 is not None and m.last_price is not None:
        side = "above" if m.last_price > m.ma_50 else "below"
        obs.append(f"Price is {side} its 50-session moving average.")
    if m.drawdown_30d is not None and m.drawdown_30d <= -10:
        obs.append(f"Maximum 30-session drawdown is {m.drawdown_30d:.1f}%.")
    return obs
