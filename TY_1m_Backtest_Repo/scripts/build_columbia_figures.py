"""
Re-render the TY 1-minute results-page figures in the project's Columbia
theme (matches scripts/build_*_figures.py in the parent repo).

Outputs go to TY_1m_Backtest_Repo/results_report/figures/, replacing the
previous matplotlib defaults.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter

# ---- Columbia palette -----------------------------------------------------
COL_NAVY = "#012169"
COL_BLUE = "#B9D9EB"
COL_INK = "#1B365D"
COL_GOLD = "#A28D5B"
COL_RED = "#A03033"
COL_GREEN = "#3F6F4A"
COL_GREY = "#9AA1A9"
COL_LIGHT = "#E6E9EE"
COL_CHARCOAL = "#2A2A2A"
COL_CREAM = "#F4F1EA"


def apply_theme() -> None:
    mpl.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": COL_INK,
            "axes.labelcolor": COL_INK,
            "axes.titlecolor": COL_NAVY,
            "axes.titleweight": "bold",
            "axes.titlesize": 13,
            "axes.labelsize": 11,
            "axes.grid": True,
            "grid.color": COL_LIGHT,
            "grid.linewidth": 0.7,
            "xtick.color": COL_CHARCOAL,
            "ytick.color": COL_CHARCOAL,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.frameon": False,
            "legend.fontsize": 9,
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "savefig.bbox": "tight",
            "savefig.dpi": 160,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


# ---- Paths ----------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
CPP_TY = ROOT / "results_cpp_ty_1m"
PY_TY = ROOT / "results_py_ty_1m" / "TY_1m"
COMPARE_5M = ROOT / "results_compare" / "TY_5m"
PARITY = ROOT / "results_py_ty_1m" / "python_cpp_fidelity_comparison.csv"
OUT = ROOT / "results_report" / "figures"
OUT.mkdir(parents=True, exist_ok=True)


def _save(fig, name):
    p = OUT / name
    fig.savefig(p)
    plt.close(fig)
    return p


def _credit(ax, txt="Source: Group 1 — TF Data 1-min OHLC, $100k initial equity"):
    ax.text(0.0, -0.16, txt, transform=ax.transAxes, ha="left", va="top",
            fontsize=8, color=COL_GREY)
    ax.text(0.99, -0.16, "MATH GR5360 — Group 1 — Columbia MAFN",
            transform=ax.transAxes, ha="right", va="top",
            fontsize=8, color=COL_GREY)


def _money(ax_yax):
    ax_yax.set_major_formatter(FuncFormatter(lambda v, _: f"${v/1000:,.0f}k"))


# ---- Loaders --------------------------------------------------------------
def load_summary() -> pd.DataFrame:
    return pd.read_csv(CPP_TY / "tf_backtest_summary.csv")


def load_eq(market: str = "TY_1m", kind: str = "walkforward") -> pd.DataFrame:
    if market == "TY_1m":
        return pd.read_csv(PY_TY / f"TY_1m_{kind}_equity.csv", parse_dates=["DateTime"])
    return pd.read_csv(COMPARE_5M / f"TY_5m_{kind}_equity.csv", parse_dates=["DateTime"])


def load_params(market: str = "TY_1m") -> pd.DataFrame:
    if market == "TY_1m":
        return pd.read_csv(PY_TY / "TY_1m_walkforward_params.csv")
    return pd.read_csv(COMPARE_5M / "TY_5m_walkforward_params.csv")


def load_ledger(market: str = "TY_1m", kind: str = "walkforward") -> pd.DataFrame:
    if market == "TY_1m":
        return pd.read_csv(PY_TY / f"TY_1m_{kind}_ledger.csv",
                           parse_dates=["entry_time", "exit_time"])
    return pd.read_csv(COMPARE_5M / f"TY_5m_{kind}_ledger.csv",
                       parse_dates=["entry_time", "exit_time"])


def load_metrics(market: str = "TY_1m", kind: str = "oos") -> pd.Series:
    if market == "TY_1m":
        return pd.read_csv(PY_TY / f"TY_1m_{kind}_metrics.csv").iloc[0]
    return pd.read_csv(COMPARE_5M / f"TY_5m_{kind}_metrics.csv").iloc[0]


def load_parity(filename: str) -> pd.DataFrame:
    return pd.read_csv(filename)


# ---------------------------------------------------------------------------
# Bloomberg-style table renderer
# ---------------------------------------------------------------------------
def render_kv_table(rows: list[tuple[str, list[str]]], col_headers: list[str],
                    title: str, source: str, *, name: str,
                    figsize=(10.5, 5.5),
                    label_w: float = 0.30):
    """Bloomberg-style key/value table. Columns are right-aligned at
    positions chosen so each cell has at least max_text_width + a small
    gap of horizontal room — avoids the prior 'S column bleeds into
    NetProfit' overlap."""
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_axis_off()
    fig.patch.set_facecolor("white")

    fig.text(0.06, 0.92, title, color=COL_NAVY, fontsize=18, fontweight="bold")

    n_cols = len(col_headers)
    # Width of each column = max(header width, max data-cell width) + gap.
    # Approximate character width for the body font @ size 10.5 in figure units.
    char_w_body = 0.0085  # approx for monospace 10.5pt at our figsize
    char_w_head = 0.011   # bold 11pt is wider
    gap = 0.012
    col_widths = []
    for j, header in enumerate(col_headers):
        w_head = len(str(header)) * char_w_head
        w_body = max((len(str(r[1][j])) for r in rows), default=0) * char_w_body
        col_widths.append(max(w_head, w_body) + gap)
    total_w = sum(col_widths)
    # Available data area: from label_w + 0.05 to 0.97
    data_left = label_w + 0.05
    data_right = 0.97
    avail = data_right - data_left
    if total_w > avail:
        # If we don't fit, scale columns down proportionally.
        scale = avail / total_w
        col_widths = [w * scale for w in col_widths]
        total_w = sum(col_widths)
    # Right-edge of each column (where right-aligned text anchors)
    data_x = []
    cum = data_right
    for w in reversed(col_widths):
        data_x.append(cum)
        cum -= w
    data_x = list(reversed(data_x))

    # Header row
    header_y = 0.81
    for i, lbl in enumerate(col_headers):
        fig.text(data_x[i], header_y, lbl, color=COL_NAVY, fontsize=11,
                 fontweight="bold", ha="right")
    fig.add_artist(plt.Line2D([0.06, 0.97], [header_y - 0.02, header_y - 0.02],
                              color=COL_INK, lw=1.2))

    # Body rows
    row_y0 = 0.72
    row_dy = 0.66 / max(len(rows), 1)
    for i, (label, vals) in enumerate(rows):
        y = row_y0 - i * row_dy
        fig.text(0.06, y, label, color=COL_INK, fontsize=10.5, ha="left")
        for j, v in enumerate(vals):
            color = COL_RED if (str(v).startswith("-") and "%" in str(v)) else COL_CHARCOAL
            fig.text(data_x[j], y, str(v), color=color, fontsize=10.5,
                     ha="right", family="DejaVu Sans Mono")
        if i < len(rows) - 1:
            fig.add_artist(plt.Line2D([0.06, 0.97], [y - 0.02, y - 0.02],
                                      color=COL_LIGHT, lw=0.5))

    fig.text(0.06, 0.04, source, color=COL_GREY, fontsize=8.5)
    fig.text(0.97, 0.04, "MATH GR5360 — Group 1 — Columbia MAFN",
             color=COL_GREY, fontsize=8.5, ha="right")
    _save(fig, name)


