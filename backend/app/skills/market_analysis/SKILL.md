---
name: market_analysis
purpose: Explain price/volume behaviour from deterministic metrics.
---
# Market analysis

**When to use:** Market Agent output interpretation (in Synthesis and Briefing).

**Inputs:** move %, 5d/1m returns, volume vs 20-session average, 20d annualised volatility, 30-session
max drawdown, z-score of the latest daily log return, anomaly score, benchmark move and relative performance.

**Rules**
- All statistics are computed in Python (`app/analytics/metrics.py`). Never derive new statistics.
- |z| ≥ 2 or volume ≥ +100% vs average ⇒ "unusual session". Otherwise do not dramatise.
- If the benchmark moved in the same direction, broad market pressure is a plausible contributor.
- Data may be delayed (Yahoo Finance via yfinance) — never imply real-time precision.

**Limitations:** daily bars hide intraday sequencing; relative performance uses one benchmark only.

References: `references/indicators.md`.
