"""
Build Columbia-themed figures for the final report.

Reads cached results from `results/walkforward/` and `results/diagnostics/`
and writes PNGs into `report/figures/`. Designed to be re-runnable.

Usage: python scripts/build_final_report_figures.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import FuncFormatter

# ----------------------------------------------------------------------------
# Columbia theme
# ----------------------------------------------------------------------------
COLUMBIA_BLUE = "#B9D9EB"
COLUMBIA_NAVY = "#012169"
COLUMBIA_INK = "#1B365D"
COLUMBIA_GOLD = "#A28D5B"
COLUMBIA_CHARCOAL = "#2A2A2A"
COLUMBIA_GREY = "#9AA1A9"
COLUMBIA_RED = "#A03033"
COLUMBIA_GREEN = "#3F6F4A"
COLUMBIA_CREAM = "#F4F1EA"

CMAP_DIVERGING = LinearSegmentedColormap.from_list(
    "columbia_div", [COLUMBIA_NAVY, "#FFFFFF", COLUMBIA_GOLD]
)
CMAP_SEQUENTIAL = LinearSegmentedColormap.from_list(
    "columbia_seq", ["#FFFFFF", COLUMBIA_BLUE, COLUMBIA_NAVY]
)


def apply_theme() -> None:
    mpl.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": COLUMBIA_INK,
            "axes.labelcolor": COLUMBIA_INK,
            "axes.titlecolor": COLUMBIA_NAVY,
            "axes.titleweight": "bold",
            "axes.titlesize": 13,
            "axes.labelsize": 11,
            "axes.grid": True,
            "grid.color": "#E6E9EE",
            "grid.linewidth": 0.7,
            "xtick.color": COLUMBIA_CHARCOAL,
            "ytick.color": COLUMBIA_CHARCOAL,
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


# ----------------------------------------------------------------------------
# Paths
# ----------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "walkforward"
DIAG = ROOT / "results" / "diagnostics"
FIG = ROOT / "report" / "figures"
FIG.mkdir(parents=True, exist_ok=True)


def _save(fig: plt.Figure, name: str) -> Path:
    out = FIG / name
    fig.savefig(out)
    plt.close(fig)
    return out


def _credit(ax: plt.Axes, text: str = "MATH GR5360 — Group 1 — Columbia MAFN") -> None:
    ax.text(
        0.99,
        -0.16,
        text,
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=8,
        color=COLUMBIA_GREY,
    )


# ----------------------------------------------------------------------------
# 1. Variance Ratio curves (TY + BTC)
# ----------------------------------------------------------------------------
def figure_vr_curves() -> None:
    ty = pd.read_csv(DIAG / "TY_vr_curve.csv")
    btc = pd.read_csv(DIAG / "BTC_vr_curve.csv")

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.5), sharey=True)

    for ax, df, label, color in [
        (axes[0], ty, "TY (10-year US Treasury futures)", COLUMBIA_NAVY),
        (axes[1], btc, "BTC (CME Bitcoin futures)", COLUMBIA_GOLD),
    ]:
        ax.axhline(1.0, color=COLUMBIA_GREY, lw=1.0, ls="--", label="VR = 1 (random walk)")
        ax.plot(df["q"], df["VR"], color=color, lw=1.8, label="VR(q)")
        # Shade 5% deviation band
        ax.fill_between(
            df["q"], 0.95, 1.05, color=COLUMBIA_BLUE, alpha=0.18, label="±5% band"
        )
        ax.set_xscale("log")
        ax.set_xlabel("Aggregation horizon q (5-min bars)")
        ax.set_title(label)
        ax.legend(loc="lower left")

    axes[0].set_ylabel("Variance ratio VR(q)")
    fig.suptitle(
        "Lo–MacKinlay variance-ratio profile — TY vs BTC",
        color=COLUMBIA_NAVY,
        fontweight="bold",
        fontsize=14,
        y=1.02,
    )
    _credit(axes[1])
    _save(fig, "fig_vr_curves.png")


# ----------------------------------------------------------------------------
# 2. Push–Response diagrams (reference horizon)
# ----------------------------------------------------------------------------
def figure_push_response() -> None:
    ty = pd.read_csv(DIAG / "TY_reference_pr.csv")
    btc = pd.read_csv(DIAG / "BTC_reference_pr.csv")

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.5))
    for ax, df, label, color in [
        (axes[0], ty, "TY @ 1440 bars (≈18 sessions)", COLUMBIA_NAVY),
        (axes[1], btc, "BTC @ 1152 bars (≈4 days)", COLUMBIA_GOLD),
    ]:
        ax.errorbar(
            df["bin_centre"],
            df["bin_mean"],
            yerr=df["bin_se"],
            fmt="o",
            color=color,
            ecolor=COLUMBIA_GREY,
            elinewidth=1.0,
            capsize=3,
            mfc="white",
            mec=color,
            mew=1.6,
            label="conditional mean ± SE",
        )
        # Linear fit for visual cue
        if len(df) >= 3:
            slope, intercept = np.polyfit(df["bin_centre"], df["bin_mean"], 1)
            xs = np.linspace(df["bin_centre"].min(), df["bin_centre"].max(), 50)
            ax.plot(xs, slope * xs + intercept, color=COLUMBIA_RED, lw=1.4, ls="--", label="linear fit")
        ax.axhline(0, color=COLUMBIA_GREY, lw=0.8)
        ax.axvline(0, color=COLUMBIA_GREY, lw=0.8)
        ax.set_xlabel("Push (price change over τ)")
        ax.set_ylabel("Mean response over τ")
        ax.set_title(label)
        ax.legend(loc="best")

    fig.suptitle(
        "Push–Response diagrams (conditional mean response) — reference horizons",
        color=COLUMBIA_NAVY,
        fontweight="bold",
        fontsize=14,
        y=1.02,
    )
    _credit(axes[1])
    _save(fig, "fig_push_response.png")


# ----------------------------------------------------------------------------
# 3. Walk-forward equity curves
# ----------------------------------------------------------------------------
def _load_equity(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["DateTime"])
    return df


def figure_equity_curves() -> None:
    ty = _load_equity(RESULTS / "TY_5m" / "TY_5m_walkforward_equity.csv")
    btc = _load_equity(RESULTS / "BTC_5m" / "BTC_5m_walkforward_equity.csv")

    fig, axes = plt.subplots(2, 1, figsize=(11.5, 8.0))

    for ax, df, label, color, profit, dd in [
        (axes[0], ty, "TY OOS walk-forward equity (1987–2026)", COLUMBIA_NAVY, 68335.5, 15864.7),
        (axes[1], btc, "BTC OOS walk-forward equity (2023–2026)", COLUMBIA_GOLD, 536397.0, 131729.25),
    ]:
        ax.plot(df["DateTime"], df["OOS_Equity"], color=color, lw=1.4)
        ax.fill_between(df["DateTime"], 100000.0, df["OOS_Equity"], color=color, alpha=0.10)
        ax.axhline(100000.0, color=COLUMBIA_GREY, lw=0.8, ls="--", label="initial equity $100k")
        ax.set_title(label)
        ax.set_ylabel("Equity ($)")
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v/1000:,.0f}k"))
        # Annotation
        ax.text(
            0.01,
            0.95,
            f"Net OOS profit: ${profit:,.0f}\nMax DD: ${dd:,.0f}\nReturn on Account: {profit/dd:,.2f}",
            transform=ax.transAxes,
            va="top",
            ha="left",
            fontsize=9,
            bbox=dict(boxstyle="round", fc=COLUMBIA_CREAM, ec=COLUMBIA_INK, lw=0.6),
        )
        ax.legend(loc="lower right")

    axes[1].set_xlabel("Date")
    fig.suptitle(
        "Channel WithDDControl — out-of-sample walk-forward equity",
        color=COLUMBIA_NAVY,
        fontweight="bold",
        fontsize=14,
        y=1.00,
    )
    _credit(axes[1])
    _save(fig, "fig_equity_walkforward.png")


# ----------------------------------------------------------------------------
# 4. Drawdown / underwater plots
# ----------------------------------------------------------------------------
def _underwater(equity: pd.Series) -> pd.Series:
    peak = equity.cummax()
    return (equity - peak) / peak * 100.0


def figure_underwater() -> None:
    ty = _load_equity(RESULTS / "TY_5m" / "TY_5m_walkforward_equity.csv")
    btc = _load_equity(RESULTS / "BTC_5m" / "BTC_5m_walkforward_equity.csv")

    fig, axes = plt.subplots(2, 1, figsize=(11.5, 7.5))

    for ax, df, label, color in [
        (axes[0], ty, "TY underwater curve (% off peak)", COLUMBIA_NAVY),
        (axes[1], btc, "BTC underwater curve (% off peak)", COLUMBIA_GOLD),
    ]:
        uw = _underwater(df["OOS_Equity"])
        ax.fill_between(df["DateTime"], uw, 0, color=color, alpha=0.45)
        ax.plot(df["DateTime"], uw, color=color, lw=1.0)
        ax.axhline(0, color=COLUMBIA_INK, lw=0.6)
        ax.set_ylabel("% drawdown")
        ax.set_title(label)
        ax.set_ylim(top=1.0)

    axes[1].set_xlabel("Date")
    fig.suptitle(
        "Drawdown family — Chekhlov underwater equity",
        color=COLUMBIA_NAVY,
        fontweight="bold",
        fontsize=14,
        y=1.00,
    )
    _credit(axes[1])
    _save(fig, "fig_underwater.png")


# ----------------------------------------------------------------------------
# 5. Walk-forward parameter stability heatmaps
# ----------------------------------------------------------------------------
def figure_param_stability() -> None:
    ty = pd.read_csv(RESULTS / "TY_5m" / "TY_5m_walkforward_params.csv")
    btc = pd.read_csv(RESULTS / "BTC_5m" / "BTC_5m_walkforward_params.csv")

    fig, axes = plt.subplots(2, 2, figsize=(13.0, 9.0))

    for col, (df, label, color) in enumerate(
        [
            (ty, "TY (155 quarterly periods)", COLUMBIA_NAVY),
            (btc, "BTC (7 quarterly periods)", COLUMBIA_GOLD),
        ]
    ):
        # Channel length L over time
        ax_l = axes[0, col]
        ax_l.plot(df["Period"], df["L"], color=color, marker="o", ms=3, lw=1.0)
        ax_l.set_title(f"{label} — channel length L by quarter")
        ax_l.set_xlabel("Walk-forward period #")
        ax_l.set_ylabel("L (5-min bars)")

        # Stop S over time
        ax_s = axes[1, col]
        ax_s.plot(df["Period"], df["S"], color=COLUMBIA_RED, marker="s", ms=3, lw=1.0)
        ax_s.set_title(f"{label} — drawdown stop S by quarter")
        ax_s.set_xlabel("Walk-forward period #")
        ax_s.set_ylabel("S (fraction)")

    fig.suptitle(
        "Walk-forward parameter stability — chosen (L, S) per quarter",
        color=COLUMBIA_NAVY,
        fontweight="bold",
        fontsize=14,
        y=1.00,
    )
    _credit(axes[1, 1])
    _save(fig, "fig_param_stability.png")


# ----------------------------------------------------------------------------
# 6. OOS vs IS profit per period (decay diagnostic)
# ----------------------------------------------------------------------------
def figure_is_oos_decay() -> None:
    ty = pd.read_csv(RESULTS / "TY_5m" / "TY_5m_walkforward_params.csv")
    btc = pd.read_csv(RESULTS / "BTC_5m" / "BTC_5m_walkforward_params.csv")

    fig, axes = plt.subplots(1, 2, figsize=(12.0, 4.6))

    for ax, df, label, color in [
        (axes[0], ty, "TY", COLUMBIA_NAVY),
        (axes[1], btc, "BTC", COLUMBIA_GOLD),
    ]:
        # Normalize IS profit per period by its 4-yr horizon, OOS by 1-quarter
        is_norm = df["IS_Profit"] / 16.0  # 16 quarters in 4 years
        oos = df["OOS_Profit"]
        ax.bar(df["Period"], is_norm, color=COLUMBIA_BLUE, alpha=0.55, label="IS profit / quarter (normalized)")
        ax.bar(df["Period"], oos, color=color, alpha=0.85, label="OOS profit / quarter", width=0.55)
        ax.axhline(0, color=COLUMBIA_INK, lw=0.6)
        ax.set_title(label)
        ax.set_xlabel("Walk-forward period #")
        ax.set_ylabel("Profit per quarter ($)")
        ax.legend(loc="upper left")

    fig.suptitle(
        "In-sample vs out-of-sample profit decay (per quarter, comparable scale)",
        color=COLUMBIA_NAVY,
        fontweight="bold",
        fontsize=14,
        y=1.04,
    )
    _credit(axes[1])
    _save(fig, "fig_is_oos_decay.png")


# ----------------------------------------------------------------------------
# 7. Trade ledger histograms (OOS PnL distribution + duration)
# ----------------------------------------------------------------------------
def figure_trade_distributions() -> None:
    ty = pd.read_csv(RESULTS / "TY_5m" / "TY_5m_walkforward_ledger.csv")
    btc = pd.read_csv(RESULTS / "BTC_5m" / "BTC_5m_walkforward_ledger.csv")

    fig, axes = plt.subplots(2, 2, figsize=(12.5, 8.0))

    for col, (df, label, color) in enumerate(
        [(ty, "TY", COLUMBIA_NAVY), (btc, "BTC", COLUMBIA_GOLD)]
    ):
        # PnL histogram
        ax_p = axes[0, col]
        win = df["pnl"][df["pnl"] > 0]
        loss = df["pnl"][df["pnl"] <= 0]
        bins = 40
        ax_p.hist(loss, bins=bins, color=COLUMBIA_RED, alpha=0.65, label=f"losers (n={len(loss)})")
        ax_p.hist(win, bins=bins, color=COLUMBIA_GREEN, alpha=0.75, label=f"winners (n={len(win)})")
        ax_p.axvline(0, color=COLUMBIA_INK, lw=0.8)
        ax_p.set_title(f"{label} — OOS trade PnL distribution")
        ax_p.set_xlabel("PnL ($)")
        ax_p.set_ylabel("count")
        ax_p.legend(loc="upper right")

        # Duration histogram (in bars)
        ax_d = axes[1, col]
        ax_d.hist(df["duration_bars"], bins=40, color=color, alpha=0.75)
        ax_d.set_title(f"{label} — OOS trade duration (bars)")
        ax_d.set_xlabel("Duration (5-min bars)")
        ax_d.set_ylabel("count")

    fig.suptitle(
        "Trade-ledger distributions — out-of-sample walk-forward",
        color=COLUMBIA_NAVY,
        fontweight="bold",
        fontsize=14,
        y=1.00,
    )
    _credit(axes[1, 1])
    _save(fig, "fig_trade_distributions.png")


# ----------------------------------------------------------------------------
# 8. IS vs OOS metric comparison bars
# ----------------------------------------------------------------------------
def figure_is_oos_comparison() -> None:
    ty_oos = pd.read_csv(RESULTS / "TY_5m" / "TY_5m_oos_metrics.csv").iloc[0]
    ty_full = pd.read_csv(RESULTS / "TY_5m" / "TY_5m_fullsample_metrics.csv").iloc[0]
    btc_oos = pd.read_csv(RESULTS / "BTC_5m" / "BTC_5m_oos_metrics.csv").iloc[0]
    btc_full = pd.read_csv(RESULTS / "BTC_5m" / "BTC_5m_fullsample_metrics.csv").iloc[0]

    metrics = [
        ("Ann. Return %", "Ann. Return %"),
        ("Sharpe Ratio", "Sharpe Ratio"),
        ("Return on Account", "Return on Account"),
        ("Profit Factor", "Profit Factor"),
        ("Win Rate %", "Win Rate %"),
    ]

    fig, axes = plt.subplots(1, 2, figsize=(13.0, 4.8), sharey=False)

    for ax, oos, full, label, color in [
        (axes[0], ty_oos, ty_full, "TY", COLUMBIA_NAVY),
        (axes[1], btc_oos, btc_full, "BTC", COLUMBIA_GOLD),
    ]:
        x = np.arange(len(metrics))
        width = 0.36
        oos_vals = [oos[name] for _, name in metrics]
        full_vals = [full[name] for _, name in metrics]
        ax.bar(x - width / 2, full_vals, width, color=COLUMBIA_BLUE, label="Full-sample (IS overlap)")
        ax.bar(x + width / 2, oos_vals, width, color=color, label="OOS walk-forward")
        ax.set_xticks(x, [m for m, _ in metrics], rotation=20, ha="right")
        ax.set_title(label)
        ax.legend(loc="upper right")
        ax.axhline(0, color=COLUMBIA_INK, lw=0.6)

    fig.suptitle(
        "Performance decay — full-sample vs out-of-sample walk-forward",
        color=COLUMBIA_NAVY,
        fontweight="bold",
        fontsize=14,
        y=1.04,
    )
    _credit(axes[1])
    _save(fig, "fig_is_oos_metrics.png")


# ----------------------------------------------------------------------------
# 9. Cumulative trade PnL vs trade index
# ----------------------------------------------------------------------------
def figure_cumulative_trades() -> None:
    ty = pd.read_csv(RESULTS / "TY_5m" / "TY_5m_walkforward_ledger.csv")
    btc = pd.read_csv(RESULTS / "BTC_5m" / "BTC_5m_walkforward_ledger.csv")

    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.6))

    for ax, df, label, color in [
        (axes[0], ty, "TY", COLUMBIA_NAVY),
        (axes[1], btc, "BTC", COLUMBIA_GOLD),
    ]:
        cum = df["pnl"].cumsum().values
        idx = np.arange(1, len(cum) + 1)
        ax.plot(idx, cum, color=color, lw=1.4)
        ax.fill_between(idx, 0, cum, color=color, alpha=0.10)
        ax.axhline(0, color=COLUMBIA_INK, lw=0.6)
        ax.set_xlabel("Closed-trade index (chronological)")
        ax.set_ylabel("Cumulative PnL ($)")
        ax.set_title(f"{label} — cumulative ledger PnL")
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v/1000:,.0f}k"))

    fig.suptitle(
        "Cumulative trade-by-trade PnL (OOS only)",
        color=COLUMBIA_NAVY,
        fontweight="bold",
        fontsize=14,
        y=1.04,
    )
    _credit(axes[1])
    _save(fig, "fig_cumulative_trades.png")


# ----------------------------------------------------------------------------
# 10. TY 5-min vs 1-min comparison
# ----------------------------------------------------------------------------
def figure_ty_resolution() -> None:
    ty_5_oos = pd.read_csv(RESULTS / "TY_5m" / "TY_5m_oos_metrics.csv").iloc[0]
    ty_1_oos = pd.read_csv(RESULTS / "TY_1m" / "TY_1m_oos_metrics.csv").iloc[0]
    ty_5_full = pd.read_csv(RESULTS / "TY_5m" / "TY_5m_fullsample_metrics.csv").iloc[0]
    ty_1_full = pd.read_csv(RESULTS / "TY_1m" / "TY_1m_fullsample_metrics.csv").iloc[0]

    metrics = [
        "Ann. Return %",
        "Sharpe Ratio",
        "Return on Account",
        "Profit Factor",
        "Win Rate %",
    ]

    fig, axes = plt.subplots(1, 2, figsize=(13.0, 4.8))

    for ax, m5, m1, label in [
        (axes[0], ty_5_full, ty_1_full, "TY full sample"),
        (axes[1], ty_5_oos, ty_1_oos, "TY OOS walk-forward"),
    ]:
        x = np.arange(len(metrics))
        width = 0.36
        v5 = [m5[k] for k in metrics]
        v1 = [m1[k] for k in metrics]
        ax.bar(x - width / 2, v5, width, color=COLUMBIA_BLUE, label="5-min bars")
        ax.bar(x + width / 2, v1, width, color=COLUMBIA_NAVY, label="1-min bars")
        ax.set_xticks(x, metrics, rotation=20, ha="right")
        ax.axhline(0, color=COLUMBIA_INK, lw=0.6)
        ax.set_title(label)
        ax.legend(loc="upper right")

    fig.suptitle(
        "TY data resolution comparison — 5-minute vs 1-minute bars",
        color=COLUMBIA_NAVY,
        fontweight="bold",
        fontsize=14,
        y=1.04,
    )
    _credit(axes[1])
    _save(fig, "fig_ty_resolution_comparison.png")


# ----------------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------------
def main() -> None:
    apply_theme()
    figure_vr_curves()
    figure_push_response()
    figure_equity_curves()
    figure_underwater()
    figure_param_stability()
    figure_is_oos_decay()
    figure_trade_distributions()
    figure_is_oos_comparison()
    figure_cumulative_trades()
    if (RESULTS / "TY_1m" / "TY_1m_oos_metrics.csv").exists():
        figure_ty_resolution()
    print(f"[ok] figures written to {FIG.resolve()}")
    for p in sorted(FIG.glob("*.png")):
        print(" -", p.name)


if __name__ == "__main__":
    main()