# ---------------------------------------------------------------------------
# 00 — Headline KPI table
# ---------------------------------------------------------------------------
def fig_00_headline():
    s = load_summary()
    rows = []
    for _, r in s.iterrows():
        rows.append((
            r["RunType"],
            [
                f"{int(r['L']):d}",
                f"{r['S']:.3f}",
                f"${r['NetProfit']:,.2f}",
                f"${r['NetMaxDD']:,.2f}",
                f"{r['NetRoA']:.3f}",
                f"{int(r['ClosedTrades']):d}",
            ],
        ))
    render_kv_table(
        rows,
        col_headers=["L", "S", "NetProfit", "NetMaxDD", "NetRoA", "Trades"],
        title="TY 1-minute — headline run summary",
        source="Source: results_cpp_ty_1m/tf_backtest_summary.csv",
        name="00_headline_results_table.png",
        label_w=0.32,
    )


# ---------------------------------------------------------------------------
# 01 — Growth of $1
# ---------------------------------------------------------------------------
def fig_01_growth():
    eq_oos = load_eq("TY_1m", "walkforward")
    eq_full = load_eq("TY_1m", "fullsample")
    fig, ax = plt.subplots(figsize=(11.5, 5.5))
    ax.plot(eq_oos["DateTime"], eq_oos["OOS_Equity"] / 100_000.0,
            color=COL_NAVY, lw=1.4, label="Walk-forward OOS")
    if "OOS_Equity" in eq_full.columns:
        ax.plot(eq_full["DateTime"], eq_full["OOS_Equity"] / 100_000.0,
                color=COL_GOLD, lw=1.4, label="Full sample (in-sample optimum)")
    elif "Equity" in eq_full.columns:
        ax.plot(eq_full["DateTime"], eq_full["Equity"] / 100_000.0,
                color=COL_GOLD, lw=1.4, label="Full sample (in-sample optimum)")
    ax.axhline(1.0, color=COL_GREY, lw=0.8, ls="--", label="$1 baseline")
    ax.set_title("TY 1-minute — growth of $1 (OOS vs full sample)",
                 color=COL_NAVY, fontsize=14, loc="left")
    ax.set_xlabel("Date")
    ax.set_ylabel("Multiple of $1")
    ax.legend(loc="upper left")
    _credit(ax)
    _save(fig, "01_growth_of_1.png")


