# Corrected TY 1-Minute Backtest Summary

This folder contains the corrected C++ `Channel WithDDControl` outputs for `TY` on `1-minute` data.

## Market-definition fidelity
- Source file: `data/TY-1minHLV.csv`
- Point value: `1000`
- Tick value: `15.625`
- Round-turn slippage: `18.625`
- Session filter: `07:20` to `14:00` Chicago time
- Active bars per session: `400`
- Warmup / Matlab parity mode: `barsBack = 17001` for the reference split

## Headline results
- Walk-forward OOS: `L=6400`, `S=0.010`, net profit `$71,952.36`, max DD `$15,603.09`, RoA `4.611`, closed trades `401`.
- Full sample: `L=6400`, `S=0.010`, net profit `$97,670.56`, max DD `$13,827.50`, RoA `7.064`, closed trades `772`.
- Reference in-sample: `L=11200`, `S=0.040`, net RoA `4.819`.
- Reference out-of-sample: net profit `$4,408.25`, max DD `$33,191.00`, RoA `0.133`.

## Notes
- This is the dedicated 1-minute TY run requested after the 5-minute fidelity pass.
- The corrected Python cache and executed notebooks for this run live under `results_py_corrected/TY_1m`.
