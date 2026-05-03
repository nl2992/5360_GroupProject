from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import default_tf_grid, infer_bar_minutes_from_index
from .strategies import run_tf_backtest


@dataclass(frozen=True)
class ReferenceWindow:
    start: pd.Timestamp
    end: pd.Timestamp


def derive_reference_windows(
    df: pd.DataFrame,
    split_ratio: float = 0.70,
) -> tuple[ReferenceWindow, ReferenceWindow]:
    """Build a single Matlab-style IS/OOS split on trading-day boundaries."""
    if df.empty:
        raise ValueError("Cannot derive reference windows from an empty DataFrame.")
    ratio = float(split_ratio)
    if not (0.0 < ratio < 1.0):
        raise ValueError("split_ratio must be strictly between 0 and 1.")

    dates = pd.DatetimeIndex(df.index).normalize().unique()
    if len(dates) < 2:
        raise ValueError("Need at least two trading dates to derive reference windows.")

    split_pos = int(np.floor(len(dates) * ratio))
    split_pos = min(max(split_pos, 1), len(dates) - 1)

    in_sample = ReferenceWindow(start=pd.Timestamp(dates[0]), end=pd.Timestamp(dates[split_pos - 1]))
    out_sample = ReferenceWindow(start=pd.Timestamp(dates[split_pos]), end=pd.Timestamp(dates[-1]))
    return in_sample, out_sample


def matlab_style_date_bounds(
    df: pd.DataFrame,
    start: str | pd.Timestamp,
    end: str | pd.Timestamp,
    bars_back: int,
) -> tuple[int, int]:
    """Return 0-based [start_idx, end_exclusive) bounds matching main.m."""
    index = pd.DatetimeIndex(df.index)
    start_ts = pd.Timestamp(start)
    end_next = pd.Timestamp(end).normalize() + pd.Timedelta(days=1)

    start_idx = max(int(index.searchsorted(start_ts, side="left")), max(0, int(bars_back) - 1))
    end_exclusive = max(int(index.searchsorted(end_next, side="left")), int(bars_back))
    end_exclusive = min(end_exclusive, len(index))
    if end_exclusive <= start_idx:
        raise ValueError(
            f"Invalid Matlab-style bounds for {start_ts.date()} to {pd.Timestamp(end).date()}: "
            f"start_idx={start_idx}, end_exclusive={end_exclusive}"
        )
    return start_idx, end_exclusive


def summarise_reference_slice(
    result: dict[str, object],
    start_idx: int,
    end_exclusive: int,
) -> dict[str, float | int]:
    equity = np.asarray(result["Equity"], dtype=float)
    drawdown = np.asarray(result["Drawdown"], dtype=float)
    pnl = np.asarray(result["BarPnL"], dtype=float)
    trade_weights = np.asarray(result.get("TradeWeights", np.zeros_like(equity)), dtype=float)

    if not (0 <= start_idx < end_exclusive <= len(equity)):
        raise ValueError(
            f"Slice [{start_idx}, {end_exclusive}) is out of bounds for equity length {len(equity)}"
        )

    profit = float(equity[end_exclusive - 1] - equity[start_idx])
    worst_dd = float(abs(np.min(drawdown[start_idx:end_exclusive])))
    stdev = float(np.std(pnl[start_idx:end_exclusive], ddof=1)) if end_exclusive - start_idx > 1 else 0.0
    trade_units = float(trade_weights[start_idx:end_exclusive].sum())
    objective = profit / worst_dd if worst_dd > 0 else 0.0

    return {
        "start_idx": int(start_idx),
        "end_exclusive": int(end_exclusive),
        "Profit": profit,
        "WorstDrawDown": worst_dd,
        "StDev": stdev,
        "TradeUnits": trade_units,
        "Objective": objective,
    }


def build_reference_series_frame(
    df: pd.DataFrame,
    result: dict[str, object],
    in_sample_bounds: tuple[int, int],
    out_sample_bounds: tuple[int, int],
) -> pd.DataFrame:
    equity = np.asarray(result["Equity"], dtype=float)
    drawdown = np.asarray(result["Drawdown"], dtype=float)
    position = np.asarray(result["Position"], dtype=int)
    pnl = np.asarray(result["BarPnL"], dtype=float)
    trade_weights = np.asarray(result.get("TradeWeights", np.zeros_like(equity)), dtype=float)

    frame = pd.DataFrame(
        {
            "DateTime": pd.DatetimeIndex(df.index),
            "Close": df["Close"].to_numpy(dtype=float),
            "Equity": equity,
            "Drawdown": drawdown,
            "BarPnL": pnl,
            "Position": position,
            "TradeUnits": trade_weights,
        }
    )
    frame["Segment"] = "pre_is"
    is_start, is_end = in_sample_bounds
    oos_start, oos_end = out_sample_bounds
    frame.loc[is_start:is_end - 1, "Segment"] = "in_sample"
    frame.loc[oos_start:oos_end - 1, "Segment"] = "out_of_sample"
    return frame


