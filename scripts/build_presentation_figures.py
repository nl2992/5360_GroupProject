"""
Build the per-slide presentation deck images for the final project.

Each figure is a self-contained slide-ready PNG, broken out one-per-market
(no side-by-side panels), in a Bloomberg-style minimalist Columbia palette.

Outputs to: report/presentation/figures/
Companion narrative: report/presentation/demo.md
"""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch
from matplotlib.ticker import FuncFormatter

# ----------------------------------------------------------------------------
# Columbia palette — same as the canonical report
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
LIGHT_GREY = "#E6E9EE"


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
            "axes.labelsize": 10,
            "axes.grid": True,
            "grid.color": LIGHT_GREY,
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
            "savefig.dpi": 180,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


# ----------------------------------------------------------------------------
# Paths
# ----------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / "results" / "walkforward"
DATA = ROOT / "data"
OUT = ROOT / "report" / "presentation" / "figures"
OUT.mkdir(parents=True, exist_ok=True)


def _save(fig: plt.Figure, name: str) -> Path:
    out = OUT / name
    fig.savefig(out)
    plt.close(fig)
    return out


def _credit(ax: plt.Axes, source: str = "Source: Group 1 walk-forward — TF Data 5-min OHLC") -> None:
    ax.text(
        0.0,
        -0.18,
        source,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=8,
        color=COLUMBIA_GREY,
    )


# ----------------------------------------------------------------------------
# Loaders
# ----------------------------------------------------------------------------
MARKETS = {
    "TY": {
        "label": "TY (10-yr Treasury futures)",
        "color": COLUMBIA_NAVY,
        "data_file": "TY-5minHLV.csv",
        "wf_dir": WF / "TY_5m",
        "prefix": "TY_5m",
        "point_value": 1000.0,
        "slippage": 18.625,
    },
    "BTC": {
        "label": "BTC (CME Bitcoin futures)",
        "color": COLUMBIA_GOLD,
        "data_file": "BTC-5minHLV.csv",
        "wf_dir": WF / "BTC_5m",
        "prefix": "BTC_5m",
        "point_value": 5.0,
        "slippage": 25.0,
    },
}


def load_equity(market: str) -> pd.DataFrame:
    cfg = MARKETS[market]
    p = cfg["wf_dir"] / f"{cfg['prefix']}_walkforward_equity.csv"
    return pd.read_csv(p, parse_dates=["DateTime"])


def load_ledger(market: str) -> pd.DataFrame:
    cfg = MARKETS[market]
    p = cfg["wf_dir"] / f"{cfg['prefix']}_walkforward_ledger.csv"
    df = pd.read_csv(p, parse_dates=["entry_time", "exit_time"])
    return df


def load_metrics(market: str, kind: str) -> pd.Series:
    cfg = MARKETS[market]
    p = cfg["wf_dir"] / f"{cfg['prefix']}_{kind}_metrics.csv"
    return pd.read_csv(p).iloc[0]


def load_ohlc(market: str) -> pd.DataFrame:
    cfg = MARKETS[market]
    df = pd.read_csv(DATA / cfg["data_file"])
    dt = pd.to_datetime(df["Date"] + " " + df["Time"], format="%m/%d/%Y %H:%M")
    df = df.assign(DateTime=dt).drop(columns=["Date", "Time"])
    return df.set_index("DateTime")


# ----------------------------------------------------------------------------
# Sortino + Calmar
# ----------------------------------------------------------------------------
def trade_returns(ledger: pd.DataFrame, equity_initial: float = 100_000.0) -> pd.Series:
    return ledger["pnl"] / equity_initial


def sortino(ledger: pd.DataFrame, ann_return_pct: float, periods_per_year: int = 252) -> float:
    r = trade_returns(ledger)
    if r.empty:
        return np.nan
    downside = r[r < 0]
    if downside.empty:
        return np.nan
    # annualised downside vol via per-year average
    n_years = max((ledger["exit_time"].max() - ledger["entry_time"].min()).days / 365.25, 1)
    trades_per_year = len(r) / n_years
    ann_downside = downside.std(ddof=1) * np.sqrt(trades_per_year) * 100
    if ann_downside <= 0:
        return np.nan
    return float(ann_return_pct) / ann_downside