# ---------------------------------------------------------------------------
# 02 — Underwater (% off peak)
# ---------------------------------------------------------------------------
def _underwater_pct(eq: pd.Series) -> pd.Series:
    return (eq - eq.cummax()) / eq.cummax() * 100


def fig_02_underwater():
    oos = load_eq("TY_1m", "walkforward")
    full = load_eq("TY_1m", "fullsample")
    fig, axes = plt.subplots(2, 1, figsize=(11.5, 6.0), sharex=True)
    uw_oos = _underwater_pct(oos["OOS_Equity"])
    axes[0].fill_between(oos["DateTime"], uw_oos, 0, color=COL_NAVY, alpha=0.45)
    axes[0].plot(oos["DateTime"], uw_oos, color=COL_NAVY, lw=1.0)
    axes[0].axhline(0, color=COL_INK, lw=0.6)
    axes[0].set_title("TY 1-minute — walk-forward OOS underwater (%)",
                      color=COL_NAVY, fontsize=12, loc="left")
    axes[0].set_ylabel("% off peak")

    eq_col = "OOS_Equity" if "OOS_Equity" in full.columns else "Equity"
    uw_full = _underwater_pct(full[eq_col])
    axes[1].fill_between(full["DateTime"], uw_full, 0, color=COL_GOLD, alpha=0.45)
    axes[1].plot(full["DateTime"], uw_full, color=COL_GOLD, lw=1.0)
    axes[1].axhline(0, color=COL_INK, lw=0.6)
    axes[1].set_title("TY 1-minute — full-sample underwater (%)",
                      color=COL_NAVY, fontsize=12, loc="left")
    axes[1].set_ylabel("% off peak")
    axes[1].set_xlabel("Date")
    _credit(axes[1])
    _save(fig, "02_underwater_curves.png")


# ---------------------------------------------------------------------------
# 03 — Quarterly performance
# ---------------------------------------------------------------------------
def fig_03_quarterly():
    p = load_params("TY_1m")
    fig, axes = plt.subplots(2, 1, figsize=(11.5, 6.0), sharex=True)
    colors = [COL_GREEN if x > 0 else COL_RED for x in p["OOS_Profit"]]
    axes[0].bar(p["Period"], p["OOS_Profit"], color=colors, edgecolor="none", alpha=0.85)
    axes[0].axhline(0, color=COL_INK, lw=0.6)
    axes[0].set_title("TY 1-minute — quarterly OOS net profit ($)",
                      color=COL_NAVY, fontsize=12, loc="left")
    axes[0].set_ylabel("Profit ($)")
    _money(axes[0].yaxis)

    axes[1].bar(p["Period"], p["OOS_Objective"],
                color=[COL_GREEN if x > 0 else COL_RED for x in p["OOS_Objective"]],
                edgecolor="none", alpha=0.85)
    axes[1].axhline(0, color=COL_INK, lw=0.6)
    axes[1].set_title("TY 1-minute — quarterly OOS objective (Profit / |MaxDD|)",
                      color=COL_NAVY, fontsize=12, loc="left")
    axes[1].set_xlabel("Walk-forward period #")
    axes[1].set_ylabel("OOS Profit / |MaxDD|")
    _credit(axes[1])
    _save(fig, "03_quarterly_performance.png")


