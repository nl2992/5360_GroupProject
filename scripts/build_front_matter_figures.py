"""
Build the front-matter (slides 1–13) Columbia-themed figures.

Outputs into: report/presentation/figures/front_*.png
"""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrow, FancyBboxPatch
from matplotlib.ticker import FuncFormatter

# Columbia palette ------------------------------------------------------------
COL_NAVY = "#012169"
COL_BLUE = "#B9D9EB"
COL_INK = "#1B365D"
COL_GOLD = "#A28D5B"
COL_GREY = "#9AA1A9"
COL_LIGHT = "#E6E9EE"
COL_RED = "#A03033"
COL_GREEN = "#3F6F4A"
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
            "axes.labelsize": 10,
            "axes.grid": True,
            "grid.color": COL_LIGHT,
            "grid.linewidth": 0.7,
            "xtick.color": COL_CHARCOAL,
            "ytick.color": COL_CHARCOAL,
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "savefig.bbox": "tight",
            "savefig.dpi": 180,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "legend.frameon": False,
        }
    )


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "report" / "presentation" / "figures"
OUT.mkdir(parents=True, exist_ok=True)


def _save(fig, name):
    out = OUT / name
    fig.savefig(out)
    plt.close(fig)
    return out


def _credit(ax, text="Source: Group 1 — TF Data 5-min OHLC"):
    ax.text(
        0.0,
        -0.15,
        text,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=8,
        color=COL_GREY,
    )


def _load_ohlc(file_name: str) -> pd.DataFrame:
    df = pd.read_csv(DATA / file_name)
    df["DateTime"] = pd.to_datetime(df["Date"] + " " + df["Time"], format="%m/%d/%Y %H:%M")
    return df.set_index("DateTime")[["Close"]]


# -----------------------------------------------------------------------------
# 1. TY long-term price overview
# -----------------------------------------------------------------------------
def figure_ty_price():
    df = _load_ohlc("TY-5minHLV.csv")
    # Daily resample for legibility on a 43-year span
    daily = df["Close"].resample("D").last().dropna()
    fig, ax = plt.subplots(figsize=(11.5, 5.0))
    ax.fill_between(daily.index, daily.values, daily.min(), color=COL_BLUE, alpha=0.35)
    ax.plot(daily.index, daily.values, color=COL_NAVY, lw=1.2)
    ax.set_title("TY (10-yr Treasury futures) — daily-resampled close price, 1983–2026",
                 color=COL_NAVY, fontsize=14, loc="left")
    ax.set_ylabel("Price (points)")
    ax.set_xlabel("Date")
    # Fact box
    fact = (
        f"Span: 03 Jan 1983 → 10 Apr 2026   |   {len(df):,} 5-min bars   |   "
        f"Session: 07:20–14:00 CT (80 bars/day)\n"
        f"Min: {daily.min():.2f}   |   Max: {daily.max():.2f}   |   "
        f"Slippage: \\$18.625 / round-turn   |   Point value: \\$1,000"
    )
    ax.text(0.01, 0.97, fact, transform=ax.transAxes, va="top", ha="left", fontsize=9,
            bbox=dict(boxstyle="round", fc=COL_CREAM, ec=COL_INK, lw=0.6))
    _credit(ax)
    _save(fig, "front_ty_price_history.png")


