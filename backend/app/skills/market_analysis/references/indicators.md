# Indicator definitions (as implemented)

| Metric | Definition |
|---|---|
| move_pct | (close_t − close_t−1) / close_t−1 × 100 |
| return_5d_pct / return_1m_pct | % change vs 5 / 21 sessions earlier |
| volume_change_pct | volume_t vs mean of the previous 20 sessions, % |
| volatility_20d | stdev of last 20 daily log returns × √252 |
| drawdown_30d | most negative peak-to-trough decline over the last 30 sessions, % |
| zscore_move | (r_t − mean(r_{t−60..t−1})) / stdev(r_{t−60..t−1}) on daily log returns |
| anomaly_score | 0.7 × min(|z|/3, 1) + 0.3 × min(max(volume_change, 0)/200, 1) |
| relative_performance_pct | move_pct − benchmark move_pct (percentage points) |