# ---------------------------------------------------------------------------
# 04 — Parameter path
# ---------------------------------------------------------------------------
def fig_04_param_path():
    p = load_params("TY_1m")
    fig, axes = plt.subplots(2, 1, figsize=(11.5, 5.6), sharex=True)
    axes[0].plot(p["Period"], p["L"], color=COL_NAVY, marker="o", ms=3, lw=1.0)
    axes[0].set_title("TY 1-minute — chosen channel length L per quarter",
                      color=COL_NAVY, fontsize=12, loc="left")
    axes[0].set_ylabel("L (1-min bars)")

    axes[1].plot(p["Period"], p["S"], color=COL_RED, marker="s", ms=3, lw=1.0)
    axes[1].set_title("TY 1-minute — chosen drawdown stop S per quarter",
                      color=COL_NAVY, fontsize=12, loc="left")
    axes[1].set_xlabel("Walk-forward period #")
    axes[1].set_ylabel("S (fraction)")
    _credit(axes[1])
    _save(fig, "04_parameter_path.png")


# ---------------------------------------------------------------------------
# 05 — Parameter frequency
# ---------------------------------------------------------------------------
def fig_05_param_freq():
    p = load_params("TY_1m")
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.5))
    l_counts = p["L"].value_counts().sort_index()
    axes[0].bar(l_counts.index.astype(str), l_counts.values,
                color=COL_NAVY, alpha=0.85, edgecolor="white")
    axes[0].set_title("TY 1-minute — frequency of chosen L",
                      color=COL_NAVY, fontsize=12, loc="left")
    axes[0].set_xlabel("L (1-min bars)")
    axes[0].set_ylabel("Walk-forward periods (count)")

    s_counts = p["S"].value_counts().sort_index()
    axes[1].bar(s_counts.index.astype(str), s_counts.values,
                color=COL_GOLD, alpha=0.85, edgecolor="white")
    axes[1].set_title("TY 1-minute — frequency of chosen S",
                      color=COL_NAVY, fontsize=12, loc="left")
    axes[1].set_xlabel("S (fraction)")
    axes[1].set_ylabel("Walk-forward periods (count)")
    _credit(axes[1])
    _save(fig, "05_parameter_frequency.png")


# ---------------------------------------------------------------------------
# 06 — Trade distributions
# ---------------------------------------------------------------------------
def fig_06_trade_dist():
    ldg = load_ledger("TY_1m", "walkforward")
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.0))
    pnl = ldg["pnl"]
    win = pnl[pnl > 0]; loss = pnl[pnl <= 0]
    axes[0].hist(loss, bins=40, color=COL_RED, alpha=0.65, label=f"Losers (n={len(loss):,d})")
    axes[0].hist(win, bins=40, color=COL_GREEN, alpha=0.80, label=f"Winners (n={len(win):,d})")
    axes[0].axvline(0, color=COL_INK, lw=0.8)
    axes[0].axvline(pnl.mean(), color=COL_NAVY, lw=1.4, ls="--",
                    label=f"Mean PnL ${pnl.mean():,.0f}")
    axes[0].set_title("TY 1-minute — OOS trade PnL distribution ($)",
                      color=COL_NAVY, fontsize=12, loc="left")
    axes[0].set_xlabel("PnL ($)"); axes[0].set_ylabel("Trade count")
    axes[0].legend(loc="upper right")

    dur = ldg["duration_bars"]
    axes[1].hist(dur, bins=40, color=COL_NAVY, alpha=0.85)
    axes[1].set_title("TY 1-minute — OOS trade duration (1-min bars)",
                      color=COL_NAVY, fontsize=12, loc="left")
    axes[1].set_xlabel("Duration (1-min bars)")
    axes[1].set_ylabel("Trade count")
    _credit(axes[1])
    _save(fig, "06_trade_distributions.png")


