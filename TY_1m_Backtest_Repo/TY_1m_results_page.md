# TY 1-Minute Corrected Results Page

This page coalesces the corrected `TY` 1-minute results from the standalone repo into one scrollable markdown report with embedded figures.

## Run configuration
- Market: `TY` 10-Year Treasury Note futures
- Interval: `1 minute`
- Point value: `1000`
- Tick value: `15.625`
- Round-turn slippage: `18.625`
- Session filter: `07:20` to `14:00` Chicago time
- Active bars per session: `400`
- Matlab-style reference warmup: `barsBack = 17001`

## Headline summary
| Run Type                |   Lookback |   Stop | NetProfit   | NetMaxDD   |   NetRoA |   ClosedTrades | TotalCost   | TurnoverContracts   |
|:------------------------|-----------:|-------:|:------------|:-----------|---------:|---------------:|:------------|:--------------------|
| walkforward_oos         |       6400 |   0.01 | $71,952.36  | $15,603.09 |    4.611 |            401 | $8,558.19   | 919                 |
| full_sample             |       6400 |   0.01 | $97,670.56  | $13,827.50 |    7.064 |            772 | $14,378.50  | 1,544               |
| reference_in_sample     |      11200 |   0.04 | $91,467.81  | $18,981.38 |    4.819 |            157 | $2,933.44   | 315                 |
| reference_out_of_sample |      11200 |   0.04 | $4,408.25   | $33,191.00 |    0.133 |             71 | $1,322.38   | 142                 |
| reference_full          |      11200 |   0.04 | $95,516.69  | $33,191.00 |    2.878 |            228 | $4,255.81   | 457                 |

- Modal walk-forward configuration: `L = 6400`, `S = 0.010` selected `15` times.
- Walk-forward OOS total profit: `$71,952.36`
- Walk-forward OOS max drawdown: `$15,603.09`
- Walk-forward OOS Sharpe: `0.299`
- Full-sample net profit: `$97,670.56`
- Full-sample max drawdown: `$13,827.50`

![Headline Results](results_report/figures/00_headline_results_table.png)

## 1-minute versus 5-minute comparison
| Run              | 1m Profit   | 5m Profit   | 1m MaxDD   | 5m MaxDD   |   1m RoA |   5m RoA |
|:-----------------|:------------|:------------|:-----------|:-----------|---------:|---------:|
| Walk-forward OOS | $71,952.36  | $68,335.52  | $15,603.09 | $15,864.70 |    4.611 |    4.307 |
| Full sample      | $97,670.56  | $87,864.72  | $13,827.50 | $17,186.47 |    7.064 |    5.112 |
| Reference IS     | $91,467.81  | $89,464.94  | $18,981.38 | $18,903.25 |    4.819 |    4.733 |
| Reference OOS    | $4,408.25   | $4,392.62   | $33,191.00 | $33,128.50 |    0.133 |    0.133 |

- 1m OOS profit minus 5m OOS profit: `$3,616.84`
- 1m OOS max drawdown minus 5m OOS max drawdown: `$-261.61`
- 1m OOS RoA minus 5m OOS RoA: `0.304`

![1m vs 5m Interval Comparison](results_report/figures/10_interval_comparison_table.png)

![1m vs 5m Growth Comparison](results_report/figures/11_growth_compare_1m_vs_5m.png)

![1m vs 5m Underwater Comparison](results_report/figures/12_underwater_compare_1m_vs_5m.png)

![1m vs 5m OOS Metric Comparison](results_report/figures/13_oos_metric_compare_1m_vs_5m.png)

![1m vs 5m Quarterly Comparison](results_report/figures/14_quarterly_compare_1m_vs_5m.png)

![1m vs 5m Parameter Comparison](results_report/figures/15_parameter_compare_1m_vs_5m.png)

![1m vs 5m Distribution Comparison](results_report/figures/16_distribution_compare_1m_vs_5m.png)

![1m vs 5m Parity Comparison](results_report/figures/17_parity_compare_1m_vs_5m.png)

## Equity curves
![Growth of $1](results_report/figures/01_growth_of_1.png)

## Underwater curves
![Underwater Curves](results_report/figures/02_underwater_curves.png)

## Quarterly walk-forward outcomes
![Quarterly Performance](results_report/figures/03_quarterly_performance.png)

## Parameter path
![Parameter Path](results_report/figures/04_parameter_path.png)