# ----------------------------------------------------------------------------
# 1. Performance Metrics table (Bloomberg-style)
# ----------------------------------------------------------------------------
def figure_metrics_table() -> None:
    cols = []
    rows = ["Annualised Return", "Volatility", "Sharpe Ratio", "Sortino Ratio",
            "Maximum Drawdown", "Return on Account", "Calmar Ratio",
            "Profit Factor", "Win Rate", "Total Trades"]

    def cell_value(metrics: pd.Series, ledger: pd.DataFrame, key: str) -> str:
        ann_ret = float(metrics["Ann. Return %"])
        ann_vol = float(metrics["Ann. Volatility %"])
        sharpe = float(metrics["Sharpe Ratio"])
        mdd_pct = float(metrics["Max Drawdown %"])
        roa = float(metrics["Return on Account"])
        pf = float(metrics["Profit Factor"])
        win = float(metrics["Win Rate %"])
        n = int(metrics["Total Trades"])
        sort = sortino(ledger, ann_ret) if ledger is not None else np.nan
        calmar = ann_ret / abs(mdd_pct) if abs(mdd_pct) > 0 else np.nan
        mapping = {
            "Annualised Return": f"{ann_ret:5.2f}%",
            "Volatility": f"{ann_vol:5.2f}%",
            "Sharpe Ratio": f"{sharpe:5.2f}",
            "Sortino Ratio": f"{sort:5.2f}" if not np.isnan(sort) else "n/a",
            "Maximum Drawdown": f"-{abs(mdd_pct):5.2f}%",
            "Return on Account": f"{roa:5.2f}",
            "Calmar Ratio": f"{calmar:5.2f}",
            "Profit Factor": f"{pf:5.2f}",
            "Win Rate": f"{win:5.2f}%",
            "Total Trades": f"{n:>5d}",
        }
        return mapping[key]

    # Build columns: TY OOS, TY Full, BTC OOS, BTC Full
    cells: dict[str, dict[str, str]] = {row: {} for row in rows}
    col_keys = [("TY OOS", "TY", "oos"), ("TY Full", "TY", "fullsample"),
                ("BTC OOS", "BTC", "oos"), ("BTC Full", "BTC", "fullsample")]
    for col_label, market, kind in col_keys:
        m = load_metrics(market, kind)
        # ledger only for OOS variant
        ldg = load_ledger(market) if kind == "oos" else None
        for r in rows:
            cells[r][col_label] = cell_value(m, ldg, r)

    fig, ax = plt.subplots(figsize=(9.0, 5.6))
    ax.set_axis_off()
    fig.patch.set_facecolor("white")

    # Title
    fig.text(0.07, 0.94, "Performance Metrics", color=COLUMBIA_NAVY, fontsize=18, fontweight="bold")

    # Column headers — push label column narrower, data columns to the right
    col_labels = [c[0] for c in col_keys]
    label_x = 0.10
    data_xs = np.linspace(0.46, 0.94, len(col_labels))
    col_x = np.concatenate([[label_x], data_xs])
    n_cols = len(col_x)

    header_y = 0.83
    fig.text(col_x[0], header_y, "", color=COLUMBIA_INK, fontsize=11, fontweight="bold")
    for i, lbl in enumerate(col_labels):
        fig.text(col_x[i + 1], header_y, lbl, color=COLUMBIA_NAVY, fontsize=11, fontweight="bold", ha="right")

    # Underline header row
    fig.add_artist(plt.Line2D([0.07, 0.96], [header_y - 0.02, header_y - 0.02], color=COLUMBIA_INK, lw=1.2))

    # Rows
    row_y0 = 0.74
    row_dy = 0.067
    for i, row in enumerate(rows):
        y = row_y0 - i * row_dy
        fig.text(col_x[0], y, row, color=COLUMBIA_INK, fontsize=10.5, ha="left")
        for j, col_label in enumerate(col_labels):
            val = cells[row][col_label]
            color = COLUMBIA_RED if val.startswith("-") else COLUMBIA_CHARCOAL
            fig.text(col_x[j + 1], y, val, color=color, fontsize=10.5, ha="right", family="DejaVu Sans Mono")
        # separator
        if i < len(rows) - 1:
            fig.add_artist(plt.Line2D([0.07, 0.96], [y - 0.02, y - 0.02], color=LIGHT_GREY, lw=0.6))

    # Footer
    fig.text(0.07, 0.04, "Source: Group 1 walk-forward (TF Data 5-min OHLC, $100k initial equity)",
             color=COLUMBIA_GREY, fontsize=8.5)
    _save(fig, "slide_01_performance_metrics.png")