# ---------------------------------------------------------------------------
# 07 — Reference split (Matlab-style)
# ---------------------------------------------------------------------------
def fig_07_reference_split():
    s = load_summary()
    is_row = s[s["RunType"] == "reference_in_sample"].iloc[0]
    oos_row = s[s["RunType"] == "reference_out_of_sample"].iloc[0]
    full_row = s[s["RunType"] == "reference_full"].iloc[0]

    metrics = ["NetProfit", "NetMaxDD", "NetRoA", "ClosedTrades"]
    labels = ["Net Profit ($)", "Max DD ($)", "Return on Account", "Trades"]
    is_vals = [is_row[m] for m in metrics]
    oos_vals = [oos_row[m] for m in metrics]
    full_vals = [full_row[m] for m in metrics]

    fig, axes = plt.subplots(1, 4, figsize=(13.0, 4.5))
    bar_w = 0.7
    for ax, lbl, iv, ov, fv in zip(axes, labels, is_vals, oos_vals, full_vals):
        ax.bar([0], [iv], bar_w, color=COL_NAVY, label="In-sample")
        ax.bar([1], [ov], bar_w, color=COL_GOLD, label="Out-of-sample")
        ax.bar([2], [fv], bar_w, color=COL_INK, label="Full")
        ax.set_xticks([0, 1, 2], ["IS", "OOS", "Full"])
        ax.axhline(0, color=COL_INK, lw=0.6)
        ax.set_title(lbl, color=COL_NAVY, fontsize=11, loc="left")
        if "$" in lbl:
            _money(ax.yaxis)
    fig.suptitle("TY 1-minute — Matlab-style reference split (L=11200, S=0.04)",
                 color=COL_NAVY, fontsize=14, fontweight="bold", y=1.02)
    _credit(axes[-1])
    _save(fig, "07_reference_split_comparison.png")


# ---------------------------------------------------------------------------
# 08 — Quarterly extremes (top/bottom 10)
# ---------------------------------------------------------------------------
def fig_08_quarter_extremes():
    p = load_params("TY_1m").sort_values("OOS_Profit")
    bottom = p.head(10)
    top = p.tail(10).iloc[::-1]
    fig, axes = plt.subplots(1, 2, figsize=(13.0, 5.0))
    axes[0].barh(top["Period"].astype(str), top["OOS_Profit"], color=COL_GREEN, alpha=0.85)
    axes[0].set_title("TY 1-minute — top 10 OOS quarters by profit",
                      color=COL_NAVY, fontsize=12, loc="left")
    axes[0].set_xlabel("OOS profit ($)"); axes[0].invert_yaxis()
    _money(axes[0].xaxis); axes[0].set_ylabel("Walk-forward period #")

    axes[1].barh(bottom["Period"].astype(str), bottom["OOS_Profit"],
                 color=COL_RED, alpha=0.85)
    axes[1].set_title("TY 1-minute — bottom 10 OOS quarters by profit",
                      color=COL_NAVY, fontsize=12, loc="left")
    axes[1].set_xlabel("OOS profit ($)"); axes[1].invert_yaxis()
    _money(axes[1].xaxis); axes[1].set_ylabel("Walk-forward period #")
    _credit(axes[1])
    _save(fig, "08_quarter_extremes.png")


# ---------------------------------------------------------------------------
# 09 — Parity table
# ---------------------------------------------------------------------------
def fig_09_parity():
    df = load_parity(PARITY)
    rows = []
    for _, r in df.iterrows():
        rows.append((
            r["RunType"],
            [
                f"${r['PythonProfit']:,.2f}",
                f"${r['CppProfit']:,.2f}",
                f"${r['PythonMaxDD']:,.2f}",
                f"${r['CppMaxDD']:,.2f}",
                f"{r['PythonRoA']:.3f}",
                f"{r['CppRoA']:.3f}",
                "✓" if bool(r["Within10Pct"]) else "✗",
            ],
        ))
    render_kv_table(
        rows,
        col_headers=["Py Profit", "C++ Profit", "Py MaxDD",
                     "C++ MaxDD", "Py RoA", "C++ RoA", "≤10%"],
        title="TY 1-minute — Python ↔ C++ parity",
        source="Source: results_py_ty_1m/python_cpp_fidelity_comparison.csv",
        name="09_parity_table.png",
        figsize=(13.0, 5.5),
        label_w=0.28,
    )