# -----------------------------------------------------------------------------
# 2. BTC long-term price overview
# -----------------------------------------------------------------------------
def figure_btc_price():
    df = _load_ohlc("BTC-5minHLV.csv")
    daily = df["Close"].resample("D").last().dropna()
    fig, ax = plt.subplots(figsize=(11.5, 5.0))
    ax.fill_between(daily.index, daily.values, daily.min(), color=COL_GOLD, alpha=0.20)
    ax.plot(daily.index, daily.values, color=COL_GOLD, lw=1.4)
    ax.set_title("BTC (CME Bitcoin futures) — daily-resampled close price, 2017–2026",
                 color=COL_NAVY, fontsize=14, loc="left")
    ax.set_ylabel("Price (USD)")
    ax.set_xlabel("Date")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v/1000:,.0f}k"))
    fact = (
        f"Span: 18 Dec 2017 → 10 Apr 2026   |   {len(df):,} 5-min bars   |   "
        f"Session: 17:00–16:00 CT (276 bars/day)\n"
        f"Min: \\${daily.min():,.0f}   |   Max: \\${daily.max():,.0f}   |   "
        f"Slippage: \\$25.00 / round-turn   |   Point value: \\$5"
    )
    ax.text(0.01, 0.97, fact, transform=ax.transAxes, va="top", ha="left", fontsize=9,
            bbox=dict(boxstyle="round", fc=COL_CREAM, ec=COL_INK, lw=0.6))
    _credit(ax)
    _save(fig, "front_btc_price_history.png")


# -----------------------------------------------------------------------------
# 3. Horizon-spectrum infographic
# -----------------------------------------------------------------------------
def figure_horizon_spectrum():
    fig, ax = plt.subplots(figsize=(11.5, 4.2))
    # Spectrum bar
    xs = np.linspace(0, 1, 1000)
    # Three-zone gradient: mean-revert (red) → mixed (cream) → trend (navy)
    for i, x in enumerate(xs):
        if x < 0.33:
            t = x / 0.33
            color = (1 - t) * np.array([0xA0, 0x30, 0x33]) / 255 + t * np.array(
                [0xF4, 0xF1, 0xEA]
            ) / 255
        elif x < 0.66:
            t = (x - 0.33) / 0.33
            color = (1 - t) * np.array([0xF4, 0xF1, 0xEA]) / 255 + t * np.array(
                [0xB9, 0xD9, 0xEB]
            ) / 255
        else:
            t = (x - 0.66) / 0.34
            color = (1 - t) * np.array([0xB9, 0xD9, 0xEB]) / 255 + t * np.array(
                [0x01, 0x21, 0x69]
            ) / 255
        ax.axvspan(x - 0.001, x + 0.001, ymin=0.45, ymax=0.6, color=color)
    # Zone labels
    ax.text(0.165, 0.75, "MEAN-REVERTING", ha="center", color=COL_RED, fontsize=11, fontweight="bold",
            transform=ax.transAxes)
    ax.text(0.495, 0.75, "MIXED / AMBIGUOUS", ha="center", color=COL_GOLD, fontsize=11, fontweight="bold",
            transform=ax.transAxes)
    ax.text(0.835, 0.75, "TREND-FOLLOWING", ha="center", color=COL_NAVY, fontsize=11, fontweight="bold",
            transform=ax.transAxes)
    # Market markers
    btc_x = 0.62  # BTC: ~12 days = trend horizon
    ty_x = 0.85  # TY: ~18 sessions
    # BTC arrow
    ax.annotate("BTC\n12-day trend (ρ = +0.67)\nL* ≈ 276 bars", xy=(btc_x, 0.45), xytext=(btc_x, 0.20),
                ha="center", fontsize=10, color=COL_GOLD, fontweight="bold",
                arrowprops=dict(arrowstyle="-|>", color=COL_GOLD, lw=1.4),
                xycoords="axes fraction", textcoords="axes fraction")
    # TY arrow
    ax.annotate("TY\n18-session trend (ρ = +0.59)\nL* ≈ 1 920 bars", xy=(ty_x, 0.45),
                xytext=(ty_x, 0.20), ha="center", fontsize=10, color=COL_NAVY, fontweight="bold",
                arrowprops=dict(arrowstyle="-|>", color=COL_NAVY, lw=1.4),
                xycoords="axes fraction", textcoords="axes fraction")
    # Caption
    ax.text(0.5, 0.02, "Horizon spectrum — both markets live on the trend-following side, but at very different time-scales.",
            ha="center", color=COL_INK, fontsize=10, transform=ax.transAxes, fontstyle="italic")
    # Title
    ax.set_title("Where each market lives on the trend / mean-reversion spectrum",
                 color=COL_NAVY, fontsize=14, fontweight="bold", loc="left")
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(False)
    _save(fig, "front_horizon_spectrum.png")


