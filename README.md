# MATH GR5360 - Final Project

**Group 1 - Columbia MAFN - Spring 2026**

Channel WithDDControl trend-following on TY (10-year US Treasury futures) and BTC (CME Bitcoin futures), with full walk-forward optimisation, Lo-MacKinlay variance-ratio diagnostics, push-response diagnostics, and a Python/C++ parity-tested engine.

> **Full write-up:** [`report/FINAL_REPORT.md`](report/FINAL_REPORT.md)
> **Presentation:** [`report/5360-Presentation-FIN.pdf`](report/5360-Presentation-FIN.pdf)

---

## Out-of-sample walk-forward results

| | TY 5-min (1987-2026) | BTC 5-min (2018-2026) | TY 1-min (extension) |
|---|---:|---:|---:|
| Net profit | $68,336 | $536,397 | $71,952 |
| Max drawdown | $15,865 | $131,729 | $15,603 |
| Return on Account | **4.31x** | **4.07x** | **4.61x** |
| Sharpe ratio | 0.31 | 3.01 | - |
| Closed trades | 395 | 1,094 | - |
| Win rate | 33.2% | 42.0% | - |
| Profit factor | 0.70 | 1.37 | - |

RoA = Net Profit / |Max Drawdown|. All figures are OOS walk-forward only (no in-sample leakage).

Walk-forward configuration: `T = 4 yr` in-sample, `tau = 1 quarter` OOS step, grid search over `ChnLen in [500, 10000]` step 10 and `StpPct in [0.005, 0.10]` step 0.001 (91,296 points), objective = Net Profit / |Max Drawdown|.

---

## Strategy

**Channel WithDDControl** - a rolling high/low channel breakout with a per-trade trailing-extreme drawdown stop.

- **Entry:** Long if `Close > max(High[1..L])`; Short if `Close < min(Low[1..L])`
- **Stop:** Exit long if `Low <= trade_high * (1 - S)`; exit short if `High >= trade_low * (1 + S)`
- **Parameters:** `ChnLen` (L) controls the lookback; `StpPct` (S) controls the stop tightness
- **PnL:** `price_change * point_value - slippage_per_round_turn`

Python and C++ engines are cross-validated to float-64 precision across all 6 run configurations (see `results/walkforward/python_cpp_fidelity_comparison.csv`).

---

## Statistical diagnostics

**Variance-ratio test (Lo-MacKinlay):**
- TY: near-random-walk at fine granularity; positive deviation from 1 at longer horizons
- BTC: stronger short-horizon deviations; trend-following signal at multi-day scales

**Push-response test:**
- TY: weak continuation at medium horizons (18-24 sessions); primary trend-following horizon
- BTC: short-horizon reversal, trend-following signal at approximately 12 days

These diagnostics justify parameter selection: TY converges to `L* ~= 1920` (~24 sessions), BTC to `L* in {276, 1104}` (~1-4 days).

---

## IS vs OOS decay

| Market | Metric | Full-sample IS | Walk-forward OOS | Decay ratio |
|---|---|---:|---:|---:|
| TY | RoA | ~7.1x | 4.31x | 0.61x |
| TY | Sharpe | ~0.55 | 0.31 | 0.56x |
| BTC | RoA | ~6.1x | 4.07x | 0.67x |
| BTC | Sharpe | ~4.5 | 3.01 | 0.67x |

Decay of 0.6-0.7x is consistent with genuine but partially overfitted in-sample performance.

---

## Repo layout

```
.
+-- Assignment Requirements/    # PDF brief + Bloomberg DES/CT/GPO screens + main.m / ezread.m
+-- data/                       # raw 5-min OHLC CSVs (TY: 1987-2026, BTC: 2018-2026)
+-- mafn_engine/                # Python research engine (Numba JIT)
|   +-- config.py               # market constants, slippage, session hours
|   +-- diagnostics.py          # Variance-ratio + Push-Response tests
|   +-- strategies.py           # Channel WithDDControl + per-trade ledger
|   +-- walkforward.py          # 4yr/1Q walk-forward driver
|   +-- metrics.py              # Sharpe + Chekhlov drawdown family
|   +-- reference_backtest.py   # Matlab-parity reference split
|   +-- workflow.py             # end-to-end pipeline runner
+-- cpp/                        # C++17 reference engine
|   +-- tf_backtest_treasury_btc.cpp
+-- notebooks/                  # narrative notebooks (outputs cleared)
|   +-- 00_Master_Pipeline.ipynb
|   +-- 01_Data_and_Statistical_Tests.ipynb
|   +-- 02_Strategy_and_WalkForward.ipynb
|   +-- 03_Performance_Metrics_Extended.ipynb
|   +-- strategy_lib.py
+-- scripts/                    # figure builders and replay/parity scripts
+-- tests/                      # smoke tests
+-- results/
|   +-- walkforward/            # Python OOS equity curves, trade ledgers, metrics
|   +-- cpp_parity/             # C++ reference artifacts + parity comparison CSV
|   +-- diagnostics/            # VR and push-response cached tables
+-- report/
|   +-- FINAL_REPORT.md         # comprehensive 16-section write-up with figures
|   +-- 5360-Presentation-FIN.pdf   # final submitted presentation (PDF)
|   +-- 5360-Presentation-FIN.pptx  # final submitted presentation (source)
|   +-- figures/                # Columbia-themed PNGs for report
|   +-- presentation/           # presentation figure assets
+-- README.md
```

---

## How to reproduce

```bash
# 1. Build C++ engine (requires CMake 3.15+, C++17 compiler)
cmake -S cpp -B cpp/build && cmake --build cpp/build -j
./cpp/build/tf_backtest_treasury_btc --mode both --markets TY BTC --bars 5

# 2. Run Python walk-forward (requires Python 3.10+, numpy, pandas, numba)
python -c "from mafn_engine.workflow import run_all; run_all()"

# 3. Verify Python/C++ parity
python scripts/replay_cpp_fidelity_in_python.py
python scripts/build_python_corrected_summary.py
# -> results/walkforward/python_cpp_fidelity_comparison.csv

# 4. Render report figures (Columbia color scheme)
python scripts/build_final_report_figures.py
python scripts/build_front_matter_figures.py
```

Full narrative is in [`report/FINAL_REPORT.md`](report/FINAL_REPORT.md) with all figures and methodology.

---

## Authors

Group 1 - Columbia MAFN - MATH GR5360 (Spring 2026).

---

*Submitted for MATH GR5360 - Mathematical Methods in Financial Price Analysis - Spring 2026.*
