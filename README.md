# Channel WithDDControl: Trend-Following on Treasury Futures and Bitcoin

Rolling high/low channel breakout with per-trade trailing-extreme drawdown stop. Walk-forward validated across 39 years of TY (10-year Treasury futures) and 3 years of BTC (CME Bitcoin futures). Python and C++ engines cross-validated to float-64 precision.

> **Full write-up:** [`report/FINAL_REPORT.md`](report/FINAL_REPORT.md)  
> **Presentation:** [`report/5360-Presentation-FIN.pdf`](report/5360-Presentation-FIN.pdf)

---

## Out-of-Sample Walk-Forward Results

| | TY 5-min (1987–2026) | BTC 5-min (2023–2026) | TY 1-min (extension) |
|---|---:|---:|---:|
| Net profit | $68,336 | $536,397 | $71,952 |
| Max drawdown | $15,865 | $131,729 | $15,603 |
| Return on Account | **4.31×** | **4.07×** | **4.61×** |
| Sharpe ratio | 0.31 | 3.01 | 0.30 |
| Closed trades | 395 | 1,094 | 401 |
| Win rate | 33.2% | 42.0% | 32.9% |

RoA = Net Profit / |Max Drawdown|. All figures are OOS walk-forward only — no in-sample leakage.

Walk-forward: T=4yr IS, τ=1Q OOS, full grid over ChnLen ∈ [500, 10 000] step 10 and StpPct ∈ [0.005, 0.10] step 0.001 (91,296 pts per window). Objective = Net Profit / |Max Drawdown|.

---

## Key Figures

### OOS Equity Curve

![Walk-forward equity curve](report/figures/fig_equity_walkforward.png)

### Variance-Ratio Curves

![VR curves — TY and BTC](report/figures/fig_vr_curves.png)

### Push-Response Test

![Push-response test](report/figures/fig_push_response.png)

### IS vs OOS Decay

![IS vs OOS metrics](report/figures/fig_is_oos_metrics.png)

![IS vs OOS decay by metric](report/figures/fig_is_oos_decay.png)

### Parameter Stability

![Parameter stability heatmap](report/figures/fig_param_stability.png)

### Underwater Drawdown

![Underwater equity chart](report/figures/fig_underwater.png)

### Trade Distribution

![Cumulative trade count](report/figures/fig_cumulative_trades.png)

![Trade P&L distributions](report/figures/fig_trade_distributions.png)

---

## Strategy

**Channel WithDDControl** — rolling high/low channel breakout with a per-trade trailing-extreme drawdown stop.

- **Entry:** Long if `Close > max(High[1..L])`; Short if `Close < min(Low[1..L])`
- **Stop:** Exit long if `Low ≤ trade_high × (1 − S)`; exit short if `High ≥ trade_low × (1 + S)`
- **Stop is trade-level trailing:** benchmark is the highest High (longs) or lowest Low (shorts) seen since entry — not an account equity HWM
- **Parameters:** `ChnLen` (L) controls lookback; `StpPct` (S) controls stop tightness
- **PnL:** `price_change × point_value − slippage_round_turn`

Python and C++ engines cross-validated to float-64 precision on all 6 run configurations (`results/walkforward/python_cpp_fidelity_comparison.csv`).

---

## Diagnostic Findings

**Variance-ratio test (Lo–MacKinlay):**
- TY: near-random-walk at all horizons; mild VR < 1 from bid-ask bounce at 5-min
- BTC: stronger short-horizon mean reversion; VR re-rises at multi-week scales

**Push-Response test:**
- TY: ρ = +0.59 at 18 sessions (p=0.056) — multi-week trend-following signal
- BTC: ρ = −0.38 at 1 day (mean-reverting); ρ = +0.67 at 12 days (p=0.023, trend)

Optimised channel lengths:
- TY: L* ≈ 1,920 (~24 days)
- BTC: L* ∈ {276, 1,104} (~1–4 days)

---

## IS vs OOS Decay

| Market | Metric | Full-sample IS | Walk-forward OOS | Decay |
|---|---|---:|---:|---:|
| TY | Net profit | $89,465 | $68,336 | 0.76× |
| TY | Sharpe | 0.41 | 0.31 | 0.76× |
| TY | RoA | 4.73× | 4.31× | 0.91× |
| BTC | Net profit | $744,674 | $536,397 | 0.72× |
| BTC | Sharpe | 4.02 | 3.01 | 0.75× |
| BTC | RoA | 27.61× | 4.07× | 0.15×* |

*BTC RoA decay driven by larger OOS max drawdown during the 2024–25 bull run. Net profit and Sharpe decay at a normal 0.72–0.75×.

---

## How to Reproduce

```bash
# 1. Build C++ engine (requires CMake 3.15+, C++17)
cmake -S cpp -B cpp/build && cmake --build cpp/build -j
./cpp/build/tf_backtest_treasury_btc --mode both --markets TY BTC --bars 5

# 2. Run Python walk-forward (requires Python 3.10+, numpy, pandas, numba)
python -c "from mafn_engine.workflow import run_all; run_all()"

# 3. Verify Python/C++ parity
python scripts/replay_cpp_fidelity_in_python.py
python scripts/build_python_corrected_summary.py
# -> results/walkforward/python_cpp_fidelity_comparison.csv

# 4. Render all report and presentation figures
python scripts/build_final_report_figures.py
python scripts/build_front_matter_figures.py
python scripts/build_presentation_figures.py
python scripts/build_diagnostic_replicas.py
```

---

## Repository Layout

```
.
├── data/                           # Raw 5-min OHLC CSVs (TY: 1987–2026, BTC: 2018–2026)
├── mafn_engine/                    # Python research engine (Numba JIT)
│   ├── config.py                   # Market constants, slippage, session hours
│   ├── diagnostics.py              # Variance-ratio + Push-Response tests
│   ├── strategies.py               # Channel WithDDControl + per-trade ledger
│   ├── walkforward.py              # 4yr/1Q walk-forward driver
│   ├── metrics.py                  # Sharpe, RoA, Chekhlov drawdown family
│   ├── reference_backtest.py       # 70/30 split reference run
│   └── workflow.py                 # End-to-end pipeline runner
├── cpp/                            # C++17 reference engine
│   └── tf_backtest_treasury_btc.cpp
├── notebooks/                      # Narrative notebooks (outputs cleared)
│   ├── 00_Master_Pipeline.ipynb
│   ├── 01_Data_and_Statistical_Tests.ipynb
│   ├── 02_Strategy_and_WalkForward.ipynb
│   └── 03_Performance_Metrics_Extended.ipynb
├── scripts/                        # Figure builders and replay/parity scripts
├── tests/                          # Smoke tests
├── results/
│   ├── walkforward/                # Python OOS equity curves, trade ledgers, metrics
│   ├── cpp_parity/                 # C++ reference artifacts + parity comparison CSV
│   └── diagnostics/                # VR and push-response cached tables
└── report/
    ├── FINAL_REPORT.md             # Comprehensive 18-section write-up with all figures
    ├── 5360-Presentation-FIN.pdf   # Final presentation (PDF)
    ├── 5360-Presentation-FIN.pptx  # Final presentation (source)
    ├── figures/                    # Report figures
    └── presentation/figures/       # Full presentation figure set
```
