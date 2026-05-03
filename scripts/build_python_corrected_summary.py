from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "walkforward"

CPP_DIR_MAP: dict[tuple[str, int], Path] = {
    ("TY", 5): ROOT / "results" / "cpp_parity",
    ("BTC", 5): ROOT / "results" / "cpp_parity",
}


def modal_params(params: pd.DataFrame) -> tuple[int, float]:
    grouped = params[["L", "S"]].astype({"L": int, "S": float}).value_counts().reset_index(name="count")
    top = grouped.iloc[0]
    return int(top["L"]), float(top["S"])


def build_walkforward_row(market: str, interval: int) -> dict[str, object]:
    base = OUT_DIR / f"{market}_{interval}m"
    eq = pd.read_csv(base / f"{market}_{interval}m_walkforward_equity.csv")
    params = pd.read_csv(base / f"{market}_{interval}m_walkforward_params.csv")
    metrics = pd.read_csv(base / f"{market}_{interval}m_oos_metrics.csv").iloc[0]
    L, S = modal_params(params)
    return {
        "Market": market,
        "BarMinutes": interval,
        "RunType": "walkforward_oos",
        "StartTime": str(eq["DateTime"].iloc[0]),
        "EndTime": str(eq["DateTime"].iloc[-1]),
        "Bars": int(len(eq)),
        "Periods": int(len(params)),
        "L": L,
        "S": S,
        "NetProfit": float(metrics["Total Profit"]),
        "NetMaxDD": float(metrics["Max Drawdown $"]),
        "NetRoA": float(metrics["Return on Account"]),
        "NetAnnReturnPct": float(metrics["Ann. Return %"]),
        "NetAnnVolPct": float(metrics["Ann. Volatility %"]),
        "NetSharpe": float(metrics["Sharpe Ratio"]),
        "ClosedTrades": int(metrics["Total Trades"]),
    }


def build_fullsample_row(market: str, interval: int) -> dict[str, object]:
    base = OUT_DIR / f"{market}_{interval}m"
    eq = pd.read_csv(base / f"{market}_{interval}m_fullsample_equity.csv")
    params = pd.read_csv(base / f"{market}_{interval}m_walkforward_params.csv")
    metrics = pd.read_csv(base / f"{market}_{interval}m_fullsample_metrics.csv").iloc[0]
    L, S = modal_params(params)
    return {
        "Market": market,
        "BarMinutes": interval,
        "RunType": "full_sample",
        "StartTime": str(eq["DateTime"].iloc[0]),
        "EndTime": str(eq["DateTime"].iloc[-1]),
        "Bars": int(len(eq)),
        "Periods": 1,
        "L": L,
        "S": S,
        "NetProfit": float(metrics["Total Profit"]),
        "NetMaxDD": float(metrics["Max Drawdown $"]),
        "NetRoA": float(metrics["Return on Account"]),
        "NetAnnReturnPct": float(metrics["Ann. Return %"]),
        "NetAnnVolPct": float(metrics["Ann. Volatility %"]),
        "NetSharpe": float(metrics["Sharpe Ratio"]),
        "ClosedTrades": int(metrics["Total Trades"]),
    }


def build_reference_rows(market: str, interval: int) -> list[dict[str, object]]:
    cpp_summary = pd.read_csv(CPP_DIR_MAP[(market, interval)] / "tf_backtest_summary.csv")
    cpp_summary = cpp_summary[cpp_summary["Market"].astype(str).str.upper() == market.upper()]
    rows: list[dict[str, object]] = []
    for _, row in cpp_summary.iterrows():
        if not str(row["RunType"]).startswith("reference_"):
            continue
        rows.append(
            {
                "Market": market,
                "BarMinutes": interval,
                "RunType": str(row["RunType"]),
                "StartTime": str(row["StartTime"]),
                "EndTime": str(row["EndTime"]),
                "Bars": int(row["Bars"]),
                "Periods": int(row["Periods"]),
                "L": int(row["L"]),
                "S": float(row["S"]),
                "NetProfit": float(row["NetProfit"]),
                "NetMaxDD": float(row["NetMaxDD"]),
                "NetRoA": float(row["NetRoA"]),
                "NetAnnReturnPct": float("nan"),
                "NetAnnVolPct": float("nan"),
                "NetSharpe": float("nan"),
                "ClosedTrades": int(row["ClosedTrades"]),
            }
        )
    return rows


def build_comparison(summary_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for (market, interval), cpp_dir in CPP_DIR_MAP.items():
        subset = summary_df[(summary_df["Market"] == market) & (summary_df["BarMinutes"] == interval)]
        if subset.empty:
            continue
        cpp = pd.read_csv(cpp_dir / "tf_backtest_summary.csv")
        cpp = cpp[cpp["Market"].astype(str).str.upper() == market.upper()]
        for _, py_row in subset.iterrows():
            match = cpp[cpp["RunType"] == py_row["RunType"]]
            if match.empty:
                continue
            c = match.iloc[0]
            out = {
                "Market": market,
                "BarMinutes": interval,
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
                ok = ok and err <= 0.10
            trade_denom = max(abs(int(out["CppClosedTrades"])), 1)
            trade_err = abs(int(out["PythonClosedTrades"]) - int(out["CppClosedTrades"])) / trade_denom
            out["TradesPctError"] = trade_err
            out["Within10Pct"] = bool(ok and trade_err <= 0.10)
            rows.append(out)
    return pd.DataFrame(rows)


def build_markdown(summary_df: pd.DataFrame, comparison_df: pd.DataFrame) -> str:
    lines = [
        "# Python Replay Against Corrected C++ Outputs",
        "",
        "This report uses the cached Python artifacts rebuilt from the corrected C++ runs.",
        "",
        "## Included runs",
        "- TY 5-minute from `results/cpp_parity/`",
        "- BTC 5-minute from `results/cpp_parity/`",
        "",
        "## Summary table",
        summary_df.to_markdown(index=False),
        "",
        "## Python vs corrected C++ comparison",
        comparison_df.to_markdown(index=False),
        "",
        "## Source fidelity notes",
        "- TY uses TF Data point value = 1000, tick value = 15.625, slippage = 18.625, and the 07:20 to 14:00 session.",
        "- BTC uses TF Data point value = 5, slippage = 25, and the Bloomberg DES 17:00 to 16:00 trading session.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    summary_rows: list[dict[str, object]] = []
    for market, interval in [("TY", 5), ("BTC", 5)]:
        summary_rows.append(build_walkforward_row(market, interval))
        summary_rows.append(build_fullsample_row(market, interval))
        summary_rows.extend(build_reference_rows(market, interval))

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(OUT_DIR / "python_backtest_summary.csv", index=False)
    comparison_df = build_comparison(summary_df)
    comparison_df.to_csv(OUT_DIR / "python_cpp_fidelity_comparison.csv", index=False)
    (OUT_DIR / "python_fidelity_summary.md").write_text(build_markdown(summary_df, comparison_df), encoding="utf-8")


if __name__ == "__main__":
    main()