## Parameter frequency
![Parameter Frequency](results_report/figures/05_parameter_frequency.png)

## Trade distributions
![Trade Distributions](results_report/figures/06_trade_distributions.png)

## Matlab-style reference split
| Segment       |   start_idx |   end_exclusive |   Profit |   WorstDrawDown |   StDev |   TradeUnits |   Objective |
|:--------------|------------:|----------------:|---------:|----------------:|--------:|-------------:|------------:|
| in_sample     |       17000 |         3011565 | 91467.8  |         18981.4 | 25.4574 |        157.5 |    4.81882  |
| out_of_sample |     3011565 |         4319435 |  4408.25 |         33191   | 22.2266 |         71   |    0.132815 |

![Reference Split Comparison](results_report/figures/07_reference_split_comparison.png)

## Quarterly extremes
![Quarter Extremes](results_report/figures/08_quarter_extremes.png)

### Top 10 OOS quarters by profit
|   Period | OOS_start           | OOS_end             |     L |     S |   OOS_Profit |   OOS_MaxDD |   OOS_Objective |   OOS_Trades |
|---------:|:--------------------|:--------------------|------:|------:|-------------:|------------:|----------------:|-------------:|
|       50 | 1999-10-29 07:21:00 | 2000-01-31 14:00:00 |  6400 | 0.03  |     14190.8  |     1750    |         8.10904 |            1 |
|      131 | 2020-01-08 10:41:00 | 2020-04-07 08:00:00 |  9600 | 0.02  |      8170.12 |     2804.94 |         2.91277 |            1 |
|       64 | 2003-05-14 11:21:00 | 2003-08-13 13:20:00 |  8000 | 0.04  |      6862.69 |     3781.25 |         1.81493 |            1 |
|        2 | 1987-09-16 08:01:00 | 1987-12-23 14:00:00 |  4800 | 0.02  |      6603.69 |     3215.38 |         2.05378 |            4 |
|       85 | 2008-09-08 08:41:00 | 2008-12-04 12:25:00 |  4800 | 0.015 |      6514.94 |     2600.37 |         2.50538 |            4 |
|       87 | 2009-03-06 11:31:00 | 2009-06-04 13:30:00 |  6400 | 0.015 |      5968.91 |     2082.38 |         2.86639 |            2 |
|      109 | 2014-08-05 12:06:00 | 2014-11-03 07:25:00 |  4800 | 0.015 |      5070.59 |     1820.34 |         2.78551 |            3 |
|       57 | 2001-08-02 07:21:00 | 2001-11-06 11:20:00 | 16000 | 0.03  |      5006.31 |     2187.5  |         2.2886  |            0 |
|       27 | 1994-01-18 07:21:00 | 1994-04-18 14:00:00 | 16000 | 0.03  |      4815.81 |     4018.62 |         1.19837 |            1 |
|       45 | 1998-07-28 07:21:00 | 1998-10-26 14:00:00 |  9600 | 0.03  |      4754.94 |     3717.12 |         1.2792  |            2 |

### Bottom 10 OOS quarters by profit
|   Period | OOS_start           | OOS_end             |     L |     S |   OOS_Profit |   OOS_MaxDD |   OOS_Objective |   OOS_Trades |
|---------:|:--------------------|:--------------------|------:|------:|-------------:|------------:|----------------:|-------------:|
|      110 | 2014-11-03 07:26:00 | 2015-02-03 08:15:00 |  8000 | 0.015 |     -6779.89 |     7325.45 |       -0.925525 |            6 |
|       98 | 2011-11-17 12:16:00 | 2012-02-17 11:20:00 |  7200 | 0.01  |     -5635.03 |     5844.47 |       -0.964165 |            6 |
|      108 | 2014-05-08 08:06:00 | 2014-08-05 12:05:00 |  6400 | 0.015 |     -5319.42 |     7310.11 |       -0.72768  |            6 |
|       65 | 2003-08-13 13:21:00 | 2003-11-14 08:40:00 |  8000 | 0.04  |     -5155.94 |     6849.75 |       -0.752719 |            2 |
|       12 | 1990-04-25 07:21:00 | 1990-07-24 14:00:00 |  9600 | 0.04  |     -5002.69 |     5555.88 |       -0.900432 |            3 |
|       69 | 2004-08-20 11:51:00 | 2004-11-23 08:10:00 |  7200 | 0.015 |     -4616.16 |     5919.34 |       -0.779843 |            4 |
|       49 | 1999-07-30 07:21:00 | 1999-10-28 14:00:00 |  9600 | 0.03  |     -4062.19 |     5568.5  |       -0.729494 |            2 |
|       59 | 2002-02-08 11:21:00 | 2002-05-10 11:20:00 | 16000 | 0.03  |     -3938.13 |     4850.69 |       -0.811869 |            2 |
|      143 | 2022-12-19 12:46:00 | 2023-03-21 10:05:00 | 16000 | 0.01  |     -3627.03 |     4164.59 |       -0.870921 |            5 |
|       66 | 2003-11-14 08:41:00 | 2004-02-20 08:20:00 |  8000 | 0.04  |     -3593.44 |     6537.25 |       -0.549686 |            2 |

