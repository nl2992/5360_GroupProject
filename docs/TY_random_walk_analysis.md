# TY Random Walk Analysis

This document summarizes the results of the Random Walk Tests applied to the TY (10-Year U.S. Treasury Note Futures) market.

The analysis is based on 5-minute close price data and includes:

* Variance Ratio (VR) Test
* Push-Response (PR) Test

The goal is to identify whether the market exhibits **trend-following** or **mean-reversion** behavior at different time scales.

---

## Methodology

### Variance Ratio Test

The Variance Ratio test compares the variance of q-period returns with q times the variance of one-period returns.

* VR(q) > 1 → positive serial dependence → trend-following
* VR(q) < 1 → negative serial dependence → mean-reversion

### Push-Response Test

The Push-Response test examines whether past price movements are followed by continuation or reversal.

* slope > 0 → continuation → trend-following
* slope < 0 → reversal → mean-reversion

---

## Summary of Results

We evaluate multiple time scales measured in 5-minute bars. The following table highlights representative scales:

| Time Scale (bars) | Approx Time | Variance Ratio | PR Slope | Interpretation                         |
| ----------------- | ----------- | -------------- | -------- | -------------------------------------- |
| 6                 | 30 min      | ~0.925         | ~0       | Near random walk / weak mean-reversion |
| 48                | 4 hours     | ~0.947         | +        | Weak trend-following                   |
| 192               | 16 hours    | ~0.944         | −        | Mean-reversion                         |
| 384               | 32 hours    | ~0.926         | −        | Stronger mean-reversion                |
| 768–1152          | 2–4 days    | ~0.89–0.90     | ++       | Trend-following                        |

---

## Interpretation

The TY market does not follow a perfect random walk. Instead, its behavior depends strongly on the time scale.

At short horizons (e.g., 30 minutes), the market behaves close to a random walk, with only weak signs of mean-reversion.

At intermediate horizons (approximately 16 to 32 hours), both the Variance Ratio and Push-Response tests consistently indicate **mean-reversion**. This suggests that price movements at these time scales tend to reverse rather than continue.

At longer horizons (multi-day scale), the Push-Response slope becomes strongly positive, indicating **trend-following behavior**, even though the Variance Ratio remains below one. This suggests that large price moves are more likely to persist over longer periods.

---

## Key Insight

The TY futures market exhibits **time-scale-dependent inefficiency**:

* Short-term → approximately random walk
* Medium-term → mean-reversion
* Long-term → trend-following

This structure implies that market predictability is not uniform across time horizons.

---

## Implications for Trading Strategy

These results provide direct motivation for the trading strategy design:

* Mean-reversion dominates at medium horizons → not suitable for breakout strategies
* Trend-following emerges at longer horizons → supports channel-based breakout strategies

Therefore, strategy parameters (e.g., lookback window) should be aligned with the time scale where trend-following behavior is strongest.

A single strategy applied uniformly across all time scales is unlikely to be optimal.

---

## Files

* `random_walk_TY.py` — implementation of VR and PR tests
* `random_walk_TY_summary.csv` — numerical results
* `variance_ratio_TY.png` — VR plot
* `push_response_TY.png` — PR plot

---

## Reproducibility

To reproduce the results:

```bash
python random_walk_TY.py
```

Make sure `TY-5minHLV.csv` is in the same directory.

---

## Notes

* Time scales are measured in 5-minute bars
* 12 bars = 1 hour
* 96 bars = 8 hours
* 1152 bars ≈ 4 days

---

## Conclusion

The TY market shows clear deviations from the random walk hypothesis. The dominant behavior shifts from mean-reversion at intermediate horizons to trend-following at longer horizons.

This provides a strong empirical foundation for applying time-scale-aware trading strategies in subsequent analysis.