# ----------------------------------------------------------------------------
# 2. Per-market equity + position panel (one image each)
# ----------------------------------------------------------------------------
def _position_series_from_ledger(eq: pd.DataFrame, ledger: pd.DataFrame) -> np.ndarray:
    """Build a piecewise-constant position series at equity-bar resolution."""
    pos = np.zeros(len(eq), dtype=int)
    times = eq["DateTime"].values
    for _, t in ledger.iterrows():
        i0 = np.searchsorted(times, np.datetime64(t["entry_time"]))
        i1 = np.searchsorted(times, np.datetime64(t["exit_time"]))
        pos[i0:i1 + 1] = int(t["direction"])
    return pos


def figure_market_equity_with_position(market: str) -> None:
    cfg = MARKETS[market]
    eq = load_equity(market)
    ledger = load_ledger(market)
    pos = _position_series_from_ledger(eq, ledger)

    metrics = load_metrics(market, "oos")
    profit = float(metrics["Total Profit"])
    sharpe = float(metrics["Sharpe Ratio"])
    roa = float(metrics["Return on Account"])
    n_trades = int(metrics["Total Trades"])

    fig = plt.figure(figsize=(11.5, 6.4))
    gs = fig.add_gridspec(3, 1, height_ratios=[1.0, 0.25, 3.0], hspace=0.18)
    ax_pos = fig.add_subplot(gs[0])
    ax_eq = fig.add_subplot(gs[2], sharex=ax_pos)

    # Position panel — coloured band: long=green, short=red, flat=grey
    long_mask = pos == 1
    short_mask = pos == -1
    flat_mask = pos == 0
    times = eq["DateTime"].values

    ax_pos.fill_between(times, 0, 1, where=long_mask, color=COLUMBIA_GREEN, step="mid", alpha=0.85, label="Long")
    ax_pos.fill_between(times, 0, 1, where=short_mask, color=COLUMBIA_RED, step="mid", alpha=0.85, label="Short")
    ax_pos.fill_between(times, 0, 1, where=flat_mask, color=LIGHT_GREY, step="mid", alpha=0.85, label="Flat")
    ax_pos.set_yticks([])
    ax_pos.set_ylim(0, 1)
    ax_pos.set_title(f"{cfg['label']} — portfolio position", color=COLUMBIA_NAVY, fontsize=12, loc="left")
    ax_pos.legend(loc="upper right", ncol=3, fontsize=8.5)
    ax_pos.tick_params(axis="x", labelbottom=False)
    for s in ("left", "top", "right"):
        ax_pos.spines[s].set_visible(False)

    # Equity panel
    ax_eq.plot(times, eq["OOS_Equity"], color=cfg["color"], lw=1.4)
    ax_eq.fill_between(times, 100_000.0, eq["OOS_Equity"], color=cfg["color"], alpha=0.10)
    ax_eq.axhline(100_000.0, color=COLUMBIA_GREY, lw=0.8, ls="--")
    ax_eq.set_title(f"{cfg['label']} — out-of-sample equity curve", color=COLUMBIA_NAVY, fontsize=12, loc="left")
    ax_eq.set_ylabel("Equity ($)")
    ax_eq.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v/1000:,.0f}k"))
    ax_eq.set_xlabel("Date")

    box = (
        f"Net OOS profit: ${profit:,.0f}\n"
        f"Return on Account: {roa:,.2f}×\n"
        f"Sharpe (OOS): {sharpe:,.2f}\n"
        f"Closed trades: {n_trades:,d}"
    )
    ax_eq.text(0.01, 0.97, box, transform=ax_eq.transAxes, va="top", ha="left", fontsize=9,
               bbox=dict(boxstyle="round", fc=COLUMBIA_CREAM, ec=COLUMBIA_INK, lw=0.6))

    _credit(ax_eq)
    _save(fig, f"slide_02_{market.lower()}_equity_position.png")


