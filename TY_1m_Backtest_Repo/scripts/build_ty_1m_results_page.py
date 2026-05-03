from __future__ import annotations

from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CPP_DIR = ROOT / "results_cpp_ty_1m"
PY_DIR = ROOT / "results_py_ty_1m"
TY_DIR = PY_DIR / "TY_1m"
COMPARE_DIR = ROOT / "results_compare" / "TY_5m"
FIG_DIR = ROOT / "results_report" / "figures"
REPORT_MD = ROOT / "TY_1m_results_page.md"


plt.style.use("seaborn-v0_8-whitegrid")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_fig(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=180, bbox_inches="tight")
    plt.close()


def format_money(x: float) -> str:
    return f"${x:,.2f}"


def format_ratio(x: float) -> str:
    return f"{x:.3f}"


def image_md(path: Path, alt: str) -> str:
    return f"![{alt}]({path.resolve()})"


def table_figure(df: pd.DataFrame, title: str, path: Path, font_size: int = 10) -> None:
    fig_h = max(2.5, 0.55 * (len(df) + 2))
    fig, ax = plt.subplots(figsize=(14, fig_h))
    ax.axis("off")
    ax.set_title(title, fontsize=15, fontweight="bold", loc="left")
    tbl = ax.table(
        cellText=df.values,
        colLabels=df.columns,
        cellLoc="center",
        loc="center",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(font_size)
    tbl.scale(1, 1.35)
    for (row, col), cell in tbl.get_celld().items():
        if row == 0:
            cell.set_text_props(weight="bold", color="white")
            cell.set_facecolor("#1F4E79")
        else:
            cell.set_facecolor("#F7F9FB" if row % 2 else "#EAF1F8")
        cell.set_edgecolor("#B8C2CC")
    save_fig(path)


def load_inputs() -> dict[str, pd.DataFrame]:
    return {
        "cpp_summary": pd.read_csv(CPP_DIR / "tf_backtest_summary.csv"),
        "oos_metrics": pd.read_csv(TY_DIR / "TY_1m_oos_metrics.csv"),
        "full_metrics": pd.read_csv(TY_DIR / "TY_1m_fullsample_metrics.csv"),
        "reference_summary": pd.read_csv(TY_DIR / "TY_1m_reference_summary.csv"),
        "params": pd.read_csv(TY_DIR / "TY_1m_walkforward_params.csv"),
        "oos_equity": pd.read_csv(TY_DIR / "TY_1m_walkforward_equity.csv", parse_dates=["DateTime"]),
        "full_equity": pd.read_csv(TY_DIR / "TY_1m_fullsample_equity.csv", parse_dates=["DateTime"]),
        "oos_ledger": pd.read_csv(TY_DIR / "TY_1m_walkforward_ledger.csv"),
        "full_ledger": pd.read_csv(TY_DIR / "TY_1m_fullsample_ledger.csv"),
        "parity": pd.read_csv(PY_DIR / "python_cpp_fidelity_comparison.csv"),
        "five_oos_metrics": pd.read_csv(COMPARE_DIR / "TY_5m_oos_metrics.csv"),
        "five_full_metrics": pd.read_csv(COMPARE_DIR / "TY_5m_fullsample_metrics.csv"),
        "five_reference_summary": pd.read_csv(COMPARE_DIR / "TY_5m_reference_summary.csv"),
        "five_params": pd.read_csv(COMPARE_DIR / "TY_5m_walkforward_params.csv"),
        "five_oos_equity": pd.read_csv(COMPARE_DIR / "TY_5m_walkforward_equity.csv", parse_dates=["DateTime"]),
        "five_full_equity": pd.read_csv(COMPARE_DIR / "TY_5m_fullsample_equity.csv", parse_dates=["DateTime"]),
        "five_oos_ledger": pd.read_csv(COMPARE_DIR / "TY_5m_walkforward_ledger.csv"),
        "five_full_ledger": pd.read_csv(COMPARE_DIR / "TY_5m_fullsample_ledger.csv"),
        "five_parity": pd.read_csv(COMPARE_DIR / "python_cpp_fidelity_comparison_ty_5m.csv"),
    }


def build_headline_table(cpp_summary: pd.DataFrame) -> pd.DataFrame:
    keep = cpp_summary[[
        "RunType",
        "L",
        "S",
        "NetProfit",
        "NetMaxDD",
        "NetRoA",
        "ClosedTrades",
        "TotalCost",
        "TurnoverContracts",
    ]].copy()
    keep["NetProfit"] = keep["NetProfit"].map(format_money)
    keep["NetMaxDD"] = keep["NetMaxDD"].map(format_money)
    keep["NetRoA"] = keep["NetRoA"].map(format_ratio)
    keep["S"] = keep["S"].map(lambda x: f"{x:.3f}")
    keep["TotalCost"] = keep["TotalCost"].map(format_money)
    keep["TurnoverContracts"] = keep["TurnoverContracts"].map(lambda x: f"{x:,.0f}")
    keep = keep.rename(columns={"RunType": "Run Type", "L": "Lookback", "S": "Stop"})
    return keep


def plot_growth(oos_eq: pd.DataFrame, full_eq: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(12.5, 5.5))
    ax.plot(oos_eq["DateTime"], oos_eq["OOS_Equity"] / 100000.0, label="Walk-forward OOS", color="#1F77B4", lw=1.4)
    ax.plot(full_eq["DateTime"], full_eq["Equity"] / 100000.0, label="Full sample", color="#D17A22", lw=1.1, alpha=0.85)
    ax.set_title("TY 1-Minute Growth of $1", fontsize=15, fontweight="bold")
    ax.set_ylabel("Growth of $1")
    ax.legend(frameon=False)
    ax.xaxis.set_major_locator(mdates.YearLocator(5))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.grid(alpha=0.25)
    save_fig(FIG_DIR / "01_growth_of_1.png")


def plot_underwater(oos_eq: pd.DataFrame, full_eq: pd.DataFrame) -> None:
    oos_dd = oos_eq["OOS_Equity"] / oos_eq["OOS_Equity"].cummax() - 1.0
    full_dd = full_eq["Equity"] / full_eq["Equity"].cummax() - 1.0
    fig, axes = plt.subplots(2, 1, figsize=(12.5, 7.5), sharex=False)
    axes[0].fill_between(oos_eq["DateTime"], oos_dd, 0, color="#B22222", alpha=0.35)
    axes[0].plot(oos_eq["DateTime"], oos_dd, color="#8B1E1E", lw=0.9)
    axes[0].set_title("TY 1-Minute Walk-Forward Underwater Curve", fontsize=14, fontweight="bold")
    axes[0].set_ylabel("Drawdown")
    axes[0].xaxis.set_major_locator(mdates.YearLocator(5))
    axes[0].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    axes[1].fill_between(full_eq["DateTime"], full_dd, 0, color="#7A3E9D", alpha=0.32)
    axes[1].plot(full_eq["DateTime"], full_dd, color="#5A2E78", lw=0.9)
    axes[1].set_title("TY 1-Minute Full-Sample Underwater Curve", fontsize=14, fontweight="bold")
    axes[1].set_ylabel("Drawdown")
    axes[1].xaxis.set_major_locator(mdates.YearLocator(5))
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    save_fig(FIG_DIR / "02_underwater_curves.png")


def plot_quarterly_performance(params: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(13, 8), sharex=True)
    x = params["Period"].to_numpy()
    axes[0].bar(x, params["OOS_Profit"], color=np.where(params["OOS_Profit"] >= 0, "#2E8B57", "#B22222"))
    axes[0].set_title("Quarterly OOS Profit by Walk-Forward Period", fontsize=14, fontweight="bold")
    axes[0].set_ylabel("Profit ($)")
    axes[1].bar(x, params["OOS_Objective"], color=np.where(params["OOS_Objective"] >= 0, "#1F77B4", "#8B1E3F"))
    axes[1].set_title("Quarterly OOS Return on Account", fontsize=14, fontweight="bold")
    axes[1].set_ylabel("RoA")
    axes[1].set_xlabel("Walk-Forward Period")
    save_fig(FIG_DIR / "03_quarterly_performance.png")


def plot_parameter_path(params: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(13, 8), sharex=True)
    axes[0].plot(params["Period"], params["L"], marker="o", ms=3, color="#1F4E79", lw=1.2)
    axes[0].set_title("Selected Lookback by Walk-Forward Period", fontsize=14, fontweight="bold")
    axes[0].set_ylabel("L")
    axes[1].plot(params["Period"], params["S"], marker="o", ms=3, color="#C05A00", lw=1.2)
    axes[1].set_title("Selected Stop by Walk-Forward Period", fontsize=14, fontweight="bold")
    axes[1].set_ylabel("S")
    axes[1].set_xlabel("Walk-Forward Period")
    save_fig(FIG_DIR / "04_parameter_path.png")


def plot_parameter_frequency(params: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
    l_counts = params["L"].value_counts().sort_index()
    s_counts = params["S"].value_counts().sort_index()
    axes[0].bar(l_counts.index.astype(str), l_counts.values, color="#4C78A8")
    axes[0].set_title("Lookback Frequency", fontsize=14, fontweight="bold")
    axes[0].set_ylabel("Count")
    axes[0].tick_params(axis="x", rotation=45)
    axes[1].bar([f"{x:.3f}" for x in s_counts.index], s_counts.values, color="#F58518")
    axes[1].set_title("Stop Frequency", fontsize=14, fontweight="bold")
    axes[1].tick_params(axis="x", rotation=45)
    save_fig(FIG_DIR / "05_parameter_frequency.png")


def plot_trade_distributions(oos_ledger: pd.DataFrame, full_ledger: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    axes[0, 0].hist(oos_ledger["pnl"], bins=50, color="#1F77B4", alpha=0.8)
    axes[0, 0].set_title("OOS Trade PnL Distribution", fontsize=13, fontweight="bold")
    axes[0, 1].hist(full_ledger["pnl"], bins=60, color="#D17A22", alpha=0.8)
    axes[0, 1].set_title("Full-Sample Trade PnL Distribution", fontsize=13, fontweight="bold")
    axes[1, 0].hist(oos_ledger["duration_bars"], bins=50, color="#2E8B57", alpha=0.8)
    axes[1, 0].set_title("OOS Trade Duration Distribution", fontsize=13, fontweight="bold")
    axes[1, 1].hist(full_ledger["duration_bars"], bins=60, color="#8B1E3F", alpha=0.8)
    axes[1, 1].set_title("Full-Sample Trade Duration Distribution", fontsize=13, fontweight="bold")
    for ax in axes.flat:
        ax.grid(alpha=0.2)
    save_fig(FIG_DIR / "06_trade_distributions.png")


def plot_reference_bars(cpp_summary: pd.DataFrame) -> None:
    ref = cpp_summary[cpp_summary["RunType"].str.startswith("reference_")].copy()
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.8))
    axes[0].bar(ref["RunType"], ref["NetProfit"], color=["#4C78A8", "#F58518", "#54A24B"])
    axes[0].set_title("Reference Profit", fontsize=13, fontweight="bold")
    axes[0].tick_params(axis="x", rotation=35)
    axes[1].bar(ref["RunType"], ref["NetMaxDD"], color=["#A0CBE8", "#FFBF79", "#8CD17D"])
    axes[1].set_title("Reference Max Drawdown", fontsize=13, fontweight="bold")
    axes[1].tick_params(axis="x", rotation=35)
    axes[2].bar(ref["RunType"], ref["NetRoA"], color=["#2E86AB", "#E27D60", "#3D9970"])
    axes[2].set_title("Reference Return on Account", fontsize=13, fontweight="bold")
    axes[2].tick_params(axis="x", rotation=35)
    save_fig(FIG_DIR / "07_reference_split_comparison.png")


def plot_quarter_extremes(params: pd.DataFrame) -> None:
    top = params.nlargest(5, "OOS_Profit")[["Period", "OOS_Profit"]].copy()
    bottom = params.nsmallest(5, "OOS_Profit")[["Period", "OOS_Profit"]].copy()
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
    axes[0].bar(top["Period"].astype(str), top["OOS_Profit"], color="#2E8B57")
    axes[0].set_title("Top 5 OOS Quarters by Profit", fontsize=13, fontweight="bold")
    axes[1].bar(bottom["Period"].astype(str), bottom["OOS_Profit"], color="#B22222")
    axes[1].set_title("Bottom 5 OOS Quarters by Profit", fontsize=13, fontweight="bold")
    save_fig(FIG_DIR / "08_quarter_extremes.png")


def plot_parity_table(parity: pd.DataFrame) -> None:
    show = parity[[
        "RunType",
        "PythonProfit",
        "CppProfit",
        "PythonMaxDD",
        "CppMaxDD",
        "PythonRoA",
        "CppRoA",
        "Within10Pct",
    ]].copy()
    show["PythonProfit"] = show["PythonProfit"].map(format_money)
    show["CppProfit"] = show["CppProfit"].map(format_money)
    show["PythonMaxDD"] = show["PythonMaxDD"].map(format_money)
    show["CppMaxDD"] = show["CppMaxDD"].map(format_money)
    show["PythonRoA"] = show["PythonRoA"].map(format_ratio)
    show["CppRoA"] = show["CppRoA"].map(format_ratio)
    show["Within10Pct"] = show["Within10Pct"].map(lambda x: "Yes" if bool(x) else "No")
    table_figure(show, "Python vs C++ TY 1-Minute Parity", FIG_DIR / "09_parity_table.png", font_size=9)


def plot_headline_table(cpp_summary: pd.DataFrame) -> None:
    table_figure(build_headline_table(cpp_summary), "TY 1-Minute Headline Results", FIG_DIR / "00_headline_results_table.png", font_size=9)


def build_interval_comparison_table(
    one_oos: pd.DataFrame,
    one_full: pd.DataFrame,
    one_ref: pd.DataFrame,
    five_oos: pd.DataFrame,
    five_full: pd.DataFrame,
    five_ref: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    mapping = [
        ("Walk-forward OOS", one_oos.iloc[0], five_oos.iloc[0]),
        ("Full sample", one_full.iloc[0], five_full.iloc[0]),
        ("Reference IS", one_ref.loc[one_ref["Segment"] == "in_sample"].iloc[0], five_ref.loc[five_ref["Segment"] == "in_sample"].iloc[0]),
        ("Reference OOS", one_ref.loc[one_ref["Segment"] == "out_of_sample"].iloc[0], five_ref.loc[five_ref["Segment"] == "out_of_sample"].iloc[0]),
    ]
    for label, one, five in mapping:
        one_profit = float(one["Total Profit"] if "Total Profit" in one else one["Profit"])
        five_profit = float(five["Total Profit"] if "Total Profit" in five else five["Profit"])
        one_dd = float(one["Max Drawdown $"] if "Max Drawdown $" in one else one["WorstDrawDown"])
        five_dd = float(five["Max Drawdown $"] if "Max Drawdown $" in five else five["WorstDrawDown"])
        one_roa = float(one["Return on Account"] if "Return on Account" in one else one["Objective"])
        five_roa = float(five["Return on Account"] if "Return on Account" in five else five["Objective"])
        rows.append(
            {
                "Run": label,
                "1m Profit": format_money(one_profit),
                "5m Profit": format_money(five_profit),
                "1m MaxDD": format_money(one_dd),
                "5m MaxDD": format_money(five_dd),
                "1m RoA": format_ratio(one_roa),
                "5m RoA": format_ratio(five_roa),
            }
        )
    return pd.DataFrame(rows)


def plot_interval_comparison_table(
    one_oos: pd.DataFrame,
    one_full: pd.DataFrame,
    one_ref: pd.DataFrame,
    five_oos: pd.DataFrame,
    five_full: pd.DataFrame,
    five_ref: pd.DataFrame,
) -> None:
    df = build_interval_comparison_table(one_oos, one_full, one_ref, five_oos, five_full, five_ref)
    table_figure(df, "TY 1-Minute vs 5-Minute Comparison", FIG_DIR / "10_interval_comparison_table.png", font_size=9)


def plot_growth_comparison(
    one_oos_eq: pd.DataFrame,
    one_full_eq: pd.DataFrame,
    five_oos_eq: pd.DataFrame,
    five_full_eq: pd.DataFrame,
) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(13, 8), sharex=False)
    axes[0].plot(one_oos_eq["DateTime"], one_oos_eq["OOS_Equity"] / 100000.0, label="1m OOS", color="#1F77B4", lw=1.3)
    axes[0].plot(five_oos_eq["DateTime"], five_oos_eq["OOS_Equity"] / 100000.0, label="5m OOS", color="#F58518", lw=1.2)
    axes[0].set_title("Walk-Forward OOS Growth: 1m vs 5m", fontsize=14, fontweight="bold")
    axes[0].legend(frameon=False)
    axes[0].set_ylabel("Growth of $1")
    axes[0].xaxis.set_major_locator(mdates.YearLocator(5))
    axes[0].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    axes[1].plot(one_full_eq["DateTime"], one_full_eq["Equity"] / 100000.0, label="1m Full", color="#1F77B4", lw=1.3)
    axes[1].plot(five_full_eq["DateTime"], five_full_eq["Equity"] / 100000.0, label="5m Full", color="#F58518", lw=1.2)
    axes[1].set_title("Full-Sample Growth: 1m vs 5m", fontsize=14, fontweight="bold")
    axes[1].legend(frameon=False)
    axes[1].set_ylabel("Growth of $1")
    axes[1].xaxis.set_major_locator(mdates.YearLocator(5))
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    save_fig(FIG_DIR / "11_growth_compare_1m_vs_5m.png")


def plot_underwater_comparison(
    one_oos_eq: pd.DataFrame,
    one_full_eq: pd.DataFrame,
    five_oos_eq: pd.DataFrame,
    five_full_eq: pd.DataFrame,
) -> None:
    one_oos_dd = one_oos_eq["OOS_Equity"] / one_oos_eq["OOS_Equity"].cummax() - 1.0
    five_oos_dd = five_oos_eq["OOS_Equity"] / five_oos_eq["OOS_Equity"].cummax() - 1.0
    one_full_dd = one_full_eq["Equity"] / one_full_eq["Equity"].cummax() - 1.0
    five_full_dd = five_full_eq["Equity"] / five_full_eq["Equity"].cummax() - 1.0
    fig, axes = plt.subplots(2, 1, figsize=(13, 8), sharex=False)
    axes[0].plot(one_oos_eq["DateTime"], one_oos_dd, label="1m OOS", color="#1F77B4", lw=1.2)
    axes[0].plot(five_oos_eq["DateTime"], five_oos_dd, label="5m OOS", color="#F58518", lw=1.2)
    axes[0].fill_between(one_oos_eq["DateTime"], one_oos_dd, 0, color="#1F77B4", alpha=0.08)
    axes[0].fill_between(five_oos_eq["DateTime"], five_oos_dd, 0, color="#F58518", alpha=0.08)
    axes[0].set_title("Walk-Forward OOS Underwater: 1m vs 5m", fontsize=14, fontweight="bold")
    axes[0].legend(frameon=False)
    axes[1].plot(one_full_eq["DateTime"], one_full_dd, label="1m Full", color="#1F77B4", lw=1.2)
    axes[1].plot(five_full_eq["DateTime"], five_full_dd, label="5m Full", color="#F58518", lw=1.2)
    axes[1].fill_between(one_full_eq["DateTime"], one_full_dd, 0, color="#1F77B4", alpha=0.08)
    axes[1].fill_between(five_full_eq["DateTime"], five_full_dd, 0, color="#F58518", alpha=0.08)
    axes[1].set_title("Full-Sample Underwater: 1m vs 5m", fontsize=14, fontweight="bold")
    axes[1].legend(frameon=False)
    save_fig(FIG_DIR / "12_underwater_compare_1m_vs_5m.png")


def plot_metric_comparison(one_oos: pd.DataFrame, five_oos: pd.DataFrame, one_full: pd.DataFrame, five_full: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(13, 8))
    labels = ["1m", "5m"]
    axes[0, 0].bar(labels, [float(one_oos.iloc[0]["Total Profit"]), float(five_oos.iloc[0]["Total Profit"])], color=["#1F77B4", "#F58518"])
    axes[0, 0].set_title("OOS Net Profit", fontsize=13, fontweight="bold")
    axes[0, 1].bar(labels, [float(one_oos.iloc[0]["Max Drawdown $"]), float(five_oos.iloc[0]["Max Drawdown $"])], color=["#1F77B4", "#F58518"])
    axes[0, 1].set_title("OOS Max Drawdown", fontsize=13, fontweight="bold")
    axes[1, 0].bar(labels, [float(one_oos.iloc[0]["Return on Account"]), float(five_oos.iloc[0]["Return on Account"])], color=["#1F77B4", "#F58518"])
    axes[1, 0].set_title("OOS Return on Account", fontsize=13, fontweight="bold")
    axes[1, 1].bar(labels, [float(one_oos.iloc[0]["Sharpe Ratio"]), float(five_oos.iloc[0]["Sharpe Ratio"])], color=["#1F77B4", "#F58518"])
    axes[1, 1].set_title("OOS Sharpe Ratio", fontsize=13, fontweight="bold")
    save_fig(FIG_DIR / "13_oos_metric_compare_1m_vs_5m.png")


def plot_quarterly_comparison(one_params: pd.DataFrame, five_params: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(13, 8), sharex=True)
    axes[0].plot(one_params["Period"], one_params["OOS_Profit"], color="#1F77B4", lw=1.1, label="1m")
    axes[0].plot(five_params["Period"], five_params["OOS_Profit"], color="#F58518", lw=1.1, label="5m")
    axes[0].axhline(0, color="#666666", lw=0.8)
    axes[0].set_title("Quarterly OOS Profit: 1m vs 5m", fontsize=14, fontweight="bold")
    axes[0].legend(frameon=False)
    axes[1].plot(one_params["Period"], one_params["OOS_Objective"], color="#1F77B4", lw=1.1, label="1m")
    axes[1].plot(five_params["Period"], five_params["OOS_Objective"], color="#F58518", lw=1.1, label="5m")
    axes[1].axhline(0, color="#666666", lw=0.8)
    axes[1].set_title("Quarterly OOS RoA: 1m vs 5m", fontsize=14, fontweight="bold")
    axes[1].set_xlabel("Walk-Forward Period")
    save_fig(FIG_DIR / "14_quarterly_compare_1m_vs_5m.png")


def plot_parameter_comparison(one_params: pd.DataFrame, five_params: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(13, 8))
    axes[0, 0].plot(one_params["Period"], one_params["L"], color="#1F77B4", lw=1.1)
    axes[0, 0].set_title("1m Selected L", fontsize=13, fontweight="bold")
    axes[0, 1].plot(five_params["Period"], five_params["L"], color="#F58518", lw=1.1)
    axes[0, 1].set_title("5m Selected L", fontsize=13, fontweight="bold")
    axes[1, 0].plot(one_params["Period"], one_params["S"], color="#1F77B4", lw=1.1)
    axes[1, 0].set_title("1m Selected S", fontsize=13, fontweight="bold")
    axes[1, 1].plot(five_params["Period"], five_params["S"], color="#F58518", lw=1.1)
    axes[1, 1].set_title("5m Selected S", fontsize=13, fontweight="bold")
    save_fig(FIG_DIR / "15_parameter_compare_1m_vs_5m.png")


def plot_distribution_comparison(one_oos_ledger: pd.DataFrame, five_oos_ledger: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
    axes[0].hist(one_oos_ledger["pnl"], bins=45, alpha=0.55, label="1m", color="#1F77B4")
    axes[0].hist(five_oos_ledger["pnl"], bins=45, alpha=0.55, label="5m", color="#F58518")
    axes[0].set_title("OOS Trade PnL: 1m vs 5m", fontsize=13, fontweight="bold")
    axes[0].legend(frameon=False)
    axes[1].hist(one_oos_ledger["duration_bars"], bins=45, alpha=0.55, label="1m", color="#1F77B4")
    axes[1].hist(five_oos_ledger["duration_bars"], bins=45, alpha=0.55, label="5m", color="#F58518")
    axes[1].set_title("OOS Trade Duration: 1m vs 5m", fontsize=13, fontweight="bold")
    axes[1].legend(frameon=False)
    save_fig(FIG_DIR / "16_distribution_compare_1m_vs_5m.png")


def plot_parity_comparison(one_parity: pd.DataFrame, five_parity: pd.DataFrame) -> None:
    show = pd.concat([one_parity.assign(Interval="1m"), five_parity.assign(Interval="5m")], ignore_index=True)
    show = show[[
        "Interval",
        "RunType",
        "PythonProfit",
        "CppProfit",
        "PythonMaxDD",
        "CppMaxDD",
        "Within10Pct",
    ]].copy()
    show["PythonProfit"] = show["PythonProfit"].map(format_money)
    show["CppProfit"] = show["CppProfit"].map(format_money)
    show["PythonMaxDD"] = show["PythonMaxDD"].map(format_money)
    show["CppMaxDD"] = show["CppMaxDD"].map(format_money)
    show["Within10Pct"] = show["Within10Pct"].map(lambda x: "Yes" if bool(x) else "No")
    table_figure(show, "TY 1m vs 5m Python/C++ Parity", FIG_DIR / "17_parity_compare_1m_vs_5m.png", font_size=8)


def build_markdown(
    cpp_summary: pd.DataFrame,
    oos_metrics: pd.DataFrame,
    full_metrics: pd.DataFrame,
    ref_summary: pd.DataFrame,
    params: pd.DataFrame,
    parity: pd.DataFrame,
    five_oos_metrics: pd.DataFrame,
    five_full_metrics: pd.DataFrame,
    five_ref_summary: pd.DataFrame,
    five_params: pd.DataFrame,
    five_parity: pd.DataFrame,
) -> str:
    headline = build_headline_table(cpp_summary)
    compare_table = build_interval_comparison_table(oos_metrics, full_metrics, ref_summary, five_oos_metrics, five_full_metrics, five_ref_summary)
    top_quarters = params.nlargest(10, "OOS_Profit")[[
        "Period", "OOS_start", "OOS_end", "L", "S", "OOS_Profit", "OOS_MaxDD", "OOS_Objective", "OOS_Trades"
    ]].copy()
    bottom_quarters = params.nsmallest(10, "OOS_Profit")[[
        "Period", "OOS_start", "OOS_end", "L", "S", "OOS_Profit", "OOS_MaxDD", "OOS_Objective", "OOS_Trades"
    ]].copy()
    modal = params[["L", "S"]].astype({"L": int, "S": float}).value_counts().reset_index(name="Count").iloc[0]
    lines = [
        "# TY 1-Minute Corrected Results Page",
        "",
        "This page coalesces the corrected `TY` 1-minute results from the standalone repo into one scrollable markdown report with embedded figures.",
        "",
        "## Run configuration",
        "- Market: `TY` 10-Year Treasury Note futures",
        "- Interval: `1 minute`",
        "- Point value: `1000`",
        "- Tick value: `15.625`",
        "- Round-turn slippage: `18.625`",
        "- Session filter: `07:20` to `14:00` Chicago time",
        "- Active bars per session: `400`",
        "- Matlab-style reference warmup: `barsBack = 17001`",
        "",
        "## Headline summary",
        headline.to_markdown(index=False),
        "",
        f"- Modal walk-forward configuration: `L = {int(modal['L'])}`, `S = {float(modal['S']):.3f}` selected `{int(modal['Count'])}` times.",
        f"- Walk-forward OOS total profit: `{format_money(float(oos_metrics.iloc[0]['Total Profit']))}`",
        f"- Walk-forward OOS max drawdown: `{format_money(float(oos_metrics.iloc[0]['Max Drawdown $']))}`",
        f"- Walk-forward OOS Sharpe: `{float(oos_metrics.iloc[0]['Sharpe Ratio']):.3f}`",
        f"- Full-sample net profit: `{format_money(float(full_metrics.iloc[0]['Total Profit']))}`",
        f"- Full-sample max drawdown: `{format_money(float(full_metrics.iloc[0]['Max Drawdown $']))}`",
        "",
        image_md(FIG_DIR / "00_headline_results_table.png", "Headline Results"),
        "",
        "## 1-minute versus 5-minute comparison",
        compare_table.to_markdown(index=False),
        "",
        f"- 1m OOS profit minus 5m OOS profit: `{format_money(float(oos_metrics.iloc[0]['Total Profit']) - float(five_oos_metrics.iloc[0]['Total Profit']))}`",
        f"- 1m OOS max drawdown minus 5m OOS max drawdown: `{format_money(float(oos_metrics.iloc[0]['Max Drawdown $']) - float(five_oos_metrics.iloc[0]['Max Drawdown $']))}`",
        f"- 1m OOS RoA minus 5m OOS RoA: `{format_ratio(float(oos_metrics.iloc[0]['Return on Account']) - float(five_oos_metrics.iloc[0]['Return on Account']))}`",
        "",
        image_md(FIG_DIR / "10_interval_comparison_table.png", "1m vs 5m Interval Comparison"),
        "",
        image_md(FIG_DIR / "11_growth_compare_1m_vs_5m.png", "1m vs 5m Growth Comparison"),
        "",
        image_md(FIG_DIR / "12_underwater_compare_1m_vs_5m.png", "1m vs 5m Underwater Comparison"),
        "",
        image_md(FIG_DIR / "13_oos_metric_compare_1m_vs_5m.png", "1m vs 5m OOS Metric Comparison"),
        "",
        image_md(FIG_DIR / "14_quarterly_compare_1m_vs_5m.png", "1m vs 5m Quarterly Comparison"),
        "",
        image_md(FIG_DIR / "15_parameter_compare_1m_vs_5m.png", "1m vs 5m Parameter Comparison"),
        "",
        image_md(FIG_DIR / "16_distribution_compare_1m_vs_5m.png", "1m vs 5m Distribution Comparison"),
        "",
        image_md(FIG_DIR / "17_parity_compare_1m_vs_5m.png", "1m vs 5m Parity Comparison"),
        "",
        "## Equity curves",
        image_md(FIG_DIR / "01_growth_of_1.png", "Growth of $1"),
        "",
        "## Underwater curves",
        image_md(FIG_DIR / "02_underwater_curves.png", "Underwater Curves"),
        "",
        "## Quarterly walk-forward outcomes",
        image_md(FIG_DIR / "03_quarterly_performance.png", "Quarterly Performance"),
        "",
        "## Parameter path",
        image_md(FIG_DIR / "04_parameter_path.png", "Parameter Path"),
        "",
        "## Parameter frequency",
        image_md(FIG_DIR / "05_parameter_frequency.png", "Parameter Frequency"),
        "",
        "## Trade distributions",
        image_md(FIG_DIR / "06_trade_distributions.png", "Trade Distributions"),
        "",
        "## Matlab-style reference split",
        ref_summary.to_markdown(index=False),
        "",
        image_md(FIG_DIR / "07_reference_split_comparison.png", "Reference Split Comparison"),
        "",
        "## Quarterly extremes",
        image_md(FIG_DIR / "08_quarter_extremes.png", "Quarter Extremes"),
        "",
        "### Top 10 OOS quarters by profit",
        top_quarters.to_markdown(index=False),
        "",
        "### Bottom 10 OOS quarters by profit",
        bottom_quarters.to_markdown(index=False),
        "",
        "## Python / C++ parity",
        parity.to_markdown(index=False),
        "",
        image_md(FIG_DIR / "09_parity_table.png", "Parity Table"),
        "",
        "## Figure inventory",
        "- `00_headline_results_table.png`: slide-style KPI table.",
        "- `01_growth_of_1.png`: walk-forward OOS vs full-sample growth of $1 for TY 1m.",
        "- `02_underwater_curves.png`: OOS and full-sample drawdown curves for TY 1m.",
        "- `03_quarterly_performance.png`: quarterly OOS profit and RoA for TY 1m.",
        "- `04_parameter_path.png`: selected `L` and `S` through time for TY 1m.",
        "- `05_parameter_frequency.png`: frequency of chosen `L` and `S` values for TY 1m.",
        "- `06_trade_distributions.png`: TY 1m trade PnL and duration distributions.",
        "- `07_reference_split_comparison.png`: TY 1m Matlab-style reference split comparison.",
        "- `08_quarter_extremes.png`: best and worst TY 1m OOS quarters.",
        "- `09_parity_table.png`: TY 1m Python/C++ agreement table.",
        "- `10_interval_comparison_table.png`: headline 1m vs 5m comparison table.",
        "- `11_growth_compare_1m_vs_5m.png`: 1m vs 5m growth comparison.",
        "- `12_underwater_compare_1m_vs_5m.png`: 1m vs 5m underwater comparison.",
        "- `13_oos_metric_compare_1m_vs_5m.png`: 1m vs 5m OOS metric bars.",
        "- `14_quarterly_compare_1m_vs_5m.png`: 1m vs 5m quarterly OOS comparisons.",
        "- `15_parameter_compare_1m_vs_5m.png`: 1m vs 5m parameter path comparisons.",
        "- `16_distribution_compare_1m_vs_5m.png`: 1m vs 5m trade distribution comparisons.",
        "- `17_parity_compare_1m_vs_5m.png`: 1m vs 5m parity table comparison.",
        "",
        "Source: corrected outputs under `results_cpp_ty_1m`, `results_py_ty_1m`, and `results_compare/TY_5m`.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    ensure_dir(FIG_DIR)
    data = load_inputs()
    plot_headline_table(data["cpp_summary"])
    plot_growth(data["oos_equity"], data["full_equity"])
    plot_underwater(data["oos_equity"], data["full_equity"])
    plot_quarterly_performance(data["params"])
    plot_parameter_path(data["params"])
    plot_parameter_frequency(data["params"])
    plot_trade_distributions(data["oos_ledger"], data["full_ledger"])
    plot_reference_bars(data["cpp_summary"])
    plot_quarter_extremes(data["params"])
    plot_parity_table(data["parity"])
    plot_interval_comparison_table(
        data["oos_metrics"], data["full_metrics"], data["reference_summary"],
        data["five_oos_metrics"], data["five_full_metrics"], data["five_reference_summary"],
    )
    plot_growth_comparison(
        data["oos_equity"], data["full_equity"],
        data["five_oos_equity"], data["five_full_equity"],
    )
    plot_underwater_comparison(
        data["oos_equity"], data["full_equity"],
        data["five_oos_equity"], data["five_full_equity"],
    )
    plot_metric_comparison(data["oos_metrics"], data["five_oos_metrics"], data["full_metrics"], data["five_full_metrics"])
    plot_quarterly_comparison(data["params"], data["five_params"])
    plot_parameter_comparison(data["params"], data["five_params"])
    plot_distribution_comparison(data["oos_ledger"], data["five_oos_ledger"])
    plot_parity_comparison(data["parity"], data["five_parity"])
    REPORT_MD.write_text(
        build_markdown(
            data["cpp_summary"],
            data["oos_metrics"],
            data["full_metrics"],
            data["reference_summary"],
            data["params"],
            data["parity"],
            data["five_oos_metrics"],
            data["five_full_metrics"],
            data["five_reference_summary"],
            data["five_params"],
            data["five_parity"],
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