## Python / C++ parity
| Market   |   BarMinutes | RunType                 |   PythonProfit |   CppProfit |   PythonMaxDD |   CppMaxDD |   PythonRoA |   CppRoA |   PythonClosedTrades |   CppClosedTrades |   ProfitPctError |   MaxDDPctError |   RoAPctError |   TradesPctError | Within10Pct   |
|:---------|-------------:|:------------------------|---------------:|------------:|--------------:|-----------:|------------:|---------:|---------------------:|------------------:|-----------------:|----------------:|--------------:|-----------------:|:--------------|
| TY       |            1 | walkforward_oos         |       71952.4  |    71952.4  |       15603.1 |    15603.1 |    4.61142  | 4.61142  |                  401 |               401 |      2.02244e-15 |     3.73052e-15 |   4.45677e-08 |                0 | True          |
| TY       |            1 | full_sample             |       97670.6  |    97670.6  |       13827.5 |    13827.5 |    7.0635   | 7.0635   |                  772 |               772 |      5.36363e-15 |     2.10478e-15 |   2.48028e-08 |                0 | True          |
| TY       |            1 | reference_in_sample     |       91467.8  |    91467.8  |       18981.4 |    18981.4 |    4.81882  | 4.81882  |                  157 |               157 |      0           |     0           |   0           |                0 | True          |
| TY       |            1 | reference_out_of_sample |        4408.25 |     4408.25 |       33191   |    33191   |    0.132815 | 0.132815 |                   71 |                71 |      0           |     0           |   0           |                0 | True          |
| TY       |            1 | reference_full          |       95516.7  |    95516.7  |       33191   |    33191   |    2.87779  | 2.87779  |                  228 |               228 |      0           |     0           |   0           |                0 | True          |

![Parity Table](results_report/figures/09_parity_table.png)

## Figure inventory
- `00_headline_results_table.png`: slide-style KPI table.
- `01_growth_of_1.png`: walk-forward OOS vs full-sample growth of $1 for TY 1m.
- `02_underwater_curves.png`: OOS and full-sample drawdown curves for TY 1m.
- `03_quarterly_performance.png`: quarterly OOS profit and RoA for TY 1m.
- `04_parameter_path.png`: selected `L` and `S` through time for TY 1m.
- `05_parameter_frequency.png`: frequency of chosen `L` and `S` values for TY 1m.
- `06_trade_distributions.png`: TY 1m trade PnL and duration distributions.
- `07_reference_split_comparison.png`: TY 1m Matlab-style reference split comparison.
- `08_quarter_extremes.png`: best and worst TY 1m OOS quarters.
- `09_parity_table.png`: TY 1m Python/C++ agreement table.
- `10_interval_comparison_table.png`: headline 1m vs 5m comparison table.
- `11_growth_compare_1m_vs_5m.png`: 1m vs 5m growth comparison.
- `12_underwater_compare_1m_vs_5m.png`: 1m vs 5m underwater comparison.
- `13_oos_metric_compare_1m_vs_5m.png`: 1m vs 5m OOS metric bars.
- `14_quarterly_compare_1m_vs_5m.png`: 1m vs 5m quarterly OOS comparisons.
- `15_parameter_compare_1m_vs_5m.png`: 1m vs 5m parameter path comparisons.
- `16_distribution_compare_1m_vs_5m.png`: 1m vs 5m trade distribution comparisons.
- `17_parity_compare_1m_vs_5m.png`: 1m vs 5m parity table comparison.

Source: corrected outputs under `results_cpp_ty_1m`, `results_py_ty_1m`, and `results_compare/TY_5m`.
