from __future__ import annotations

import argparse
import sys
from pathlib import Path

import nbformat
import numpy as np
import pandas as pd
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_DIR = ROOT / "notebooks"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mafn_engine import get_market, load_ohlc, performance_from_ledger, prepare_analysis_frame, validate_ohlc  # noqa: E402
from mafn_engine.reference_backtest import (  # noqa: E402
    build_reference_series_frame,
    matlab_style_date_bounds,
    summarise_reference_slice,
)
from mafn_engine.strategies import run_backtest, run_tf_backtest  # noqa: E402


def parse_job(value: str) -> tuple[str, int]:
    ticker, interval = value.split(":", 1)
    return ticker.upper(), int(interval)


def execute_parametrized_notebook(
    template_path: Path,
    out_path: Path,
    *,
    market: str,
    interval: int,
    results_cache_dir: Path,
    timeout: int | None = None,
) -> None:
    notebook = nbformat.read(template_path, as_version=4)
    notebook.cells[1].source = (
        f"MARKET_SELECT = '{market}'\n"
        "QUICK_TEST = True\n"
        "WALKFORWARD_MODE = 'tf'\n"
        "RUN_EXTENDED_SURFACE = False\n\n"
        f"DATA_INTERVAL_MINUTES = {int(interval)}\n"
        "DATA_FILE_OVERRIDE = None  # use repo data folder\n"
        f"RESULTS_CACHE_DIR = r'{results_cache_dir}'\n"
        "# Note: the repo currently contains TY-1minHLV.csv but no valid BTC-1minHLV.csv.\n"
    )
    client = NotebookClient(
        notebook,
        timeout=timeout,
        kernel_name="python3",
        resources={"metadata": {"path": str(template_path.parent)}},
    )
    client.execute()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(notebook, out_path)


def _concat_oos_equity(market_e0: float, chunks: list[pd.Series]) -> pd.DataFrame:
    if not chunks:
        return pd.DataFrame(columns=["OOS_PnL_cum", "OOS_Equity"])
    pnl = pd.concat(chunks)
    pnl = pnl[~pnl.index.duplicated(keep="first")]
    cum_pnl = pnl.cumsum()
    return pd.DataFrame({"OOS_PnL_cum": cum_pnl, "OOS_Equity": market_e0 + cum_pnl})


def _summary_row(
    ticker: str,
    interval: int,
    run_type: str,
    start_time: pd.Timestamp,
    end_time: pd.Timestamp,
    bars: int,
    periods: int,
    L: int,
    S: float,
    metrics: dict[str, float],
) -> dict[str, object]:
    return {
        "Market": ticker,
        "BarMinutes": int(interval),
        "RunType": run_type,
        "StartTime": pd.Timestamp(start_time).strftime("%m/%d/%Y %H:%M"),
        "EndTime": pd.Timestamp(end_time).strftime("%m/%d/%Y %H:%M"),
        "Bars": int(bars),
        "Periods": int(periods),
        "L": int(L),
        "S": float(S),
        "NetProfit": float(metrics["Total Profit"]),
        "NetMaxDD": float(metrics["Max Drawdown $"]),
        "NetRoA": float(metrics["Return on Account"]),
        "NetAnnReturnPct": float(metrics["Ann. Return %"]),
        "NetAnnVolPct": float(metrics["Ann. Volatility %"]),
        "NetSharpe": float(metrics["Sharpe Ratio"]),
        "ClosedTrades": int(metrics["Total Trades"]),
    }