# ----------------------------------------------------------------------------
# 3. Per-market drawdown family (Chekhlov)
# ----------------------------------------------------------------------------
def figure_market_drawdown(market: str) -> None:
    cfg = MARKETS[market]
    eq = load_equity(market)
    metrics = load_metrics(market, "oos")

    peak = eq["OOS_Equity"].cummax()
    uw_pct = (eq["OOS_Equity"] - peak) / peak * 100.0
    uw_dollar = eq["OOS_Equity"] - peak

    mdd_dollar = float(metrics["Max Drawdown $"])
    mdd_pct = float(metrics["Max Drawdown %"])
    avg_dd = float(metrics["Avg Drawdown $"])
    cdd = float(metrics["CDD (α=0.05) $"])

    fig, axes = plt.subplots(2, 1, figsize=(11.5, 6.0), sharex=True)
    ax_p = axes[0]
    ax_d = axes[1]

    ax_p.fill_between(eq["DateTime"], uw_pct, 0, color=cfg["color"], alpha=0.45)
    ax_p.plot(eq["DateTime"], uw_pct, color=cfg["color"], lw=1.0)
    ax_p.axhline(0, color=COLUMBIA_INK, lw=0.6)
    ax_p.axhline(-mdd_pct, color=COLUMBIA_RED, lw=0.8, ls="--", label=f"Max DD = -{mdd_pct:,.2f}%")
    ax_p.set_title(f"{cfg['label']} — % drawdown vs running peak", color=COLUMBIA_NAVY, fontsize=12, loc="left")
    ax_p.set_ylabel("% off peak")
    ax_p.legend(loc="lower right")

    ax_d.fill_between(eq["DateTime"], uw_dollar, 0, color=cfg["color"], alpha=0.30)
    ax_d.plot(eq["DateTime"], uw_dollar, color=cfg["color"], lw=1.0)
    ax_d.axhline(0, color=COLUMBIA_INK, lw=0.6)
    ax_d.set_title(f"{cfg['label']} — $ drawdown vs running peak", color=COLUMBIA_NAVY, fontsize=12, loc="left")
    ax_d.set_ylabel("$ off peak")
    ax_d.set_xlabel("Date")
    ax_d.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v/1000:,.0f}k"))

    box = (
        f"Max DD: ${mdd_dollar:,.0f}  ({mdd_pct:,.2f}%)\n"
        f"Avg DD: ${avg_dd:,.0f}\n"
        f"CDD(α=0.05): ${cdd:,.0f}"
    )
    ax_d.text(0.01, 0.05, box, transform=ax_d.transAxes, va="bottom", ha="left", fontsize=9,
              bbox=dict(boxstyle="round", fc=COLUMBIA_CREAM, ec=COLUMBIA_INK, lw=0.6))
    _credit(ax_d)
    _save(fig, f"slide_03_{market.lower()}_drawdown_family.png")


# ----------------------------------------------------------------------------
# 4. Per-market trade PnL distribution
# ----------------------------------------------------------------------------
def figure_market_trade_distribution(market: str) -> None:
    cfg = MARKETS[market]
    ledger = load_ledger(market)
    pnl = ledger["pnl"]
    win = pnl[pnl > 0]
    loss = pnl[pnl <= 0]

    fig, ax = plt.subplots(figsize=(11.0, 5.0))
    bins = 40
    ax.hist(loss, bins=bins, color=COLUMBIA_RED, alpha=0.65, label=f"Losers (n={len(loss):,d})")
    ax.hist(win, bins=bins, color=COLUMBIA_GREEN, alpha=0.80, label=f"Winners (n={len(win):,d})")
    ax.axvline(0, color=COLUMBIA_INK, lw=0.8)
    ax.axvline(float(pnl.mean()), color=COLUMBIA_NAVY, lw=1.4, ls="--",
               label=f"Mean PnL = ${pnl.mean():,.0f}")
    ax.set_title(f"{cfg['label']} — out-of-sample trade PnL distribution",
                 color=COLUMBIA_NAVY, fontsize=12, loc="left")
    ax.set_xlabel("PnL ($)")
    ax.set_ylabel("Trade count")
    ax.legend(loc="upper right")
    box = (
        f"Avg winner: ${float(win.mean()):,.0f}   "
        f"Avg loser: ${float(loss.mean()):,.0f}\n"
        f"Best:  ${float(pnl.max()):,.0f}   "
        f"Worst: ${float(pnl.min()):,.0f}\n"
        f"Profit factor: {float(win.sum()) / abs(float(loss.sum())):,.2f}"
    )
    ax.text(0.01, 0.97, box, transform=ax.transAxes, va="top", ha="left", fontsize=9,
            bbox=dict(boxstyle="round", fc=COLUMBIA_CREAM, ec=COLUMBIA_INK, lw=0.6))
    _credit(ax)
    _save(fig, f"slide_04_{market.lower()}_trade_distribution.png")


