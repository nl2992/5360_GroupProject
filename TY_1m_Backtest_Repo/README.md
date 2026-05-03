# TY 1-Minute Channel WithDDControl Repo

This is a standalone local repository for the corrected `TY` 1-minute trend-following backtest based on the professor's `Channel WithDDControl` logic.

It was carved out from the broader course project so the `TY` 1-minute experiment can be inspected, rerun, and shared separately.

## What is included

- Corrected C++ backtest source:
  - [cpp/tf_backtest_treasury_btc.cpp](cpp/tf_backtest_treasury_btc.cpp)
- Corrected Python engine:
  - [mafn_engine](mafn_engine)
- Helper scripts:
  - [scripts/replay_cpp_fidelity_in_python.py](scripts/replay_cpp_fidelity_in_python.py)
  - [scripts/build_python_corrected_summary.py](scripts/build_python_corrected_summary.py)
- Notebook templates:
  - [notebooks/02_Strategy_and_WalkForward.ipynb](notebooks/02_Strategy_and_WalkForward.ipynb)
  - [notebooks/03_Performance_Metrics_Extended.ipynb](notebooks/03_Performance_Metrics_Extended.ipynb)
- Executed TY 1-minute notebooks:
  - [notebooks_executed/02_Strategy_and_WalkForward_TY_1m_executed.ipynb](notebooks_executed/02_Strategy_and_WalkForward_TY_1m_executed.ipynb)
  - [notebooks_executed/03_Performance_Metrics_Extended_TY_1m_executed.ipynb](notebooks_executed/03_Performance_Metrics_Extended_TY_1m_executed.ipynb)
- Corrected C++ TY 1-minute outputs:
  - [results_cpp_ty_1m](results_cpp_ty_1m)
- Corrected Python TY 1-minute outputs:
  - [results_py_ty_1m](results_py_ty_1m)

## Market-definition fidelity used here

- Market: `TY` 10-Year Treasury Note futures
- Data interval: `1 minute`
- Point value: `1000`
- Tick value: `15.625`
- Round-turn slippage: `18.625`
- Session filter: `07:20` to `14:00` Chicago time
- Active bars per session: `400`
- Matlab-style reference mode: `barsBack = 17001`

Those settings reflect the corrected fidelity pass against the `TF Data` workbook and the professor's Matlab logic.

## Headline results

From [results_cpp_ty_1m/tf_backtest_summary.csv](results_cpp_ty_1m/tf_backtest_summary.csv):

- Walk-forward OOS:
  - `L = 6400`
  - `S = 0.010`
  - net profit = `$71,952.36`
  - max drawdown = `$15,603.09`
  - return on account = `4.611`
  - closed trades = `401`
- Full sample:
  - `L = 6400`
  - `S = 0.010`
  - net profit = `$97,670.56`
  - max drawdown = `$13,827.50`
  - return on account = `7.064`
  - closed trades = `772`
- Reference split:
  - best `L = 11200`
  - best `S = 0.040`
  - in-sample RoA = `4.819`
  - out-of-sample profit = `$4,408.25`
  - out-of-sample max drawdown = `$33,191.00`
  - out-of-sample RoA = `0.133`

## Python / C++ parity

The corrected Python replay matches the corrected C++ outputs within tolerance on every `TY` 1-minute check.

See:

- [results_py_ty_1m/python_cpp_fidelity_comparison_ty_1m.csv](results_py_ty_1m/python_cpp_fidelity_comparison_ty_1m.csv)
- [results_py_ty_1m/python_fidelity_summary_ty_1m.md](results_py_ty_1m/python_fidelity_summary_ty_1m.md)

## What was intentionally omitted

This standalone repo does **not** duplicate the largest raw bar-by-bar C++ output files, because they are enormous:

- `TY_tf_oos_returns.csv`
- `TY_tf_fullsample_returns.csv`
- `TY_tf_reference_series.csv`

It also does not track the two largest Python equity files in git, because GitHub rejects files larger than `100 MB`:

- `results_py_ty_1m/TY_1m/TY_1m_fullsample_equity.csv`
- `results_py_ty_1m/TY_1m/TY_1m_walkforward_equity.csv`

Those files can still exist locally after generation, but they are intentionally ignored by git in this standalone repo.

They still exist in the parent project here:

- [../results_cpp_fidelity_ty_1m](../results_cpp_fidelity_ty_1m)

The source `TY` 1-minute input CSV was also not duplicated here due size:

- [../data/TY-1minHLV.csv](../data/TY-1minHLV.csv)

## Quick run commands

Compile the C++ backtest:

```bash
g++ -std=c++17 -O2 -Wall -Wextra -pedantic cpp/tf_backtest_treasury_btc.cpp -o cpp/tf_backtest_treasury_btc
```

Run the corrected `TY` 1-minute backtest:

```bash
./cpp/tf_backtest_treasury_btc --mode both --grid-mode quick --bar-minutes 1 --markets TY --out-dir results_cpp_ty_1m
```

Refresh the Python replay summary:

```bash
python scripts/build_python_corrected_summary.py
```