def compare_against_cpp(py_summary: pd.DataFrame, cpp_summary_path: Path, tolerance: float = 0.10) -> pd.DataFrame:
    cpp = pd.read_csv(cpp_summary_path)
    rows: list[dict[str, object]] = []
    for _, py_row in py_summary.iterrows():
        match = cpp[
            (cpp["Market"].astype(str).str.upper() == str(py_row["Market"]).upper())
            & (cpp["RunType"].astype(str) == str(py_row["RunType"]))
        ]
        if match.empty:
            continue
        c = match.iloc[0]
        out = {
            "Market": py_row["Market"],
            "RunType": py_row["RunType"],
            "PythonProfit": float(py_row["NetProfit"]),
            "CppProfit": float(c["NetProfit"]),
            "PythonMaxDD": float(py_row["NetMaxDD"]),
            "CppMaxDD": float(c["NetMaxDD"]),
            "PythonRoA": float(py_row["NetRoA"]),
            "CppRoA": float(c["NetRoA"]),
            "PythonClosedTrades": int(py_row["ClosedTrades"]),
            "CppClosedTrades": int(c["ClosedTrades"]),
        }
        ok = True
        for left, right, key in [
            ("PythonProfit", "CppProfit", "ProfitPctError"),
            ("PythonMaxDD", "CppMaxDD", "MaxDDPctError"),
            ("PythonRoA", "CppRoA", "RoAPctError"),
        ]:
            denom = abs(float(out[right]))
            err = 0.0 if denom == 0 else abs(float(out[left]) - float(out[right])) / denom
            out[key] = err
            ok = ok and err <= tolerance
        trade_denom = max(abs(int(out["CppClosedTrades"])), 1)
        trade_err = abs(int(out["PythonClosedTrades"]) - int(out["CppClosedTrades"])) / trade_denom
        out["TradesPctError"] = trade_err
        out["Within10Pct"] = bool(ok and trade_err <= tolerance)
        rows.append(out)
    return pd.DataFrame(rows)


