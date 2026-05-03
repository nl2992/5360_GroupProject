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

from mafn_engine import (  # noqa: E402
    choose_tf_story_configuration,
    default_tf_grid,
    get_market,
    load_ohlc,
    performance_from_ledger,
    prepare_analysis_frame,
    run_backtest,
    select_modal_configuration,
    validate_ohlc,
    walk_forward,
)
from mafn_engine.reference_backtest import run_reference_split  # noqa: E402


def parse_job(value: str) -> tuple[str, int]:
    ticker, interval = value.split(":", 1)
    return ticker.upper(), int(interval)


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


def compare_against_cpp(py_summary: pd.DataFrame, cpp_summary_path: Path, tolerance: float = 0.10) -> pd.DataFrame:
    if not cpp_summary_path.exists():
        return pd.DataFrame()

    cpp = pd.read_csv(cpp_summary_path)
    cpp = cpp.rename(columns={"RunType": "CppRunType"})
    cpp = cpp[cpp["RunType"].isin(["walkforward_oos", "full_sample", "reference_in_sample", "reference_out_of_sample", "reference_full"])] if "RunType" in cpp.columns else cpp
    rows: list[dict[str, object]] = []

    for _, py_row in py_summary.iterrows():
        if int(py_row["BarMinutes"]) != 5:
            continue
        match = cpp[
            (cpp["Market"].astype(str).str.upper() == str(py_row["Market"]).upper())
            & (cpp["RunType"].astype(str) == str(py_row["RunType"]))
        ]
        if match.empty:
            continue
        c = match.iloc[0]
        comp: dict[str, object] = {
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
            denom = abs(float(comp[right]))
            err = 0.0 if denom == 0 else abs(float(comp[left]) - float(comp[right])) / denom
            comp[key] = err
            ok = ok and err <= tolerance
        trade_denom = max(abs(int(comp["CppClosedTrades"])), 1)
        trade_err = abs(int(comp["PythonClosedTrades"]) - int(comp["CppClosedTrades"])) / trade_denom
        comp["TradesPctError"] = trade_err
        comp["Within10Pct"] = bool(ok and trade_err <= tolerance)
        rows.append(comp)

    return pd.DataFrame(rows)


def run_job(root: Path, out_dir: Path, ticker: str, interval: int, quick: bool) -> tuple[list[dict[str, object]], str]:
    market_dir = out_dir / f"{ticker}_{interval}m"
    market_dir.mkdir(parents=True, exist_ok=True)
    spec = get_market(ticker)
    print(f"[job] starting {ticker} {interval}m", flush=True)

    try:
        full_df = load_ohlc(str(root / "data"), ticker, fallback_synthetic=False, bar_minutes=interval)
    except FileNotFoundError as exc:
        note = f"{ticker} {interval}m: skipped because the requested source file is missing ({exc})."
        (market_dir / "status.txt").write_text(note + "\n", encoding="utf-8")
        print(f"[job] {note}", flush=True)
        return [], note

    validation = validate_ohlc(full_df)
    analysis_df = prepare_analysis_frame(full_df, ticker)
    tf_grid = default_tf_grid(ticker, quick=quick, bar_minutes=interval)
    wf_bundle = walk_forward(
        analysis_df,
        ticker,
        mode="tf",
        tf_grid=tf_grid,
        T_years=4,
        tau_quarters=1,
        quick=quick,
        verbose=False,
    )
    modal_cfg = select_modal_configuration(wf_bundle["params"])
    if modal_cfg is None:
        modal_cfg = choose_tf_story_configuration(ticker, tf_grid=tf_grid, params_df=wf_bundle["params"], bar_minutes=interval)
    full_sample = run_backtest(
        analysis_df,
        ticker,
        "tf",
        {"L": int(modal_cfg["L"]), "S": float(modal_cfg["S"])},
    )
    reference = run_reference_split(analysis_df, ticker, tf_grid=tf_grid)

    oos_metrics = performance_from_ledger(
        wf_bundle["ledger"],
        wf_bundle["equity"]["OOS_Equity"].to_numpy(dtype=float) if len(wf_bundle["equity"]) else np.array([spec.E0]),
        ticker,
        bar_minutes=interval,
    )
    full_metrics = performance_from_ledger(
        full_sample["Ledger"],
        np.asarray(full_sample["Equity"], dtype=float),
        ticker,
        bar_minutes=interval,
    )
    ref_full_metrics = performance_from_ledger(
        reference["result"]["Ledger"],
        np.asarray(reference["result"]["Equity"], dtype=float),
        ticker,
        bar_minutes=interval,
    )
    ref_is_metrics = {
        "Total Profit": float(reference["in_sample_stats"]["Profit"]),
        "Max Drawdown $": float(reference["in_sample_stats"]["WorstDrawDown"]),
        "Return on Account": float(reference["in_sample_stats"]["Objective"]),
        "Ann. Return %": np.nan,
        "Ann. Volatility %": np.nan,
        "Sharpe Ratio": np.nan,
        "Total Trades": float(reference["in_sample_stats"]["TradeUnits"]),
    }
    ref_oos_metrics = {
        "Total Profit": float(reference["out_sample_stats"]["Profit"]),
        "Max Drawdown $": float(reference["out_sample_stats"]["WorstDrawDown"]),
        "Return on Account": float(reference["out_sample_stats"]["Objective"]),
        "Ann. Return %": np.nan,
        "Ann. Volatility %": np.nan,
        "Sharpe Ratio": np.nan,
        "Total Trades": float(reference["out_sample_stats"]["TradeUnits"]),
    }

    wf_bundle["params"].to_csv(market_dir / f"{ticker}_{interval}m_walkforward_params.csv", index=False)
    wf_bundle["equity"].to_csv(
        market_dir / f"{ticker}_{interval}m_walkforward_equity.csv",
        index_label="DateTime",
    )
    wf_bundle["ledger"].to_csv(market_dir / f"{ticker}_{interval}m_walkforward_ledger.csv", index=False)
    pd.DataFrame([oos_metrics]).to_csv(market_dir / f"{ticker}_{interval}m_oos_metrics.csv", index=False)
    pd.DataFrame([full_metrics]).to_csv(market_dir / f"{ticker}_{interval}m_fullsample_metrics.csv", index=False)
    pd.DataFrame(
        {
            "DateTime": analysis_df.index,
            "Equity": np.asarray(full_sample["Equity"], dtype=float),
        }
    ).to_csv(market_dir / f"{ticker}_{interval}m_fullsample_equity.csv", index=False)
    full_sample["Ledger"].to_csv(market_dir / f"{ticker}_{interval}m_fullsample_ledger.csv", index=False)
    reference["surface"].to_csv(market_dir / f"{ticker}_{interval}m_reference_surface.csv", index=False)
    pd.DataFrame(
        [
            {"Segment": "in_sample", **reference["in_sample_stats"]},
            {"Segment": "out_of_sample", **reference["out_sample_stats"]},
        ]
    ).to_csv(market_dir / f"{ticker}_{interval}m_reference_summary.csv", index=False)
    reference["series"].to_csv(market_dir / f"{ticker}_{interval}m_reference_series.csv", index=False)
    pd.DataFrame([validation]).to_csv(market_dir / f"{ticker}_{interval}m_validation.csv", index=False)

    rows = [
        _summary_row(
            ticker,
            interval,
            "walkforward_oos",
            wf_bundle["equity"].index[0] if len(wf_bundle["equity"]) else analysis_df.index[0],
            wf_bundle["equity"].index[-1] if len(wf_bundle["equity"]) else analysis_df.index[-1],
            len(wf_bundle["equity"]),
            len(wf_bundle["params"]),
            int(modal_cfg["L"]),
            float(modal_cfg["S"]),
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
            int(modal_cfg["L"]),
            float(modal_cfg["S"]),
            full_metrics,
        ),
        _summary_row(
            ticker,
            interval,
            "reference_in_sample",
            reference["series"].loc[reference["series"]["Segment"] == "in_sample", "DateTime"].iloc[0],
            reference["series"].loc[reference["series"]["Segment"] == "in_sample", "DateTime"].iloc[-1],
            int((reference["series"]["Segment"] == "in_sample").sum()),
            1,
            int(reference["best_params"]["L"]),
            float(reference["best_params"]["S"]),
            ref_is_metrics,
        ),
        _summary_row(
            ticker,
            interval,
            "reference_out_of_sample",
            reference["series"].loc[reference["series"]["Segment"] == "out_of_sample", "DateTime"].iloc[0],
            reference["series"].loc[reference["series"]["Segment"] == "out_of_sample", "DateTime"].iloc[-1],
            int((reference["series"]["Segment"] == "out_of_sample").sum()),
            1,
            int(reference["best_params"]["L"]),
            float(reference["best_params"]["S"]),
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
            int(reference["best_params"]["L"]),
            float(reference["best_params"]["S"]),
            ref_full_metrics,
        ),
    ]
    note = (
        f"{ticker} {interval}m: loaded {len(full_df):,} raw bars and {len(analysis_df):,} session-filtered bars; "
        f"walk-forward produced {len(wf_bundle['params'])} OOS periods."
    )
    (market_dir / "status.txt").write_text(note + "\n", encoding="utf-8")
    print(f"[job] completed {ticker} {interval}m", flush=True)
    return rows, note


def build_markdown(summary_df: pd.DataFrame, notes: list[str], comparison_df: pd.DataFrame) -> str:
    lines = [
        "# Python Fidelity Backtest Summary",
        "",
        "This report uses the corrected Python trend-following engine with Bloomberg / TF Data market-definition fidelity fixes.",
        "",
        "## Run notes",
    ]
    lines.extend(f"- {note}" for note in notes)
    lines.extend(["", "## Summary table", summary_df.to_markdown(index=False), ""])
    if len(comparison_df):
        lines.extend(
            [
                "## Python vs corrected C++ 5-minute comparison",
                comparison_df.to_markdown(index=False),
                "",
                "Tolerance rule: values within 10% are considered acceptable; current corrected 5-minute rows should be materially tighter than that.",
            ]
        )
    else:
        lines.extend(["## Python vs corrected C++ 5-minute comparison", "Cannot confirm from existing outputs."])
    lines.extend(
        [
            "",
            "## Source fidelity notes",
            "- TY uses TF Data point value = 1000, tick value = 15.625, round-turn slippage = 18.625, session 07:20 to 14:00.",
            "- BTC uses TF Data point value = 5, round-turn slippage = 25, and Bloomberg DES session 17:00 to 16:00.",
            "- BTC metadata uses tick value = 25 because Bloomberg DES defines a 5-point minimum fluctuation and a 5-Bitcoin contract size.",
            "- BTC 1-minute backtests are only run if a valid BTC 1-minute futures CSV exists locally.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run corrected Python backtests and notebook executions.")
    parser.add_argument(
        "--job",
        action="append",
        default=["TY:5", "BTC:5", "BTC:1"],
        help="Market/interval job in the form TICKER:MINUTES. Defaults to TY:5, BTC:5, BTC:1.",
    )
    parser.add_argument("--out-dir", default="results/walkforward", help="Output directory relative to repo root.")
    parser.add_argument("--quick", action="store_true", default=True, help="Use the quick trend-following grid.")
    parser.add_argument("--no-execute-notebooks", action="store_true", help="Skip notebook execution.")
    parser.add_argument("--timeout", type=int, default=0, help="Per-notebook timeout in seconds; 0 means no timeout.")
    args = parser.parse_args()

    out_dir = ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    jobs = [parse_job(value) for value in args.job]
    summary_rows: list[dict[str, object]] = []
    notes: list[str] = []
    successful_jobs: list[tuple[str, int]] = []

    for ticker, interval in jobs:
        rows, note = run_job(ROOT, out_dir, ticker, interval, quick=bool(args.quick))
        notes.append(note)
        summary_rows.extend(rows)
        if rows:
            successful_jobs.append((ticker, interval))

    summary_df = pd.DataFrame(summary_rows)
    if len(summary_df):
        summary_df.to_csv(out_dir / "python_backtest_summary.csv", index=False)
        print(f"[summary] wrote {out_dir / 'python_backtest_summary.csv'}", flush=True)

    comparison_df = compare_against_cpp(summary_df, ROOT / "results" / "cpp_parity" / "tf_backtest_summary.csv")
    if len(comparison_df):
        comparison_df.to_csv(out_dir / "python_cpp_fidelity_comparison.csv", index=False)

    report = build_markdown(summary_df, notes, comparison_df)
    (out_dir / "python_fidelity_summary.md").write_text(report, encoding="utf-8")
    print(f"[summary] wrote {out_dir / 'python_fidelity_summary.md'}", flush=True)

    if not args.no_execute_notebooks:
        notebook_out = out_dir / "notebooks"
        for ticker, interval in successful_jobs:
            for notebook_name in ["02_Strategy_and_WalkForward.ipynb", "03_Performance_Metrics_Extended.ipynb"]:
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