# ---------------------------------------------------------------------------
# 10 — 1m vs 5m headline comparison
# ---------------------------------------------------------------------------
def fig_10_interval_table():
    s_1m = load_summary().set_index("RunType")
    s_5m = pd.read_csv(COMPARE_5M / "python_cpp_fidelity_comparison_ty_5m.csv").set_index("RunType")

    pairs = [("walkforward_oos", "Walk-forward OOS"),
             ("full_sample", "Full sample"),
             ("reference_in_sample", "Reference IS"),
             ("reference_out_of_sample", "Reference OOS")]

    rows = []
    for key, label in pairs:
        try:
            r1 = s_1m.loc[key]
            r5 = s_5m.loc[key]
            rows.append((
                label,
                [
                    f"${float(r1['NetProfit']):,.2f}",
                    f"${float(r5['CppProfit']):,.2f}",
                    f"${float(r1['NetMaxDD']):,.2f}",
                    f"${float(r5['CppMaxDD']):,.2f}",
                    f"{float(r1['NetRoA']):.3f}",
                    f"{float(r5['CppRoA']):.3f}",
                ],
            ))
        except KeyError:
            continue
    render_kv_table(
        rows,
        col_headers=["1m Profit", "5m Profit", "1m MaxDD",
                     "5m MaxDD", "1m RoA", "5m RoA"],
        title="TY 1-minute vs 5-minute — headline comparison",
        source="Sources: results_cpp_ty_1m/tf_backtest_summary.csv  +  results_compare/TY_5m/",
        name="10_interval_comparison_table.png",
        figsize=(13.0, 5.0),
        label_w=0.30,
    )


# ---------------------------------------------------------------------------
# 11 — Growth of $1 1m vs 5m
# ---------------------------------------------------------------------------
def fig_11_growth_compare():
    eq1 = load_eq("TY_1m", "walkforward")
    eq5 = load_eq("TY_5m", "walkforward")
    fig, ax = plt.subplots(figsize=(11.5, 5.5))
    ax.plot(eq1["DateTime"], eq1["OOS_Equity"] / 100_000, color=COL_NAVY, lw=1.4,
            label="TY 1-min OOS")
    ax.plot(eq5["DateTime"], eq5["OOS_Equity"] / 100_000, color=COL_GOLD, lw=1.4,
            label="TY 5-min OOS")
    ax.axhline(1.0, color=COL_GREY, lw=0.8, ls="--", label="$1 baseline")
    ax.set_title("TY — walk-forward OOS growth of $1: 1-min vs 5-min",
                 color=COL_NAVY, fontsize=14, loc="left")
    ax.set_xlabel("Date"); ax.set_ylabel("Multiple of $1")
    ax.legend(loc="upper left")
    _credit(ax)
    _save(fig, "11_growth_compare_1m_vs_5m.png")


def fig_12_underwater_compare():
    eq1 = load_eq("TY_1m", "walkforward")
    eq5 = load_eq("TY_5m", "walkforward")
    fig, ax = plt.subplots(figsize=(11.5, 5.0))
    ax.fill_between(eq1["DateTime"], _underwater_pct(eq1["OOS_Equity"]),
                    0, color=COL_NAVY, alpha=0.30, label="1-min OOS")
    ax.fill_between(eq5["DateTime"], _underwater_pct(eq5["OOS_Equity"]),
                    0, color=COL_GOLD, alpha=0.45, label="5-min OOS")
    ax.axhline(0, color=COL_INK, lw=0.6)
    ax.set_title("TY — walk-forward OOS underwater (%): 1-min vs 5-min",
                 color=COL_NAVY, fontsize=14, loc="left")
    ax.set_xlabel("Date"); ax.set_ylabel("% off peak")
    ax.legend(loc="lower left")
    _credit(ax)
    _save(fig, "12_underwater_compare_1m_vs_5m.png")


