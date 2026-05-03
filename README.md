# MATH GR5360 - Final Project

**Group 1 - Columbia MAFN - Spring 2026**

Channel WithDDControl trend-following on TY (10-year US Treasury futures) and BTC (CME Bitcoin futures). Walk-forward validated, dual-engine cross-checked, diagnostics-first.

> **Full write-up:** [`report/FINAL_REPORT.md`](report/FINAL_REPORT.md)
> **Presentation:** [`report/5360-Presentation-FIN.pdf`](report/5360-Presentation-FIN.pdf)

---

## Out-of-sample walk-forward results

| | TY 5-min (1987-2026) | BTC 5-min (2023-2026) | TY 1-min (extension) |
|---|---:|---:|---:|
| Net profit | $68,336 | $536,397 | $71,952 |
| Max drawdown | $15,865 | $131,729 | $15,603 |
| Return on Account | **4.31x** | **4.07x** | **4.61x** |
| Sharpe ratio | 0.31 | 3.01 | 0.30 |
| Closed trades | 395 | 1,094 | 401 |
| Win rate | 33.2% | 42.0% | 32.9% |

RoA = Net Profit / |Max Drawdown|. All figures are OOS walk-forward only (no IS leakage).

Walk-forward: T=4yr IS, tau=1Q OOS, full grid over ChnLen in [500, 10000] step 10 and StpPct in [0.005, 0.10] step 0.001 (91,296 pts per window). Objective = Net Profit / |Max Drawdown|.

---

## Strategy

**Channel WithDDControl** - rolling high/low channel breakout with a per-trade trailing-extreme drawdown stop.

- **Entry:** Long if `Close > max(High[1..L])`; Short if `Close < min(Low[1..L])`
- **Stop:** Exit long if `Low <= trade_high * (1 - S)`; exit short if `High >= trade_low * (1 + S)`
- **Stop is trade-level trailing:** benchmark is the highest High (longs) or lowest Low (shorts) seen since entry, not an account equity HWM
- **Parameters:** ChnLen (L) controls lookback; StpPct (S) controls stop tightness
- **PnL:** `price_change * point_value - slippage_round_turn`

Python and C++ engines cross-validated to float-64 precision on all 6 run configurations (`results/walkforward/python_cpp_fidelity_comparison.csv`).

---

## Diagnostic findings

**Variance-ratio test (Lo-MacKinlay):**
- TY: near-random-walk at all horizons; mild VR < 1 from bid-ask bounce at 5-min
- BTC: stronger short-horizon mean reversion; VR re-rises at multi-week scales

**Push-Response test:**
- TY: rho = +0.59 at 18 sessions (p=0.056) - multi-week trend-following signal
- BTC: rho = -0.38 at 1 day (mean-reverting); rho = +0.67 at 12 days (p=0.023, trend)

These diagnostics justify why the walk-forward selects different L values:
- TY: `L* ~= 1,920` bars (~24 trading days)
- BTC: `L* in {276, 1,104}` (~1-4 trading days)

---

## IS vs OOS decay

| Market | Metric | Full-sample IS (C++ ref) | Walk-forward OOS | Decay |
|---|---|---:|---:|---:|
| TY | Net profit | $89,465 | $68,336 | 0.76x |
| TY | Sharpe | 0.41 | 0.31 | 0.76x |
| TY | RoA | 4.73x | 4.31x | 0.91x |
| BTC | Net profit | $744,674 | $536,397 | 0.72x |
| BTC | Sharpe | 4.02 | 3.01 | 0.75x |
| BTC | RoA | 27.61x | 4.07x | 0.15x* |

*BTC RoA decay is a MaxDD artefact: the 2024-25 bull run created larger drawdowns OOS than anything in the IS window. Net profit and Sharpe decay at a healthy 0.72-0.75x.

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
|   +-- metrics.py              # Sharpe, RoA, Chekhlov drawdown family
|   +-- reference_backtest.py   # Matlab-parity 70/30 split reference run
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
|   +-- FINAL_REPORT.md         # comprehensive 18-section write-up with all figures
|   +-- 5360-Presentation-FIN.pdf    # final submitted presentation (PDF)
|   +-- 5360-Presentation-FIN.pptx  # final submitted presentation (source)
|   +-- figures/                # Columbia-themed PNGs for report body
|   +-- presentation/figures/   # full figure set (front_*, repl_*, slide_*)
+-- README.md
```

---

## How to reproduce

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

## Authors

Group 1 - Columbia MAFN - MATH GR5360 (Spring 2026).

---

*Submitted for MATH GR5360 - Mathematical Methods in Financial Price Analysis - Spring 2026.*