# ----------------------------------------------------------------------------
# 5. Best / worst trade autopsy (with price-action overlay)
# ----------------------------------------------------------------------------
def _slice_ohlc_around(market: str, t0: pd.Timestamp, t1: pd.Timestamp, pad_pct: float = 0.4) -> pd.DataFrame:
    """Slice OHLC around a trade. We use an asymmetric pre/post pad and
    enforce a minimum window so very short trades (e.g. BTC's 25-minute
    breakout) still show enough pre-trade context for the chart to be
    legible — in particular, gaps and prior-session levels relevant to
    the channel break.
    """
    ohlc = load_ohlc(market)
    span = t1 - t0
    pre_pad = max(span * pad_pct, pd.Timedelta(days=3))
    post_pad = max(span * pad_pct, pd.Timedelta(hours=4))
    return ohlc.loc[t0 - pre_pad:t1 + post_pad]


def _draw_trade(ax: plt.Axes, market: str, trade: pd.Series, title: str, why: str, color: str) -> None:
    cfg = MARKETS[market]
    t0 = pd.Timestamp(trade["entry_time"])
    t1 = pd.Timestamp(trade["exit_time"])
    sub = _slice_ohlc_around(market, t0, t1)
    if sub.empty:
        return
    # Insert NaN breaks across data gaps > 30 minutes so the line plot
    # does not visually interpolate across weekends/exchange closes.
    closes = sub["Close"].copy().astype(float)
    if len(closes) > 1:
        deltas = closes.index.to_series().diff()
        gaps = deltas > pd.Timedelta(minutes=30)
        closes.loc[gaps] = np.nan
    ax.plot(closes.index, closes.values, color=color, lw=1.2)
    # Trade region shading
    ax.axvspan(t0, t1, color=color, alpha=0.10)
    # Entry / exit markers
    direction = "LONG" if int(trade["direction"]) == 1 else "SHORT"
    pnl = float(trade["pnl"])
    pnl_color = COLUMBIA_GREEN if pnl >= 0 else COLUMBIA_RED
    entry_price = float(trade["entry_price"])
    exit_price = float(trade["exit_price"])
    # Connect entry → exit with a thin dotted reference line so the
    # economic move (entry fill → exit fill) is unambiguous even when the
    # close-price line and the fill prices diverge (e.g. weekend gaps).
    ax.plot([t0, t1], [entry_price, exit_price], color=pnl_color, lw=1.0, ls=":", alpha=0.6)
    ax.scatter([t0], [entry_price], s=110, color=COLUMBIA_NAVY, zorder=5,
               edgecolor="white", linewidths=1.6, label=f"{direction} entry @ {entry_price:,.4g}")
    ax.scatter([t1], [exit_price], s=110, color=pnl_color, zorder=5, marker="X",
               edgecolor="white", linewidths=1.6, label=f"Exit @ {exit_price:,.4g}")
    # Make sure both fill prices are inside the y-axis visible range
    y_lo = min(float(sub["Low"].min()), entry_price, exit_price)
    y_hi = max(float(sub["High"].max()), entry_price, exit_price)
    pad = (y_hi - y_lo) * 0.06 if y_hi > y_lo else 1.0
    ax.set_ylim(y_lo - pad, y_hi + pad)
    # PnL banner
    pnl_txt = f"${pnl:,.0f}"
    ax.text(0.99, 0.97, f"PnL: {pnl_txt}", transform=ax.transAxes, ha="right", va="top",
            fontsize=12, fontweight="bold", color=pnl_color,
            bbox=dict(boxstyle="round", fc="white", ec=pnl_color, lw=1.2))
    # Why-it-got-cooked annotation. Place it in the empty quadrant:
    # if price ended higher than entry (long winner / short loser) → bottom-right is clear;
    # if price ended lower than entry → top-right is clear (PnL banner moves to top-left then).
    if exit_price >= entry_price:
        ax.text(0.99, 0.05, why, transform=ax.transAxes, ha="right", va="bottom",
                fontsize=9.5, bbox=dict(boxstyle="round", fc=COLUMBIA_CREAM, ec=COLUMBIA_INK, lw=0.6))
    else:
        ax.text(0.01, 0.05, why, transform=ax.transAxes, ha="left", va="bottom",
                fontsize=9.5, bbox=dict(boxstyle="round", fc=COLUMBIA_CREAM, ec=COLUMBIA_INK, lw=0.6))
    ax.set_title(title, color=COLUMBIA_NAVY, fontsize=12, loc="left")
    ax.set_ylabel("Price")
    ax.set_xlabel("Time")
    ax.legend(loc="upper left")