def fig_13_oos_metric_compare():
    m1 = load_metrics("TY_1m", "oos")
    m5 = load_metrics("TY_5m", "oos")
    metrics = [
        ("Ann. Return %", "Ann. Return %"),
        ("Ann. Volatility %", "Ann. Volatility %"),
        ("Sharpe Ratio", "Sharpe Ratio"),
        ("Return on Account", "Return on Account"),
        ("Profit Factor", "Profit Factor"),
        ("Win Rate %", "Win Rate %"),
    ]
    fig, ax = plt.subplots(figsize=(11.5, 5.0))
    x = np.arange(len(metrics))
    w = 0.36
    v1 = [float(m1[k]) for _, k in metrics]
    v5 = [float(m5[k]) for _, k in metrics]
    ax.bar(x - w / 2, v1, w, color=COL_NAVY, label="1-min")
    ax.bar(x + w / 2, v5, w, color=COL_GOLD, label="5-min")
    ax.set_xticks(x, [m for m, _ in metrics], rotation=20, ha="right")
    ax.axhline(0, color=COL_INK, lw=0.6)
    ax.set_title("TY OOS metrics — 1-min vs 5-min",
                 color=COL_NAVY, fontsize=14, loc="left")
    ax.legend(loc="upper right")
    _credit(ax)
    _save(fig, "13_oos_metric_compare_1m_vs_5m.png")


def fig_14_quarterly_compare():
    p1 = load_params("TY_1m")
    p5 = load_params("TY_5m")
    fig, axes = plt.subplots(2, 1, figsize=(11.5, 6.0), sharex=True)
    axes[0].bar(p1["Period"], p1["OOS_Profit"], color=COL_NAVY, alpha=0.85, edgecolor="none",
                label="1-min")
    axes[0].axhline(0, color=COL_INK, lw=0.6)
    axes[0].set_title("TY OOS profit per quarter — 1-min", color=COL_NAVY, fontsize=12, loc="left")
    axes[0].set_ylabel("Profit ($)"); _money(axes[0].yaxis)

    axes[1].bar(p5["Period"], p5["OOS_Profit"], color=COL_GOLD, alpha=0.85, edgecolor="none",
                label="5-min")
    axes[1].axhline(0, color=COL_INK, lw=0.6)
    axes[1].set_title("TY OOS profit per quarter — 5-min", color=COL_NAVY, fontsize=12, loc="left")
    axes[1].set_xlabel("Walk-forward period #")
    axes[1].set_ylabel("Profit ($)"); _money(axes[1].yaxis)
    _credit(axes[1])
    _save(fig, "14_quarterly_compare_1m_vs_5m.png")


def fig_15_parameter_compare():
    p1 = load_params("TY_1m")
    p5 = load_params("TY_5m")
    fig, axes = plt.subplots(2, 1, figsize=(11.5, 6.0), sharex=True)
    axes[0].plot(p1["Period"], p1["L"], color=COL_NAVY, marker="o", ms=3, lw=1.0, label="1-min L")
    axes[0].plot(p5["Period"], p5["L"] * 5, color=COL_GOLD, marker="s", ms=3, lw=1.0,
                 label="5-min L × 5")
    axes[0].set_title("TY chosen L per quarter — 1-min vs 5-min (×5 to align time-scale)",
                      color=COL_NAVY, fontsize=12, loc="left")
    axes[0].set_ylabel("L (1-min equivalent bars)")
    axes[0].legend(loc="upper right")

    axes[1].plot(p1["Period"], p1["S"], color=COL_NAVY, marker="o", ms=3, lw=1.0, label="1-min S")
    axes[1].plot(p5["Period"], p5["S"], color=COL_GOLD, marker="s", ms=3, lw=1.0, label="5-min S")
    axes[1].set_title("TY chosen S per quarter — 1-min vs 5-min",
                      color=COL_NAVY, fontsize=12, loc="left")
    axes[1].set_xlabel("Walk-forward period #")
    axes[1].set_ylabel("S (fraction)")
    axes[1].legend(loc="upper right")
    _credit(axes[1])
    _save(fig, "15_parameter_compare_1m_vs_5m.png")


