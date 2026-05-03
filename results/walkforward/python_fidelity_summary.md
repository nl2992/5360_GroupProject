# Python Replay Against Corrected C++ Outputs

This summary uses the cached Python artifacts replayed against the C++ engine for parity checks.

## Included runs
- TY 5-minute from `results/cpp_parity/`
- BTC 5-minute from `results/cpp_parity/`

## Summary table

| Market   |   BarMinutes | RunType                 | StartTime           | EndTime             |   Bars |   Periods |    L |    S |        NetProfit |   NetMaxDD |    NetRoA |   NetAnnReturnPct |   NetAnnVolPct |   NetSharpe |   ClosedTrades |
|:---------|-------------:|:------------------------|:--------------------|:--------------------|-------:|----------:|-----:|-----:|-----------------:|-----------:|----------:|------------------:|---------------:|------------:|---------------:|
| TY       |            5 | walkforward_oos         | 1987-06-08 08:05:00 | 2026-03-05 13:00:00 | 781200 |       155 | 1440 | 0.01 |  68335.5         |    15864.7 |  4.30739  |           1.45124 |        4.63742 |    0.312941 |            395 |
| TY       |            5 | full_sample             | 1983-01-03 08:05:00 | 2026-04-10 14:00:00 | 863887 |         1 | 1440 | 0.01 |  87864.7         |    17186.5 |  5.11244  |           1.54291 |        3.7955  |    0.40651  |            724 |
| TY       |            5 | reference_in_sample     | 12/07/1983 08:45    | 06/26/2013 14:00    | 585313 |         1 | 2240 | 0.04 |  89464.9         |    18903.2 |  4.73278  |         nan       |      nan       |  nan        |            154 |
| TY       |            5 | reference_out_of_sample | 06/27/2013 07:25    | 04/10/2026 14:00    | 261574 |         1 | 2240 | 0.04 |   4392.62        |    33128.5 |  0.132594 |         nan       |      nan       |  nan        |             71 |
| TY       |            5 | reference_full          | 01/03/1983 08:05    | 04/10/2026 14:00    | 863887 |         1 | 2240 | 0.04 |  93513.8         |    33128.5 |  2.82276  |         nan       |      nan       |  nan        |            225 |
| BTC      |            5 | walkforward_oos         | 2023-08-22 09:05:00 | 2026-02-12 22:30:00 | 176295 |         7 |  276 | 0.01 | 536397           |   131729   |  4.07197  |         112.701   |       37.484   |    3.00665  |           1094 |
| BTC      |            5 | full_sample             | 2017-12-18 00:35:00 | 2026-04-10 16:00:00 | 590436 |         1 |  276 | 0.01 |      1.73778e+06 |   131729   | 13.1921   |          50.285   |       11.1136  |    4.52462  |           5016 |
| BTC      |            5 | reference_in_sample     | 03/15/2018 23:15    | 10/12/2023 23:55    | 396339 |         1 |  552 | 0.01 | 744674           |    26967.2 | 27.614    |         nan       |      nan       |  nan        |           2325 |
| BTC      |            5 | reference_out_of_sample | 10/13/2023 00:00    | 04/10/2026 16:00    | 177097 |         1 |  552 | 0.01 | 449022           |   103824   |  4.32486  |         nan       |      nan       |  nan        |            936 |
| BTC      |            5 | reference_full          | 12/18/2017 00:35    | 04/10/2026 16:00    | 590436 |         1 |  552 | 0.01 |      1.1937e+06  |   103824   | 11.4974   |         nan       |      nan       |  nan        |           3261 |

## Python vs C++ comparison

| Market   |   BarMinutes | RunType                 |     PythonProfit |        CppProfit |   PythonMaxDD |   CppMaxDD |   PythonRoA |    CppRoA |   PythonClosedTrades |   CppClosedTrades |   ProfitPctError |   MaxDDPctError |   RoAPctError |   TradesPctError | Within10Pct   |
|:---------|-------------:|:------------------------|-----------------:|-----------------:|--------------:|-----------:|------------:|----------:|---------------------:|------------------:|-----------------:|----------------:|--------------:|-----------------:|:--------------|
| TY       |            5 | walkforward_oos         |  68335.5         |  68335.5         |       15864.7 |    15864.7 |    4.30739  |  4.30739  |                  395 |               395 |      1.70358e-15 |     1.8345e-15  |   6.4934e-08  |                0 | True          |
| TY       |            5 | full_sample             |  87864.7         |  87864.7         |       17186.5 |    17186.5 |    5.11244  |  5.11244  |                  724 |               724 |      5.63099e-15 |     3.38683e-15 |   3.18714e-08 |                0 | True          |
| TY       |            5 | reference_in_sample     |  89464.9         |  89464.9         |       18903.2 |    18903.2 |    4.73278  |  4.73278  |                  154 |               154 |      0           |     0           |   0           |                0 | True          |
| TY       |            5 | reference_out_of_sample |   4392.62        |   4392.62        |       33128.5 |    33128.5 |    0.132594 |  0.132594 |                   71 |                71 |      0           |     0           |   0           |                0 | True          |
| TY       |            5 | reference_full          |  93513.8         |  93513.8         |       33128.5 |    33128.5 |    2.82276  |  2.82276  |                  225 |               225 |      0           |     0           |   0           |                0 | True          |
| BTC      |            5 | walkforward_oos         | 536397           | 536397           |      131729   |   131729   |    4.07197  |  4.07197  |                 1094 |              1094 |      8.68128e-16 |     0           |   5.0719e-08  |                0 | True          |
| BTC      |            5 | full_sample             |      1.73778e+06 |      1.73778e+06 |      131729   |   131729   |   13.1921   | 13.1921   |                 5016 |              5016 |      0           |     0           |   1.51981e-08 |                0 | True          |
| BTC      |            5 | reference_in_sample     | 744674           | 744674           |       26967.2 |    26967.2 |   27.614    | 27.614    |                 2325 |              2325 |      0           |     0           |   0           |                0 | True          |
| BTC      |            5 | reference_out_of_sample | 449022           | 449022           |      103824   |   103824   |    4.32486  |  4.32486  |                  936 |               936 |      0           |     0           |   0           |                0 | True          |
| BTC      |            5 | reference_full          |      1.1937e+06  |      1.1937e+06  |      103824   |   103824   |   11.4974   | 11.4974   |                 3261 |              3261 |      0           |     0           |   0           |                0 | True          |

## Source fidelity notes
- TY uses TF Data point value = 1000, tick value = 15.625, slippage = 18.625, and the 07:20 to 14:00 session.
- BTC uses TF Data point value = 5, slippage = 25, and the Bloomberg DES 17:00 to 16:00 trading session.
