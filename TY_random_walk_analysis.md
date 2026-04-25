# TY Random Walk Analysis

This document summarizes the results of the Random Walk Tests applied to the TY (10-Year U.S. Treasury Note Futures) market.

The analysis is based on 5-minute close price data and includes:

- Variance Ratio (VR) Test  
- Push-Response (PR) Test  

The goal is to identify whether the market exhibits **trend-following** or **mean-reversion** behavior at different time scales.

---

## Methodology

### Variance Ratio Test

The Variance Ratio test compares the variance of q-period returns with q times the variance of one-period returns.

- VR(q) > 1 → positive serial dependence → trend-following  
- VR(q) < 1 → negative serial dependence → mean-reversion  

### Push-Response Test

The Push-Response test examines whether past price movements are followed by continuation or reversal.

- slope > 0 → continuation → trend-following  
- slope < 0 → reversal → mean-reversion  

---

## Summary of Results

We evaluate multiple time scales measured in 5-minute bars. The following table highlights representative scales:

| Time Scale (bars) | Approx Time | Variance Ratio | PR Slope | Interpretation |
|------------------|------------|---------------|----------|----------------|
| 6                | 30 min     | ~0.925        | ~0       | Near random walk / weak mean-reversion |
| 48               | 4 hours    | ~0.947        | +        | Mixed evidence |
| 192              | 16 hours   | ~0.944        | −        | Mean-reversion |
| 384              | 32 hours   | ~0.926        | −        | Stronger mean-reversion |
| 768–1152         | 2–4 days   | ~0.89–0.90    | ++       | Mixed evidence / PR-only trend-following signal |

---

## Interpretation

The TY market does not follow a perfect random walk. Instead, its behavior depends strongly on the time scale.

At short horizons (e.g., 30 minutes), the market behaves close to a random walk, with only weak signs of mean-reversion.

At intermediate horizons (approximately 16 to 32 hours), both the Variance Ratio and Push-Response tests consistently indicate **mean-reversion**. This suggests that price movements at these time scales tend to reverse rather than continue. The Variance Ratio is generally below one, and for several intermediate scales, the deviations are statistically significant at conventional levels.

At longer horizons (multi-day scale), the Push-Response slope becomes positive, indicating potential trend-following behavior. However, the Variance Ratio remains below one, which does not support strong positive serial dependence. Therefore, the evidence at long horizons should be interpreted as **mixed rather than conclusive**.

The strongest evidence of inefficiency appears at intermediate time scales (approximately 16 to 32 hours), where both tests consistently indicate mean-reversion.

---

## Key Insight

The TY futures market exhibits time-scale-dependent inefficiency:

- Short-term → close to random walk / weak mean-reversion  
- Medium-term → relatively stronger mean-reversion  
- Long-term → mixed evidence: Push-Response becomes positive, but Variance Ratio remains below one  

---

## Implications for Trading Strategy

These results suggest that the TY market does not show uniform behavior across all time scales. Medium horizons show more consistent mean-reversion evidence, while longer horizons show mixed signals: the Push-Response test suggests continuation, but the Variance Ratio test remains below one.

Therefore, channel-based breakout strategies may be worth testing at longer lookback windows, where the Push-Response test suggests some trend-following behavior, although the evidence remains mixed.

---

## Files

- `random_walk_TY.py` — implementation of VR and PR tests  
- `random_walk_TY_summary.csv` — numerical results  
- `variance_ratio_TY.png` — VR plot  
- `push_response_TY.png` — PR plot  

---

## Reproducibility

To reproduce the results:

```bash
python random_walk_TY.py
