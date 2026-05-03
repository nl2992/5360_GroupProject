# TY 1-Minute Python vs C++ Fidelity Summary

These rows are extracted from the corrected Python replay cache for the dedicated TY 1-minute run.

## Python summary
| Market   |   BarMinutes | RunType                 | StartTime           | EndTime             |    Bars |   Periods |     L |    S |   NetProfit |   NetMaxDD |   NetRoA |   NetAnnReturnPct |   NetAnnVolPct |   NetSharpe |   ClosedTrades |
|:---------|-------------:|:------------------------|:--------------------|:--------------------|--------:|----------:|------:|-----:|------------:|-----------:|---------:|------------------:|---------------:|------------:|---------------:|
| TY       |            1 | walkforward_oos         | 1987-06-08 08:01:00 | 2026-03-05 13:00:00 | 3906000 |       155 |  6400 | 0.01 |    71952.4  |    15603.1 | 4.61142  |           1.52878 |        5.11045 |    0.299147 |            401 |
| TY       |            1 | full_sample             | 1983-01-03 08:01:00 | 2026-04-10 14:00:00 | 4319435 |         1 |  6400 | 0.01 |    97670.6  |    13827.5 | 7.0635   |           1.67608 |        4.15862 |    0.403037 |            772 |
| TY       |            1 | reference_in_sample     | 03/10/1983 09:21    | 06/26/2013 14:00    | 2994565 |         1 | 11200 | 0.04 |    91467.8  |    18981.4 | 4.81882  |         nan       |      nan       |  nan        |            157 |
| TY       |            1 | reference_out_of_sample | 06/27/2013 07:21    | 04/10/2026 14:00    | 1307870 |         1 | 11200 | 0.04 |     4408.25 |    33191   | 0.132815 |         nan       |      nan       |  nan        |             71 |
| TY       |            1 | reference_full          | 01/03/1983 08:01    | 04/10/2026 14:00    | 4319435 |         1 | 11200 | 0.04 |    95516.7  |    33191   | 2.87779  |         nan       |      nan       |  nan        |            228 |

## Python vs C++ parity
| Market   |   BarMinutes | RunType                 |   PythonProfit |   CppProfit |   PythonMaxDD |   CppMaxDD |   PythonRoA |   CppRoA |   PythonClosedTrades |   CppClosedTrades |   ProfitPctError |   MaxDDPctError |   RoAPctError |   TradesPctError | Within10Pct   |
|:---------|-------------:|:------------------------|---------------:|------------:|--------------:|-----------:|------------:|---------:|---------------------:|------------------:|-----------------:|----------------:|--------------:|-----------------:|:--------------|
| TY       |            1 | walkforward_oos         |       71952.4  |    71952.4  |       15603.1 |    15603.1 |    4.61142  | 4.61142  |                  401 |               401 |      2.02244e-15 |     3.73052e-15 |   4.45677e-08 |                0 | True          |
| TY       |            1 | full_sample             |       97670.6  |    97670.6  |       13827.5 |    13827.5 |    7.0635   | 7.0635   |                  772 |               772 |      5.36363e-15 |     2.10478e-15 |   2.48028e-08 |                0 | True          |
| TY       |            1 | reference_in_sample     |       91467.8  |    91467.8  |       18981.4 |    18981.4 |    4.81882  | 4.81882  |                  157 |               157 |      0           |     0           |   0           |                0 | True          |
| TY       |            1 | reference_out_of_sample |        4408.25 |     4408.25 |       33191   |    33191   |    0.132815 | 0.132815 |                   71 |                71 |      0           |     0           |   0           |                0 | True          |
| TY       |            1 | reference_full          |       95516.7  |    95516.7  |       33191   |    33191   |    2.87779  | 2.87779  |                  228 |               228 |      0           |     0           |   0           |                0 | True          |
