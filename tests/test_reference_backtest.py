from __future__ import annotations

import sys
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mafn_engine.reference_backtest import (
    derive_reference_windows,
    matlab_style_date_bounds,
    run_reference_split,
    summarise_reference_slice,
)
from mafn_engine.strategies import run_tf_backtest


class ReferenceBacktestTests(unittest.TestCase):
    def test_derive_reference_windows_splits_on_trading_day_boundaries(self) -> None:
        index = pd.date_range("2024-01-01 07:20:00", periods=80 * 10, freq="5min")
        df = pd.DataFrame({"Close": np.arange(len(index), dtype=float)}, index=index)
        in_sample, out_sample = derive_reference_windows(df, split_ratio=0.60)
        self.assertLess(in_sample.start, in_sample.end)
        self.assertLess(in_sample.end, out_sample.start)

    def test_matlab_style_date_bounds_match_main_m_indexing_convention(self) -> None:
        index = pd.date_range("2024-01-01 07:20:00", periods=3000, freq="5min")
        df = pd.DataFrame({"Close": np.arange(len(index), dtype=float)}, index=index)
        start_idx, end_exclusive = matlab_style_date_bounds(df, "2024-01-03", "2024-01-04", bars_back=10)
        self.assertEqual(start_idx, int(index.searchsorted(pd.Timestamp("2024-01-03"), side="left")))
        self.assertEqual(
            end_exclusive,
            int(index.searchsorted(pd.Timestamp("2024-01-05"), side="left")),
        )

    def test_reference_slice_uses_continuous_drawdown_and_trade_units(self) -> None:
        n = 140
        index = pd.date_range("2024-01-01 07:20:00", periods=n, freq="5min")
        close = np.full(n, 100.0)
        open_ = close.copy()
        high = close.copy()
        low = close.copy()

        high[110] = 101.0
        close[110] = 101.0

        low[111] = 94.0
        close[111] = 95.0
        high[111] = 101.0

        df = pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close}, index=index)
        result = run_tf_backtest(
            df,
            "TY",
            L=10,
            S=0.05,
            eval_start=0,
            eval_end=len(df),
            warmup_bars=20,
            bars_back=20,
            rebase_at_eval_start=False,
        )
        stats = summarise_reference_slice(result, 100, 120)
        self.assertGreater(stats["WorstDrawDown"], 0.0)
        self.assertGreater(stats["TradeUnits"], 0.0)

    def test_run_reference_split_returns_surface_and_segmented_series(self) -> None:
        periods = 288 * 90
        index = pd.date_range("2024-01-01 07:20:00", periods=periods, freq="5min")
        base = 110.0 + np.linspace(0.0, 2.0, periods)
        wave = 0.75 * np.sin(np.linspace(0.0, 8.0 * np.pi, periods))
        close = base + wave
        open_ = np.r_[close[0], close[:-1]]
        high = np.maximum(open_, close) + 0.1
        low = np.minimum(open_, close) - 0.1
        df = pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close}, index=index)

        bundle = run_reference_split(
            df,
            "TY",
            in_sample=("2024-01-01", "2024-02-15"),
            out_sample=("2024-02-16", "2024-03-15"),
            bars_back=100,
            tf_grid={"L": np.array([80, 100], dtype=int), "S": np.array([0.01, 0.02], dtype=float)},
        )
        self.assertGreater(len(bundle["surface"]), 0)
        self.assertIn("Segment", bundle["series"].columns)
        self.assertIn("in_sample", set(bundle["series"]["Segment"]))
        self.assertIn("out_of_sample", set(bundle["series"]["Segment"]))


if __name__ == "__main__":
    unittest.main()