def evaluate_reference_tf_grid(
    df: pd.DataFrame,
    ticker: str,
    *,
    in_sample: tuple[str | pd.Timestamp, str | pd.Timestamp] | None = None,
    out_sample: tuple[str | pd.Timestamp, str | pd.Timestamp] | None = None,
    bars_back: int = 17_001,
    tf_grid: dict[str, np.ndarray] | None = None,
    rebase_at_eval_start: bool = False,
    split_ratio: float = 0.70,
) -> pd.DataFrame:
    bar_minutes = infer_bar_minutes_from_index(df.index)
    tf_grid = default_tf_grid(ticker, quick=True, bar_minutes=bar_minutes) if tf_grid is None else tf_grid
    if in_sample is None or out_sample is None:
        auto_is, auto_oos = derive_reference_windows(df, split_ratio=split_ratio)
        in_sample = (auto_is.start, auto_is.end)
        out_sample = (auto_oos.start, auto_oos.end)
    is_bounds = matlab_style_date_bounds(df, in_sample[0], in_sample[1], bars_back)
    oos_bounds = matlab_style_date_bounds(df, out_sample[0], out_sample[1], bars_back)

    rows: list[dict[str, float | int | str]] = []
    for L in np.asarray(tf_grid["L"], dtype=int):
        for S in np.asarray(tf_grid["S"], dtype=float):
            result = run_tf_backtest(
                df,
                ticker,
                L=int(L),
                S=float(S),
                eval_start=0,
                eval_end=len(df),
                warmup_bars=int(bars_back),
                bars_back=int(bars_back),
                rebase_at_eval_start=rebase_at_eval_start,
            )
            if result.get("error"):
                continue

            is_stats = summarise_reference_slice(result, *is_bounds)
            oos_stats = summarise_reference_slice(result, *oos_bounds)
            rows.append(
                {
                    "Ticker": ticker.upper(),
                    "L": int(L),
                    "S": float(S),
                    "barsBack": int(bars_back),
                    "IS_Profit": is_stats["Profit"],
                    "IS_WorstDrawDown": is_stats["WorstDrawDown"],
                    "IS_StDev": is_stats["StDev"],
                    "IS_Trades": is_stats["TradeUnits"],
                    "IS_Objective": is_stats["Objective"],
                    "OOS_Profit": oos_stats["Profit"],
                    "OOS_WorstDrawDown": oos_stats["WorstDrawDown"],
                    "OOS_StDev": oos_stats["StDev"],
                    "OOS_Trades": oos_stats["TradeUnits"],
                    "OOS_Objective": oos_stats["Objective"],
                }
            )

    return pd.DataFrame(rows).sort_values(["IS_Objective", "OOS_Objective"], ascending=False).reset_index(drop=True)


def select_best_reference_params(surface_df: pd.DataFrame) -> dict[str, float | int]:
    if surface_df is None or len(surface_df) == 0:
        raise ValueError("Reference surface is empty.")
    top = surface_df.iloc[0]
    return {"L": int(top["L"]), "S": float(top["S"]), "barsBack": int(top["barsBack"])}


def run_reference_split(
    df: pd.DataFrame,
    ticker: str,
    *,
    in_sample: tuple[str | pd.Timestamp, str | pd.Timestamp] | None = None,
    out_sample: tuple[str | pd.Timestamp, str | pd.Timestamp] | None = None,
    bars_back: int = 17_001,
    tf_grid: dict[str, np.ndarray] | None = None,
    split_ratio: float = 0.70,
) -> dict[str, object]:
    if in_sample is None or out_sample is None:
        auto_is, auto_oos = derive_reference_windows(df, split_ratio=split_ratio)
        in_sample = (auto_is.start, auto_is.end)
        out_sample = (auto_oos.start, auto_oos.end)
    surface = evaluate_reference_tf_grid(
        df,
        ticker,
        in_sample=in_sample,
        out_sample=out_sample,
        bars_back=bars_back,
        tf_grid=tf_grid,
        split_ratio=split_ratio,
    )
    best = select_best_reference_params(surface)
    result = run_tf_backtest(
        df,
        ticker,
        L=int(best["L"]),
        S=float(best["S"]),
        eval_start=0,
        eval_end=len(df),
        warmup_bars=int(bars_back),
        bars_back=int(bars_back),
        rebase_at_eval_start=False,
    )
    is_bounds = matlab_style_date_bounds(df, in_sample[0], in_sample[1], bars_back)
    oos_bounds = matlab_style_date_bounds(df, out_sample[0], out_sample[1], bars_back)
    return {
        "surface": surface,
        "best_params": best,
        "result": result,
        "in_sample_bounds": is_bounds,
        "out_sample_bounds": oos_bounds,
        "in_sample_stats": summarise_reference_slice(result, *is_bounds),
        "out_sample_stats": summarise_reference_slice(result, *oos_bounds),
        "series": build_reference_series_frame(df, result, is_bounds, oos_bounds),
    }