# -----------------------------------------------------------------------------
# 4. Variance Ratio test definition card
# -----------------------------------------------------------------------------
def figure_vr_test_card():
    fig, ax = plt.subplots(figsize=(11.5, 4.0))
    ax.set_axis_off()
    fig.patch.set_facecolor("white")

    # Headline
    fig.text(0.04, 0.88, "Lo–MacKinlay Variance Ratio test", color=COL_NAVY,
             fontsize=20, fontweight="bold")

    # Formula in a centered box
    formula_box = FancyBboxPatch((0.07, 0.45), 0.86, 0.22,
                                  boxstyle="round,pad=0.02",
                                  fc=COL_CREAM, ec=COL_INK, lw=0.8,
                                  transform=fig.transFigure)
    fig.patches.append(formula_box)
    fig.text(0.50, 0.575, r"$VR(q)\ =\ \dfrac{\mathrm{Var}[r_t(q)]}{q\,\mathrm{Var}[r_t(1)]}$",
             ha="center", va="center", fontsize=22, color=COL_NAVY)
    fig.text(0.50, 0.46,
             "compared against the random-walk null  VR(q) = 1.  Heteroskedasticity-robust Z-statistic Z₂*.",
             ha="center", va="top", fontsize=10, color=COL_GREY, style="italic")

    # Interpretation row
    fig.text(0.04, 0.34, "Interpretation", color=COL_NAVY, fontsize=12, fontweight="bold")

    rows = [
        ("VR(q) > 1", "positive serial correlation → trend-following", COL_GREEN),
        ("VR(q) ≈ 1", "consistent with random-walk null", COL_GREY),
        ("VR(q) < 1", "negative serial correlation → mean-reverting", COL_RED),
    ]
    for i, (lhs, rhs, color) in enumerate(rows):
        y = 0.27 - i * 0.06
        fig.text(0.06, y, lhs, color=color, fontsize=11, fontweight="bold", family="DejaVu Sans Mono")
        fig.text(0.18, y, rhs, color=COL_INK, fontsize=11)

    fig.text(0.04, 0.04, "Source: Lo & MacKinlay (1988), Review of Financial Studies",
             color=COL_GREY, fontsize=8.5)
    _save(fig, "front_vr_test_card.png")


# -----------------------------------------------------------------------------
# 5. Push–Response test definition card
# -----------------------------------------------------------------------------
def figure_pr_test_card():
    fig, ax = plt.subplots(figsize=(11.5, 4.0))
    ax.set_axis_off()
    fig.patch.set_facecolor("white")
    fig.text(0.04, 0.88, "Push–Response test", color=COL_NAVY,
             fontsize=20, fontweight="bold")

    box = FancyBboxPatch((0.07, 0.40), 0.86, 0.30,
                          boxstyle="round,pad=0.02",
                          fc=COL_CREAM, ec=COL_INK, lw=0.8,
                          transform=fig.transFigure)
    fig.patches.append(box)

    fig.text(0.50, 0.62,
             r"$\mathrm{push}_t = p_t - p_{t-\tau}$    "
             r"$\mathrm{response}_t = p_{t+\tau} - p_t$",
             ha="center", va="center", fontsize=18, color=COL_NAVY)
    fig.text(0.50, 0.50,
             "Bin pushes by decile, plot the conditional mean of the response per bin.\n"
             r"Spearman $\rho$ on (push, response) measures monotonic predictability.",
             ha="center", va="top", fontsize=10, color=COL_INK)

    rows = [
        ("ρ > 0", "monotonically increasing — trend-following", COL_GREEN),
        ("ρ ≈ 0", "no monotone predictability", COL_GREY),
        ("ρ < 0", "monotonically decreasing — mean-reverting", COL_RED),
    ]
    fig.text(0.04, 0.30, "Interpretation", color=COL_NAVY, fontsize=12, fontweight="bold")
    for i, (lhs, rhs, color) in enumerate(rows):
        y = 0.23 - i * 0.06
        fig.text(0.06, y, lhs, color=color, fontsize=11, fontweight="bold", family="DejaVu Sans Mono")
        fig.text(0.16, y, rhs, color=COL_INK, fontsize=11)

    fig.text(0.04, 0.04, "Source: Lecture 4 — Lehalle & Laruelle (2013), Market Microstructure in Practice",
             color=COL_GREY, fontsize=8.5)
    _save(fig, "front_pr_test_card.png")