def replay_market(root: Path, cpp_dir: Path, out_dir: Path, ticker: str, interval: int) -> tuple[list[dict[str, object]], str]:
    market_dir = out_dir / f"{ticker}_{interval}m"
    market_dir.mkdir(parents=True, exist_ok=True)
    spec = get_market(ticker)
    print(f"[replay] starting {ticker} {interval}m", flush=True)

    try:
        full_df = load_ohlc(str(root / "data"), ticker, fallback_synthetic=False, bar_minutes=interval)
    except FileNotFoundError as exc:
        note = f"{ticker} {interval}m: skipped because the requested source file is missing ({exc})."
        (market_dir / "status.txt").write_text(note + "\n", encoding="utf-8")
        print(f"[replay] {note}", flush=True)
        return [], note

    periods_path = cpp_dir / ticker / f"{ticker}_tf_walkforward_periods.csv"
    cpp_summary_path = cpp_dir / "tf_backtest_summary.csv"
    if not periods_path.exists() or not cpp_summary_path.exists():
        note = f"{ticker} {interval}m: missing corrected C++ period or summary files in {cpp_dir}."
        (market_dir / "status.txt").write_text(note + "\n", encoding="utf-8")
        print(f"[replay] {note}", flush=True)
        return [], note

    validation = validate_ohlc(full_df)
    analysis_df = prepare_analysis_frame(full_df, ticker)
    periods = pd.read_csv(periods_path)
    cpp_summary = pd.read_csv(cpp_summary_path)
    index = pd.DatetimeIndex(analysis_df.index)

    params_rows: list[dict[str, object]] = []
    equity_chunks: list[pd.Series] = []
    ledger_chunks: list[pd.DataFrame] = []

    for row in periods.itertuples(index=False):
        L = int(row.L)
        S = float(row.S)
        oos_start = pd.to_datetime(row.OOSStart)
        oos_end = pd.to_datetime(row.OOSEnd)
        eval_start = int(index.searchsorted(oos_start, side="left"))
        eval_end = int(index.searchsorted(oos_end, side="right"))
        result = run_backtest(
            analysis_df,
            ticker,
            "tf",
            {"L": L, "S": S},
            eval_start=eval_start,
            eval_end=eval_end,
        )
        if result.get("error"):
            raise RuntimeError(f"Python replay failed for {ticker} period {row.Period}: {result}")

        params_rows.append(
            {
                "Period": int(row.Period),
                "Family": "tf",
                "IS_start": pd.to_datetime(row.ISStart),
                "IS_end": pd.to_datetime(row.ISEnd),
                "OOS_start": oos_start,
                "OOS_end": oos_end,
                "L": L,
                "S": S,
                "IS_Objective": float(row.ISNetObjective),
                "IS_Profit": float(row.ISNetProfit),
                "IS_MaxDD": float(row.ISNetMaxDD),
                "OOS_Objective": float(result["Objective"]),
                "OOS_Profit": float(result["Profit"]),
                "OOS_MaxDD": float(result["MaxDD"]),
                "OOS_Trades": int(result["NumTrades"]),
                "RoundTurnCost": float(result["RoundTurnCost"]),
            }
        )

        local_start = eval_start - int(result["SliceStart"])
        local_end = eval_end - int(result["SliceStart"])
        oos_equity = np.asarray(result["Equity"][local_start:local_end], dtype=float)
        oos_pnl = np.diff(np.r_[spec.E0, oos_equity])
        equity_chunks.append(pd.Series(oos_pnl, index=analysis_df.index[eval_start:eval_end], name="OOS_PnL"))

        if len(result["Ledger"]):
            ledger = result["Ledger"]
            ledger = ledger[ledger["is_oos"]].copy()
            ledger.insert(0, "Period", int(row.Period))
            ledger.insert(1, "Family", "tf")
            ledger["L"] = L
            ledger["S"] = S
            ledger_chunks.append(ledger)

    wf_params = pd.DataFrame(params_rows)
    wf_equity = _concat_oos_equity(spec.E0, equity_chunks)
    wf_ledger = pd.concat(ledger_chunks, ignore_index=True) if ledger_chunks else pd.DataFrame(columns=["Period", "Family"])
    oos_metrics = performance_from_ledger(
        wf_ledger,
        wf_equity["OOS_Equity"].to_numpy(dtype=float) if len(wf_equity) else np.array([spec.E0]),
        ticker,
        bar_minutes=interval,
    )

    full_row = cpp_summary[
        (cpp_summary["Market"].astype(str).str.upper() == ticker)
        & (cpp_summary["RunType"].astype(str) == "full_sample")
    ].iloc[0]
    full_result = run_backtest(
        analysis_df,
        ticker,
        "tf",
        {"L": int(full_row["L"]), "S": float(full_row["S"])},
    )
    full_metrics = performance_from_ledger(
        full_result["Ledger"],
        np.asarray(full_result["Equity"], dtype=float),
        ticker,
        bar_minutes=interval,
    )

    ref_row = cpp_summary[
        (cpp_summary["Market"].astype(str).str.upper() == ticker)
        & (cpp_summary["RunType"].astype(str) == "reference_in_sample")
    ].iloc[0]
    ref_result = run_tf_backtest(
        analysis_df,
        ticker,
        L=int(ref_row["L"]),
        S=float(ref_row["S"]),
        eval_start=0,
        eval_end=len(analysis_df),
        warmup_bars=17001,
        bars_back=17001,
        rebase_at_eval_start=False,
    )
    in_bounds = matlab_style_date_bounds(analysis_df, ref_row["StartTime"], ref_row["EndTime"], 17001)
    ref_oos_row = cpp_summary[
        (cpp_summary["Market"].astype(str).str.upper() == ticker)
        & (cpp_summary["RunType"].astype(str) == "reference_out_of_sample")
    ].iloc[0]
    out_bounds = matlab_style_date_bounds(analysis_df, ref_oos_row["StartTime"], ref_oos_row["EndTime"], 17001)
    ref_is_stats = summarise_reference_slice(ref_result, *in_bounds)
    ref_oos_stats = summarise_reference_slice(ref_result, *out_bounds)
    ref_series = build_reference_series_frame(analysis_df, ref_result, in_bounds, out_bounds)
    ref_full_metrics = performance_from_ledger(
        ref_result["Ledger"],
        np.asarray(ref_result["Equity"], dtype=float),
        ticker,
        bar_minutes=interval,
    )
    ref_is_metrics = {
        "Total Profit": float(ref_is_stats["Profit"]),
        "Max Drawdown $": float(ref_is_stats["WorstDrawDown"]),
        "Return on Account": float(ref_is_stats["Objective"]),
        "Ann. Return %": np.nan,
        "Ann. Volatility %": np.nan,
        "Sharpe Ratio": np.nan,
        "Total Trades": float(ref_is_stats["TradeUnits"]),
    }
    ref_oos_metrics = {
        "Total Profit": float(ref_oos_stats["Profit"]),
        "Max Drawdown $": float(ref_oos_stats["WorstDrawDown"]),
        "Return on Account": float(ref_oos_stats["Objective"]),
        "Ann. Return %": np.nan,
        "Ann. Volatility %": np.nan,
        "Sharpe Ratio": np.nan,
        "Total Trades": float(ref_oos_stats["TradeUnits"]),
    }

    wf_params.to_csv(market_dir / f"{ticker}_{interval}m_walkforward_params.csv", index=False)
    wf_equity.to_csv(market_dir / f"{ticker}_{interval}m_walkforward_equity.csv", index_label="DateTime")
    wf_ledger.to_csv(market_dir / f"{ticker}_{interval}m_walkforward_ledger.csv", index=False)
    pd.DataFrame([oos_metrics]).to_csv(market_dir / f"{ticker}_{interval}m_oos_metrics.csv", index=False)
    pd.DataFrame([full_metrics]).to_csv(market_dir / f"{ticker}_{interval}m_fullsample_metrics.csv", index=False)
    pd.DataFrame({"DateTime": analysis_df.index, "Equity": np.asarray(full_result["Equity"], dtype=float)}).to_csv(
        market_dir / f"{ticker}_{interval}m_fullsample_equity.csv",
        index=False,
    )
    full_result["Ledger"].to_csv(market_dir / f"{ticker}_{interval}m_fullsample_ledger.csv", index=False)
    pd.DataFrame(
        [
            {"Segment": "in_sample", **ref_is_stats},
            {"Segment": "out_of_sample", **ref_oos_stats},
        ]
    ).to_csv(market_dir / f"{ticker}_{interval}m_reference_summary.csv", index=False)
    ref_series.to_csv(market_dir / f"{ticker}_{interval}m_reference_series.csv", index=False)
    pd.DataFrame([validation]).to_csv(market_dir / f"{ticker}_{interval}m_validation.csv", index=False)

    rows = [
        _summary_row(
            ticker,
            interval,
            "walkforward_oos",
            wf_equity.index[0] if len(wf_equity) else analysis_df.index[0],
            wf_equity.index[-1] if len(wf_equity) else analysis_df.index[-1],
            len(wf_equity),
            len(wf_params),
            int(full_row["L"]) if ticker == "TY" else int(full_row["L"]),
            float(full_row["S"]),
            oos_metrics,
        ),
        _summary_row(
            ticker,
            interval,
            "full_sample",
            analysis_df.index[0],
            analysis_df.index[-1],
            len(analysis_df),
            1,
            int(full_row["L"]),
            float(full_row["S"]),
            full_metrics,
        ),
        _summary_row(
            ticker,
            interval,
            "reference_in_sample",
            ref_series.loc[ref_series["Segment"] == "in_sample", "DateTime"].iloc[0],
            ref_series.loc[ref_series["Segment"] == "in_sample", "DateTime"].iloc[-1],
            int((ref_series["Segment"] == "in_sample").sum()),
            1,
            int(ref_row["L"]),
            float(ref_row["S"]),
            ref_is_metrics,
        ),
        _summary_row(
            ticker,
            interval,
            "reference_out_of_sample",
            ref_series.loc[ref_series["Segment"] == "out_of_sample", "DateTime"].iloc[0],
            ref_series.loc[ref_series["Segment"] == "out_of_sample", "DateTime"].iloc[-1],
            int((ref_series["Segment"] == "out_of_sample").sum()),
            1,
            int(ref_row["L"]),
            float(ref_row["S"]),
            ref_oos_metrics,
        ),
        _summary_row(
            ticker,
            interval,
            "reference_full",
            analysis_df.index[0],
            analysis_df.index[-1],
            len(analysis_df),
            1,
            int(ref_row["L"]),
            float(ref_row["S"]),
            ref_full_metrics,
        ),
    ]
    note = (
        f"{ticker} {interval}m: replayed {len(wf_params)} corrected C++ walk-forward periods through Python, "
        f"with {len(full_df):,} raw bars and {len(analysis_df):,} session-filtered bars."
    )
    (market_dir / "status.txt").write_text(note + "\n", encoding="utf-8")
    print(f"[replay] completed {ticker} {interval}m", flush=True)
    return rows, note