def figure_best_worst(market: str) -> None:
    cfg = MARKETS[market]
    ledger = load_ledger(market)
    best = ledger.loc[ledger["pnl"].idxmax()]
    worst = ledger.loc[ledger["pnl"].idxmin()]

    # WHY narratives, market-specific
    if market == "TY":
        why_best = (
            "Why it worked\n"
            "• Entered LONG on 21 Jan 2020 — TY broke above the 1920-bar high\n"
            "• Held 50 days as COVID drove a flight-to-safety bond rally\n"
            "• Exited 10 Mar 2020 on the equity trailing-stop after a 6.3pt move\n"
            "• Channel breakout + slow stop = textbook trend-following payoff"
        )
        why_worst = (
            "Why it got cooked\n"
            "• Entered LONG on 22 Feb 2002 — broke above a 3200-bar (40-day) high\n"
            "• Treasuries reversed almost immediately on hawkish Fed signals\n"
            "• Price slid 2.93pt in 12 days; trailing-stop fired at $-2,952 loss\n"
            "• Classic 'breakout caught at the local top before mean-reversion'\n"
            "• Wide L=3200 channel made the stop physically distant"
        )
    else:  # BTC
        why_best = (
            "Why it worked\n"
            "• Entered LONG on 02 Mar 2025 17:05 — broke above the 276-bar (1d) high\n"
            "• 25 minutes later BTC ripped from $85,720 → $94,748\n"
            "• Trailing-stop never fired; closed by next reversal signal\n"
            "• Crypto's late-2025 trend cycle paid this trade $45k in 5 bars"
        )
        why_worst = (
            "Why it got cooked\n"
            "• Entered SHORT on 22 Aug 2025 07:35 — broke below the 276-bar low\n"
            "• Within 90 minutes BTC pumped $2,115 (+1.9%) against the position\n"
            "• Tight 1% drawdown stop fired at $112,075 → $114,190\n"
            "• Channel breakout in a fast-mean-reverting regime is a common failure\n"
            "• The PR diagram already flags BTC as mean-reverting at the 1d horizon"
        )

    # Two figures: best & worst, separately
    fig_best, ax = plt.subplots(figsize=(11.5, 5.4))
    _draw_trade(ax, market, best, f"{cfg['label']} — most profitable OOS trade", why_best, cfg["color"])
    _credit(ax)
    _save(fig_best, f"slide_05_{market.lower()}_best_trade.png")

    fig_worst, ax = plt.subplots(figsize=(11.5, 5.4))
    _draw_trade(ax, market, worst, f"{cfg['label']} — worst OOS trade", why_worst, cfg["color"])
    _credit(ax)
    _save(fig_worst, f"slide_06_{market.lower()}_worst_trade.png")


# ----------------------------------------------------------------------------
# 6. Per-market parameter stability (single market)
# ----------------------------------------------------------------------------
def figure_market_param_stability(market: str) -> None:
    cfg = MARKETS[market]
    p = cfg["wf_dir"] / f"{cfg['prefix']}_walkforward_params.csv"
    df = pd.read_csv(p)

    fig, axes = plt.subplots(2, 1, figsize=(11.5, 5.6), sharex=True)
    axes[0].plot(df["Period"], df["L"], color=cfg["color"], marker="o", ms=3, lw=1.0)
    axes[0].set_title(f"{cfg['label']} — channel length L per quarterly OOS period",
                      color=COLUMBIA_NAVY, fontsize=12, loc="left")
    axes[0].set_ylabel("L (5-min bars)")

    axes[1].plot(df["Period"], df["S"], color=COLUMBIA_RED, marker="s", ms=3, lw=1.0)
    axes[1].set_title(f"{cfg['label']} — drawdown stop S per quarterly OOS period",
                      color=COLUMBIA_NAVY, fontsize=12, loc="left")
    axes[1].set_xlabel("Walk-forward period #")
    axes[1].set_ylabel("S (fraction)")
    _credit(axes[1])
    _save(fig, f"slide_07_{market.lower()}_param_stability.png")


# ----------------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------------
def main() -> None:
    apply_theme()
    figure_metrics_table()
    for mkt in ("TY", "BTC"):
        figure_market_equity_with_position(mkt)
        figure_market_drawdown(mkt)
        figure_market_trade_distribution(mkt)
        figure_market_param_stability(mkt)
        figure_best_worst(mkt)
    print(f"[ok] presentation figures written to {OUT.resolve()}")
    for p in sorted(OUT.glob("*.png")):
        print(" -", p.name)


if __name__ == "__main__":
    main()