# -----------------------------------------------------------------------------
# 6. Why-different-horizons institutional context (TY)
# -----------------------------------------------------------------------------
def figure_horizons_context():
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6))
    # TY card
    ax_ty = axes[0]
    ax_ty.set_axis_off()
    ax_ty.add_patch(FancyBboxPatch((0.02, 0.02), 0.96, 0.96,
                                    boxstyle="round,pad=0.02",
                                    fc=COL_CREAM, ec=COL_NAVY, lw=1.2,
                                    transform=ax_ty.transAxes))
    ax_ty.text(0.5, 0.94, "TY — slow trend regime", color=COL_NAVY, fontsize=14,
               fontweight="bold", ha="center", transform=ax_ty.transAxes)
    items_ty = [
        ("Players", "Pension funds, insurers, central banks — slow macro reactors."),
        ("Drivers", "FOMC, inflation prints, fiscal news — multi-day to multi-week moves."),
        ("Vol", "Annualised ~4–6%; intraday is mostly bid-ask noise."),
        ("Microstructure", "Deep liquid book — short-term arbitrage corrects deviations fast."),
        ("Implication", "Channel L > 500 bars (~ multi-week) needed to filter noise."),
    ]
    for i, (k, v) in enumerate(items_ty):
        y = 0.78 - i * 0.13
        ax_ty.text(0.06, y, k, color=COL_GOLD, fontsize=10.5, fontweight="bold",
                   transform=ax_ty.transAxes)
        ax_ty.text(0.34, y, v, color=COL_INK, fontsize=10.5,
                   transform=ax_ty.transAxes, wrap=True)

    # BTC card
    ax_btc = axes[1]
    ax_btc.set_axis_off()
    ax_btc.add_patch(FancyBboxPatch((0.02, 0.02), 0.96, 0.96,
                                     boxstyle="round,pad=0.02",
                                     fc=COL_CREAM, ec=COL_GOLD, lw=1.2,
                                     transform=ax_btc.transAxes))
    ax_btc.text(0.5, 0.94, "BTC — fast trend regime", color=COL_GOLD, fontsize=14,
                fontweight="bold", ha="center", transform=ax_btc.transAxes)
    items_btc = [
        ("Players", "Retail + algorithmic momentum — self-reinforcing flows."),
        ("Drivers", "Regulatory news, exchange events, risk-off — minutes to days."),
        ("Vol", "Annualised ~30–60%; intraday signal-to-noise is high."),
        ("Microstructure", "Thinner book; large flows leave persistent imprints."),
        ("Implication", "Channel L ≈ 276 bars (1 day) is enough to identify breakouts."),
    ]
    for i, (k, v) in enumerate(items_btc):
        y = 0.78 - i * 0.13
        ax_btc.text(0.06, y, k, color=COL_NAVY, fontsize=10.5, fontweight="bold",
                    transform=ax_btc.transAxes)
        ax_btc.text(0.34, y, v, color=COL_INK, fontsize=10.5,
                    transform=ax_btc.transAxes, wrap=True)

    fig.suptitle("Why the same trend principle uses different horizons in TY and BTC",
                 color=COL_NAVY, fontsize=14, fontweight="bold", y=1.02)
    _save(fig, "front_horizons_context.png")


