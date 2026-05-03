from __future__ import annotations

import sys
import tempfile
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mafn_engine.diagnostics import choose_regime_family, load_ohlc, summarise_trend_profile
from mafn_engine.config import default_tf_grid, professor_reference_tau
from mafn_engine.metrics import drawdown_family
from mafn_engine.strategies import run_tf_backtest
from mafn_engine.walkforward import _concat_oos_equity, select_modal_configuration
from mafn_engine.workflow import build_market_story, build_pair_story, choose_tf_story_configuration


class EngineSmokeTests(unittest.TestCase):
    @staticmethod
    def _make_session_frame(start: str, periods: int, price0: float = 100.0) -> pd.DataFrame:
        index = pd.date_range(start, periods=periods, freq="5min")
        ramp = np.linspace(0.0, 1.0, periods)
        wave = 0.4 * np.sin(np.linspace(0.0, 10.0 * np.pi, periods))
        close = price0 + ramp + wave
        open_ = np.r_[close[0], close[:-1]]
        high = np.maximum(open_, close) + 0.05
        low = np.minimum(open_, close) - 0.05
        return pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close}, index=index)

    def test_load_ohlc_accepts_direct_csv_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "TY-5minHLV.csv"
            csv_path.write_text(
                "Date,Time,Open,High,Low,Close,Volume\n"
                "01/03/2024,07:20,110,111,109,110.5,10\n"
                "01/03/2024,07:25,110.5,111.5,110,111,12\n",
                encoding="utf-8",
            )
            df = load_ohlc(str(csv_path), "TY", fallback_synthetic=False)
            self.assertEqual(len(df), 2)
            self.assertListEqual(list(df.columns), ["Open", "High", "Low", "Close", "Volume"])

    def test_drawdown_family_uses_positive_magnitudes(self) -> None:
        equity = np.array([100.0, 120.0, 90.0, 95.0, 130.0])
        dd = drawdown_family(equity, alpha=0.4)
        self.assertAlmostEqual(dd["MaxDD"], 30.0)
        self.assertAlmostEqual(dd["AvgDD"], 11.0)
        self.assertTrue(np.all(dd["Underwater"] <= 0.0))

    def test_concat_oos_equity_expects_incremental_pnl(self) -> None:
        idx1 = pd.date_range("2020-01-01", periods=3, freq="D")
        idx2 = pd.date_range("2020-01-04", periods=2, freq="D")
        chunk1 = pd.Series([10.0, -5.0, 3.0], index=idx1)
        chunk2 = pd.Series([4.0, -2.0], index=idx2)
        equity = _concat_oos_equity(100.0, [chunk1, chunk2])
        self.assertAlmostEqual(float(equity["OOS_PnL_cum"].iloc[-1]), 10.0)
        self.assertAlmostEqual(float(equity["OOS_Equity"].iloc[-1]), 110.0)

    def test_select_modal_configuration_handles_mixed_tf_mr_rows(self) -> None:
        params = pd.DataFrame(
            [
                {"Family": "tf", "L": 1000, "S": 0.01, "N1": np.nan, "N2": np.nan},
                {"Family": "mr", "N1": 1.0, "N2": 0.5, "VolLen": 48, "MALen": 48, "StpPct": 0.02},
                {"Family": "mr", "N1": 1.0, "N2": 0.5, "VolLen": 48, "MALen": 48, "StpPct": 0.02},
            ]
        )
        modal = select_modal_configuration(params)
        self.assertEqual(
            modal,
            {"family": "mr", "N1": 1.0, "N2": 0.5, "VolLen": 48, "MALen": 48, "StpPct": 0.02},
        )

    def test_regime_choice_defaults_to_tf_when_no_significant_votes(self) -> None:
        vr = pd.DataFrame(
            {
                "significant": [False, False],
                "pattern": ["mean_revert", "trend"],
                "VR": [0.98, 1.01],
            }
        )
        pr = pd.DataFrame(
            {
                "significant": [False, False],
                "pattern": ["mean_revert", "trend"],
                "spearman_rho": [-0.1, 0.1],
            }
        )
        choice = choose_regime_family(vr, pr)
        self.assertEqual(choice["family"], "tf")
        self.assertEqual(choice["reason"], "weak-evidence default")

    def test_trend_profile_can_favor_slow_tf_even_when_short_horizon_is_weak(self) -> None:
        vr = pd.DataFrame(
            {
                "ticker": ["TY"] * 6,
                "k": [24, 48, 80, 160, 800, 1600],
                "time_scale": ["2.0hr", "4.0hr", "1.0sess", "2.0sess", "10.0sess", "20.0sess"],
                "VR": [0.93, 0.95, 0.97, 0.99, 1.03, 1.08],
                "significant": [False, False, False, False, True, True],
                "pattern": ["mean_revert", "mean_revert", "mean_revert", "mean_revert", "trend", "trend"],
            }
        )
        pr = pd.DataFrame(
            {
                "push_bars": [24, 48, 80, 160, 800, 1600],
                "push_scale": ["2.0hr", "4.0hr", "1.0sess", "2.0sess", "10.0sess", "20.0sess"],
                "spearman_rho": [-0.20, -0.12, -0.05, 0.01, 0.09, 0.18],
                "significant": [False, False, False, False, True, True],
            }
        )
        profile = summarise_trend_profile(vr, pr, ticker="TY")
        self.assertEqual(profile["assignment_family"], "tf")
        self.assertTrue(profile["trend_strengthens_with_horizon"])
        self.assertEqual(profile["tf_speed_bias"], "slow")
        self.assertGreater(profile["vr_long_minus_short"], 0.0)

    def test_professor_reference_taus_match_requested_markets(self) -> None:
        self.assertEqual(professor_reference_tau("TY"), 1440)
        self.assertEqual(professor_reference_tau("BTC"), 1104)

    def test_tf_story_configuration_defaults_to_professor_horizon(self) -> None:
        cfg = choose_tf_story_configuration("TY", tf_grid=default_tf_grid("TY", quick=True), params_df=pd.DataFrame())
        self.assertEqual(cfg["family"], "tf")
        self.assertEqual(cfg["L"], 1440)

    def test_market_story_and_pair_story_expose_narrative_bundles(self) -> None:
        ty_idx = []
        for day in pd.date_range("2024-01-02", periods=45, freq="B"):
            ty_idx.extend(pd.date_range(f"{day.date()} 07:20:00", periods=80, freq="5min"))
        ty_df = self._make_session_frame(str(ty_idx[0]), len(ty_idx), price0=110.0)
        ty_df.index = pd.DatetimeIndex(ty_idx)

        btc_df = self._make_session_frame("2024-01-01 00:00:00", 3200, price0=20000.0)

        ty_story = build_market_story("TY", data=ty_df, include_walkforward=False)
        self.assertEqual(ty_story["tf_config"]["L"], 1440)
        self.assertIn("longer-horizon trend-following", " ".join(ty_story["narrative_lines"]))
        self.assertIn("full sample", " ".join(ty_story["narrative_lines"]))

        pair = build_pair_story(
            ("TY", "BTC"),
            data_map={"TY": ty_df, "BTC": btc_df},
            include_walkforward=False,
        )
        self.assertEqual(pair["tickers"], ["TY", "BTC"])
        self.assertListEqual(pair["diagnostics_df"]["Ticker"].tolist(), ["TY", "BTC"])
        self.assertEqual(pair["strategy_df"]["Story Family"].tolist(), ["tf", "tf"])

    def test_tf_ledger_reconciles_when_final_position_is_flat(self) -> None:
        n = 120
        index = pd.date_range("2020-01-01 07:20:00", periods=n, freq="5min")
        close = np.full(n, 100.0)
        high = np.full(n, 100.0)
        low = np.full(n, 100.0)
        open_ = np.full(n, 100.0)

        close[105] = 101.0
        high[105] = 101.0
        low[105] = 100.0
        open_[105] = 100.0

        close[106] = 95.0
        high[106] = 101.0
        low[106] = 94.0
        open_[106] = 101.0

        df = pd.DataFrame(
            {"Open": open_, "High": high, "Low": low, "Close": close},
            index=index,
        )

        result = run_tf_backtest(df, "TY", L=10, S=0.05)
        self.assertFalse(result["error"])
        self.assertEqual(int(result["Position"][-1]), 0)
        ledger = result["Ledger"]
        self.assertGreater(len(ledger), 0)
        self.assertAlmostEqual(result["Profit"], float(ledger["pnl"].sum()), places=6)


if __name__ == "__main__":
    unittest.main()