def fig_16_distribution_compare():
    l1 = load_ledger("TY_1m", "walkforward")
    l5 = load_ledger("TY_5m", "walkforward")
    # Use % equity-return for cross-resolution comparability
    pct1 = l1["pnl"] / 100_000.0 * 100
    pct5 = l5["pnl"] / 100_000.0 * 100
    fig, axes = plt.subplots(1, 2, figsize=(13.0, 5.0))
    axes[0].hist(pct1, bins=40, color=COL_NAVY, alpha=0.80,
                 label=f"1-min (n={len(pct1):,d})")
    axes[0].axvline(0, color=COL_INK, lw=0.8)
    axes[0].axvline(pct1.mean(), color=COL_NAVY, lw=1.4, ls="--",
                    label=f"mean = {pct1.mean():+.2f}%")
    axes[0].set_title("TY 1-minute — equity-return % per trade",
                      color=COL_NAVY, fontsize=12, loc="left")
    axes[0].set_xlabel("PnL / $100k × 100%")
    axes[0].set_ylabel("Trade count")
    axes[0].legend(loc="upper right")

    axes[1].hist(pct5, bins=40, color=COL_GOLD, alpha=0.80,
                 label=f"5-min (n={len(pct5):,d})")
    axes[1].axvline(0, color=COL_INK, lw=0.8)
    axes[1].axvline(pct5.mean(), color=COL_NAVY, lw=1.4, ls="--",
                    label=f"mean = {pct5.mean():+.2f}%")
    axes[1].set_title("TY 5-minute — equity-return % per trade",
                      color=COL_NAVY, fontsize=12, loc="left")
    axes[1].set_xlabel("PnL / $100k × 100%")
    axes[1].set_ylabel("Trade count")
    axes[1].legend(loc="upper right")
    _credit(axes[1])
    _save(fig, "16_distribution_compare_1m_vs_5m.png")


def fig_17_parity_compare():
    df1 = load_parity(PARITY)
    df5 = pd.read_csv(COMPARE_5M / "python_cpp_fidelity_comparison_ty_5m.csv")
    rows = []
    for run in ["walkforward_oos", "full_sample", "reference_in_sample",
                "reference_out_of_sample", "reference_full"]:
        try:
            r1 = df1[df1["RunType"] == run].iloc[0]
            r5 = df5[df5["RunType"] == run].iloc[0]
            rows.append((
                run,
                [
                    f"{float(r1['ProfitPctError']):.2e}",
                    f"{float(r5['ProfitPctError']):.2e}",
                    f"{float(r1['MaxDDPctError']):.2e}",
                    f"{float(r5['MaxDDPctError']):.2e}",
                    "✓" if bool(r1['Within10Pct']) else "✗",
                    "✓" if bool(r5['Within10Pct']) else "✗",
                ],
            ))
        except (KeyError, IndexError):
            continue
    render_kv_table(
        rows,
        col_headers=["1m |Δ profit|/profit", "5m |Δ profit|/profit",
                     "1m |Δ MaxDD|/MaxDD", "5m |Δ MaxDD|/MaxDD",
                     "1m within 10%", "5m within 10%"],
        title="TY 1-minute vs 5-minute — Python ↔ C++ parity errors",
        source="Sources: results_py_ty_1m/python_cpp_fidelity_comparison.csv  +  results_compare/TY_5m/",
        name="17_parity_compare_1m_vs_5m.png",
        figsize=(13.5, 5.5),
        label_w=0.30,
    )


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def main() -> None:
    apply_theme()
    builders = [
        fig_00_headline, fig_01_growth, fig_02_underwater, fig_03_quarterly,
        fig_04_param_path, fig_05_param_freq, fig_06_trade_dist,
        fig_07_reference_split, fig_08_quarter_extremes, fig_09_parity,
        fig_10_interval_table, fig_11_growth_compare, fig_12_underwater_compare,
        fig_13_oos_metric_compare, fig_14_quarterly_compare,
        fig_15_parameter_compare, fig_16_distribution_compare, fig_17_parity_compare,
    ]
    for fn in builders:
        try:
            fn()
            print(f"[ok] {fn.__name__}")
        except Exception as e:  # pragma: no cover
            print(f"[err] {fn.__name__}: {e}")
    print(f"[done] {OUT}")


if __name__ == "__main__":
    main()
