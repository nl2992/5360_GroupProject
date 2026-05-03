# Corrected Backtest Logic — C++ 5-Minute Confirmation

This run reflects the logic fixes applied on 2026-05-01 before the Python notebook reruns.

## What changed

- Treasury session filtering now uses bar-close convention `(07:20, 14:00]`, which restores the intended 80 liquid 5-minute bars per session.

- BTC now uses the actual CME local session definition `17:00-16:00`, so the active 5-minute trading day is 276 bars rather than the old 288-bar 24-hour approximation.

- BTC quick lookback horizons were converted from 24-hour approximations to session-consistent horizons: `276, 552, 828, 1104, 1380, 1656, 2208`.

- Python `load_ohlc()` now fails loudly if a requested 1-minute file is missing instead of silently falling back to 5-minute data.

- Both engines now reject pre-inception or obviously mislabeled BTC files.

## Market assumptions used in the corrected run

| Market   | DataFile             |   PointValue |   TickValueUsed |   RoundTurnCost | SessionLocal   | BarRule                                                            |   BarsPerSession_5m | Notes                                                                              |
|:---------|:---------------------|-------------:|----------------:|----------------:|:---------------|:-------------------------------------------------------------------|--------------------:|:-----------------------------------------------------------------------------------|
| TY       | data/TY-5minHLV.csv  |         1000 |          15.625 |          18.625 | 07:20-14:00    | (07:20, 14:00] bar-close timestamps                                |                  80 | Aligned to TF Data row and professor liquid-session handling.                      |
| BTC      | data/BTC-5minHLV.csv |            5 |          25     |          25     | 17:00-16:00    | (17:00, 16:00] across midnight; maintenance break excluded by file |                 276 | Slpg from TF Data; minimum tick value from Bloomberg DES = 5 points x $5/pt = $25. |

## 5-minute headline results

| Market   | RunType                 |    L |    S |        NetProfit |   NetMaxDD |    NetRoA |   ClosedTrades |   RoundTurnCost | CostNote                                                                                                                                  |
|:---------|:------------------------|-----:|-----:|-----------------:|-----------:|----------:|---------------:|----------------:|:------------------------------------------------------------------------------------------------------------------------------------------|
| TY       | walkforward_oos         | 1440 | 0.01 |  68335.5         |    15864.7 |  4.30739  |            395 |          18.625 | Official TF Data TY round-turn cost = $18.625 per contract.                                                                               |
| TY       | full_sample             | 1440 | 0.01 |  87864.7         |    17186.5 |  5.11244  |            724 |          18.625 | Official TF Data TY round-turn cost = $18.625 per contract.                                                                               |
| TY       | reference_in_sample     | 2240 | 0.04 |  89464.9         |    18903.2 |  4.73278  |            154 |          18.625 | Official TF Data TY round-turn cost = $18.625 per contract.                                                                               |
| TY       | reference_out_of_sample | 2240 | 0.04 |   4392.62        |    33128.5 |  0.132594 |             71 |          18.625 | Official TF Data TY round-turn cost = $18.625 per contract.                                                                               |
| TY       | reference_full          | 2240 | 0.04 |  93513.8         |    33128.5 |  2.82276  |            225 |          18.625 | Official TF Data TY round-turn cost = $18.625 per contract.                                                                               |
| BTC      | walkforward_oos         |  276 | 0.01 | 536397           |   131729   |  4.07197  |           1094 |          25     | Official TF Data BTC round-turn cost = $25.00 per contract; Bloomberg DES implies a 5-point minimum tick, or $25 per minimum fluctuation. |
| BTC      | full_sample             |  276 | 0.01 |      1.73778e+06 |   131729   | 13.1921   |           5016 |          25     | Official TF Data BTC round-turn cost = $25.00 per contract; Bloomberg DES implies a 5-point minimum tick, or $25 per minimum fluctuation. |
| BTC      | reference_in_sample     |  552 | 0.01 | 744674           |    26967.2 | 27.614    |           2325 |          25     | Official TF Data BTC round-turn cost = $25.00 per contract; Bloomberg DES implies a 5-point minimum tick, or $25 per minimum fluctuation. |
| BTC      | reference_out_of_sample |  552 | 0.01 | 449022           |   103824   |  4.32486  |            936 |          25     | Official TF Data BTC round-turn cost = $25.00 per contract; Bloomberg DES implies a 5-point minimum tick, or $25 per minimum fluctuation. |
| BTC      | reference_full          |  552 | 0.01 |      1.1937e+06  |   103824   | 11.4974   |           3261 |          25     | Official TF Data BTC round-turn cost = $25.00 per contract; Bloomberg DES implies a 5-point minimum tick, or $25 per minimum fluctuation. |

## Quarterly extremes

| Market   | Label     |   Period | OOSStart         | OOSEnd           |    L |    S |   NetProfit |   NetMaxDD |    NetRoA |   ClosedTrades |
|:---------|:----------|---------:|:-----------------|:-----------------|-----:|-----:|------------:|-----------:|----------:|---------------:|
| TY       | best_oos  |       50 | 10/29/1999 07:25 | 01/31/2000 14:00 | 1920 | 0.03 |    10472.1  |    1734.38 |  6.03795  |              1 |
| TY       | worst_oos |      136 | 04/01/2021 10:15 | 06/30/2021 09:15 | 3200 | 0.01 |    -2689.69 |    2727.25 | -0.986227 |              2 |
| BTC      | best_oos  |        7 | 10/06/2025 10:20 | 02/12/2026 22:30 | 1104 | 0.01 |   115255    |   17356.2  |  6.64053  |             95 |
| BTC      | worst_oos |        6 | 05/30/2025 00:35 | 10/06/2025 10:15 |  276 | 0.01 |    12053.8  |  131729    |  0.091504 |            134 |

## 1-minute data status

- `TY-1minHLV.csv` exists in the repo and the corrected C++ engine can read it.

- There is currently **no valid BTC 1-minute futures file** in the repo. The engine now fails explicitly instead of substituting 5-minute BTC data.

- If a valid `BTC-1minHLV.csv` is supplied later, the same C++ and Python paths are now interval-aware and ready to run it.


## Source files

- `Assignment Requirements/TF Data-2_副本.xls`

- `Assignment Requirements/BTC DES.gif`

- `data/TY-5minHLV.csv`

- `data/BTC-5minHLV.csv`