def build_markdown(summary_df: pd.DataFrame, notes: list[str], comparison_df: pd.DataFrame) -> str:
    lines = [
        "# Python Replay Against Corrected C++ Outputs",
        "",
        "This report replays the corrected C++ period selections through the fixed Python engine so the notebook layer can consume aligned Python artifacts.",
        "",
        "## Run notes",
    ]
    lines.extend(f"- {note}" for note in notes)
    lines.extend(["", "## Summary table", summary_df.to_markdown(index=False), ""])
    if len(comparison_df):
        lines.extend(["## Python vs corrected C++ comparison", comparison_df.to_markdown(index=False), ""])
    lines.extend(
        [
            "## Source fidelity notes",
            "- TY uses TF Data point value = 1000, tick value = 15.625, slippage = 18.625, and the 07:20 to 14:00 session.",
            "- BTC uses TF Data point value = 5, slippage = 25, and the Bloomberg DES 17:00 to 16:00 trading session.",
            "- TY 1-minute uses the same official TY market definition, scaled to 1-minute bars with 400 active bars per session.",
            "- BTC 1-minute backtests remain unavailable until a valid BTC 1-minute futures CSV is supplied locally.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay corrected C++ outputs through the fixed Python engine.")
    parser.add_argument("--job", action="append", default=[], help="Job like TICKER:MINUTES. Pass once per market/interval.")
    parser.add_argument("--cpp-results-dir", default="results/cpp_parity", help="Corrected C++ output directory relative to repo root.")
    parser.add_argument("--out-dir", default="results/walkforward", help="Output directory relative to repo root.")
    parser.add_argument("--no-execute-notebooks", action="store_true", help="Skip executing notebooks against the cached replay outputs.")
    parser.add_argument("--include-master-notebook", action="store_true", help="Also execute 00_Master_Pipeline.ipynb after replaying the cached results.")
    parser.add_argument("--timeout", type=int, default=0, help="Per-notebook timeout in seconds; 0 means no timeout.")
    args = parser.parse_args()

    cpp_dir = ROOT / args.cpp_results_dir
    out_dir = ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    summary_rows: list[dict[str, object]] = []
    notes: list[str] = []
    successful_jobs: list[tuple[str, int]] = []

    jobs = [parse_job(value) for value in args.job] if args.job else [("TY", 5), ("BTC", 5), ("BTC", 1)]

    for ticker, interval in jobs:
        rows, note = replay_market(ROOT, cpp_dir, out_dir, ticker, interval)
        notes.append(note)
        summary_rows.extend(rows)
        if rows:
            successful_jobs.append((ticker, interval))

    summary_df = pd.DataFrame(summary_rows)
    if len(summary_df):
        summary_df.to_csv(out_dir / "python_backtest_summary.csv", index=False)
    comparison_df = compare_against_cpp(summary_df, cpp_dir / "tf_backtest_summary.csv")
    if len(comparison_df):
        comparison_df.to_csv(out_dir / "python_cpp_fidelity_comparison.csv", index=False)
    (out_dir / "python_fidelity_summary.md").write_text(build_markdown(summary_df, notes, comparison_df), encoding="utf-8")

    if not args.no_execute_notebooks:
        notebook_out = out_dir / "notebooks"
        notebook_names = [
            "02_Strategy_and_WalkForward.ipynb",
            "03_Performance_Metrics_Extended.ipynb",
        ]
        if args.include_master_notebook:
            notebook_names.insert(0, "00_Master_Pipeline.ipynb")
        for ticker, interval in successful_jobs:
            for notebook_name in notebook_names:
                template = NOTEBOOK_DIR / notebook_name
                out_path = notebook_out / f"{template.stem}_{ticker}_{interval}m_executed.ipynb"
                print(f"[notebook] executing {notebook_name} for {ticker} {interval}m", flush=True)
                execute_parametrized_notebook(
                    template,
                    out_path,
                    market=ticker,
                    interval=interval,
                    results_cache_dir=out_dir,
                    timeout=None if args.timeout == 0 else args.timeout,
                )
                print(f"[notebook] wrote {out_path}", flush=True)


if __name__ == "__main__":
    main()