# -----------------------------------------------------------------------------
# 7. Walk-forward design schematic
# -----------------------------------------------------------------------------
def figure_walkforward_schematic():
    fig, ax = plt.subplots(figsize=(11.5, 3.8))
    ax.set_axis_off()
    # Three IS+OOS rows showing the rolling design
    rows = 3
    row_h = 0.18
    gap = 0.04
    for r in range(rows):
        y = 0.78 - r * (row_h + gap)
        # IS bar (4 years wide)
        is_left = 0.05 + r * 0.07
        is_w = 0.6
        ax.add_patch(FancyBboxPatch((is_left, y), is_w, row_h,
                                     boxstyle="round,pad=0.005",
                                     fc=COL_BLUE, ec=COL_NAVY, lw=0.8,
                                     transform=ax.transAxes))
        ax.text(is_left + is_w / 2, y + row_h / 2, f"In-sample · 4 years (period {r + 1})",
                ha="center", va="center", color=COL_NAVY, fontsize=10, fontweight="bold",
                transform=ax.transAxes)
        # OOS bar (1 quarter, narrower)
        oos_left = is_left + is_w + 0.005
        oos_w = 0.10
        ax.add_patch(FancyBboxPatch((oos_left, y), oos_w, row_h,
                                     boxstyle="round,pad=0.005",
                                     fc=COL_GOLD, ec=COL_NAVY, lw=0.8,
                                     transform=ax.transAxes))
        ax.text(oos_left + oos_w / 2, y + row_h / 2, f"OOS Q{r + 1}",
                ha="center", va="center", color=COL_NAVY, fontsize=10, fontweight="bold",
                transform=ax.transAxes)
    # Vertical legend on right
    ax.text(0.85, 0.78, "T = 4 years IS", color=COL_NAVY, fontsize=11, fontweight="bold",
            transform=ax.transAxes, va="top")
    ax.text(0.85, 0.70, "τ = 1 quarter OOS", color=COL_GOLD, fontsize=11, fontweight="bold",
            transform=ax.transAxes, va="top")
    ax.text(0.85, 0.62, "rolls forward 1 quarter\nper iteration", color=COL_INK, fontsize=10,
            transform=ax.transAxes, va="top")
    ax.text(0.85, 0.44, "Objective:\n  Net Profit / Max DD\nFull-grid search over\n  L ∈ [500, 10 000] step 10\n  S ∈ [0.005, 0.10] step 0.001",
            color=COL_INK, fontsize=9.5, transform=ax.transAxes, va="top",
            family="DejaVu Sans Mono",
            bbox=dict(boxstyle="round", fc=COL_CREAM, ec=COL_INK, lw=0.5))

    ax.text(0.5, 0.07, "Walk-forward schematic — every 4-year IS optimum is evaluated on the next quarter OOS, then the window slides forward one quarter.",
            ha="center", color=COL_GREY, fontsize=9.5, transform=ax.transAxes, fontstyle="italic")
    fig.suptitle("Rolling 4-year IS → 1-quarter OOS walk-forward",
                 color=COL_NAVY, fontsize=14, fontweight="bold", y=1.02)
    _save(fig, "front_walkforward_schematic.png")


def main():
    apply_theme()
    figure_ty_price()
    figure_btc_price()
    figure_horizon_spectrum()
    figure_vr_test_card()
    figure_pr_test_card()
    figure_horizons_context()
    figure_walkforward_schematic()
    print(f"[ok] front-matter figures written to {OUT.resolve()}")
    for p in sorted(OUT.glob("front_*.png")):
        print(" -", p.name)


if __name__ == "__main__":
    main()
