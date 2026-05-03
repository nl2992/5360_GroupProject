# MATH GR5360 — Final Project

**Group 1 — Columbia MAFN — Spring 2026**

Channel WithDDControl trend-following on TY (10-year US Treasury futures) and BTC (CME Bitcoin futures), with full walk-forward optimisation, Lo–MacKinlay variance-ratio diagnostics, push–response diagnostics, and a Python ↔ C++ parity-tested engine.

> **The full write-up with figures lives in [`report/FINAL_REPORT.md`](report/FINAL_REPORT.md).**

---

## Quick numbers (out-of-sample walk-forward)

| | TY (1987–2026) | BTC (2023–2026) |
|---|---:|---:|
| Net profit | $68 335.5 | $536 397.0 |
| Max drawdown | $15 864.7 | $131 729.3 |
| Return on Account | **4.31×** | **4.07×** |
| Sharpe | 0.31 | 3.01 |
| Closed trades | 395 | 1 094 |
| Win rate | 33.2 % | 42.0 % |
| Profit factor | 0.70 | 1.37 |

Headline configuration: `T = 4 yr` in-sample, `τ = 1 quarter` OOS, full-grid search over `ChnLen ∈ [500, 10 000]` step 10 and `StpPct ∈ [0.005, 0.10]` step 0.001, target = Net Profit / Max Drawdown.

---

## Repo layout

```
.
├── Assignment Requirements/    # PDF + Bloomberg DES/CT/GPO screens + main.m / ezread.m
├── data/                       # raw 5-min OHLC CSVs from TickData
├── mafn_engine/                # Python research engine (numba JIT)
│   ├── config.py               # market constants, slippage, sessions
│   ├── diagnostics.py          # Variance ratio + Push–Response
│   ├── strategies.py           # Channel WithDDControl + trade ledger
│   ├── walkforward.py          # 4yr / 1Q walk-forward driver
│   ├── metrics.py              # Sharpe + Chekhlov drawdown family
│   └── reference_backtest.py   # Matlab-parity reference split
├── cpp/                        # C++17 reference engine
│   └── tf_backtest_treasury_btc.cpp
├── notebooks/                  # 00–03 narrative notebooks + strategy_lib.py
├── scripts/                    # report-builder & replay scripts
├── tests/                      # smoke tests
├── results/
│   ├── walkforward/            # canonical Python OOS / full-sample artifacts
│   ├── cpp_parity/             # cross-checked C++ artifacts
│   └── diagnostics/            # cached VR & Push–Response tables
├── report/
│   ├── FINAL_REPORT.md         # the comprehensive write-up
│   └── figures/                # Columbia-themed PNGs
└── README.md
```

## Reproduction

```bash
# 1. Build C++ engine
cmake -S cpp -B cpp/build && cmake --build cpp/build -j
./cpp/build/tf_backtest_treasury_btc --mode both --markets TY BTC --bars 5

# 2. Replay corrected Python pipeline against C++ outputs (parity check)
python scripts/replay_cpp_fidelity_in_python.py
python scripts/build_python_corrected_summary.py

# 3. Render Columbia-themed report figures
python scripts/build_final_report_figures.py
```

The Python and C++ engines reproduce each other to float-64 precision on every metric (see `results/walkforward/python_cpp_fidelity_comparison.csv`).

## Statistical-test inferences

- **TY** is near-random-walk on Lo–MacKinlay, with a clear positive Spearman ρ in the push–response diagram at the **multi-week (≈ 18-session)** horizon → trend-following inefficiency.
- **BTC** is mean-reverting at intraday and multi-day horizons, but trend-following at ≈ 12 days (push–response ρ ≈ +0.67, p ≈ 0.02).

The OOS-selected breakout lengths reflect this: TY converges to `L* ≈ 1920` (≈ 24 days), BTC to `L* ∈ {276, 1104}` (≈ 1 day / 4 days).

## Authors

Group 1 — Columbia MAFN — MATH GR5360 (Spring 2026).

---

*Submission for MATH GR5360 — Mathematical Methods in Financial Price Analysis — due 2 May 2026.*
