"""
Replicate (with Columbia theming) the five reference diagnostics charts the
team has been working with — and add equivalents for BTC and a percentage-
return trade distribution that the dollar-PnL histograms don't capture.

Outputs into report/presentation/figures/repl_*.png.

Charts produced:
  repl_ty_price_yield.png            TY price (top) + implied 10-yr yield (bottom)
  repl_ty_pr_grid.png                Push-Response grid τ ∈ {1..350} for TY
  repl_btc_pr_grid.png               Push-Response grid τ ∈ {1..1152} for BTC
  repl_ty_vr_curve.png               VR(q) for TY out to q ≈ 5 000 bars
  repl_btc_vr_curve.png              VR(q) for BTC out to q ≈ 5 000 bars
  repl_ty_vr_decade_windows.png      VR by 10-year backward windows (TY)
  repl_btc_vr_decade_windows.png     VR by 2-year backward windows (BTC)
  repl_ty_vr_lookback.png            VR for past 10/20/30/40-year lookbacks (TY)
  repl_ty_pct_returns.png            Per-trade % return distribution (TY)
  repl_btc_pct_returns.png           Per-trade % return distribution (BTC)
"""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter

# Columbia palette ------------------------------------------------------------
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
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "axes.grid": True,
            "grid.color": COL_LIGHT,
            "grid.linewidth": 0.6,
            "xtick.color": COL_CHARCOAL,
            "ytick.color": COL_CHARCOAL,
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "savefig.bbox": "tight",
            "savefig.dpi": 170,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "legend.frameon": False,
        }
    )


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
WF = ROOT / "results" / "walkforward"
OUT = ROOT / "report" / "presentation" / "figures"
OUT.mkdir(parents=True, exist_ok=True)


def _save(fig, name):
    out = OUT / name
    fig.savefig(out)
    plt.close(fig)
    return out


def _credit(ax, source="Source: Group 1 — TF Data 5-min OHLC"):
    ax.text(0.0, -0.18, source, transform=ax.transAxes, ha="left", va="top",
            fontsize=8, color=COL_GREY)


def _load_close(file_name: str, *, resample: str | None = None) -> pd.Series:
    df = pd.read_csv(DATA / file_name)
    df["DateTime"] = pd.to_datetime(df["Date"] + " " + df["Time"], format="%m/%d/%Y %H:%M")
    s = df.set_index("DateTime")["Close"].astype(float)
    if resample:
        s = s.resample(resample).last().dropna()
    return s


# ----------------------------------------------------------------------------
# 1. Implied 10-yr yield from TY futures price
# ----------------------------------------------------------------------------
def implied_yield(price: np.ndarray) -> np.ndarray:
    """Solve for yield-to-maturity y given price P of a 6% semi-annual,
    10-year bond. Returns yield in percent."""
    coupon = 3.0
    nper = 20
    par = 100.0
    # Newton iteration — vectorised
    y = np.full_like(price, 0.05)  # 5% start
    for _ in range(40):
        # f(y) = sum_{i=1..20} c/(1+y/2)^i + par/(1+y/2)^20 - P
        rate = 1 + y / 2
        # Sum of geometric series for coupons
        # Using closed form: c * (1 - rate^-n) / (y/2)
        # Avoid division by zero at y=0
        y_safe = np.where(np.abs(y) < 1e-9, 1e-9, y)
        rate_pow = rate ** -nper
        coupon_pv = coupon * (1.0 - rate_pow) / (y_safe / 2.0)
        principal_pv = par * rate_pow
        f = coupon_pv + principal_pv - price
        # df/dy via numerical derivative
        h = 1e-5
        rate_h = 1 + (y + h) / 2
        rate_pow_h = rate_h ** -nper
        f_h = coupon * (1.0 - rate_pow_h) / ((y + h) / 2.0) + par * rate_pow_h - price
        df = (f_h - f) / h
        df = np.where(np.abs(df) < 1e-12, 1e-12, df)
        y = y - f / df
        y = np.clip(y, -0.05, 1.0)
    return y * 100.0


def figure_ty_price_yield():
    s = _load_close("TY-5minHLV.csv", resample="D")
    y_pct = implied_yield(s.values)

    fig, axes = plt.subplots(2, 1, figsize=(11.5, 6.6), sharex=True)
    axes[0].plot(s.index, s.values, color=COL_NAVY, lw=1.0)
    axes[0].fill_between(s.index, s.values, s.min(), color=COL_BLUE, alpha=0.20)
    axes[0].set_title("TY 10-year Treasury futures — daily close",
                      color=COL_NAVY, fontsize=13, loc="left")
    axes[0].set_ylabel("TY price (points)")

    axes[1].plot(s.index, y_pct, color=COL_GOLD, lw=1.0)
    axes[1].fill_between(s.index, y_pct, 0, color=COL_GOLD, alpha=0.18)
    axes[1].set_title("Implied 10-year Treasury yield (from futures price, 6%-coupon model)",
                      color=COL_NAVY, fontsize=13, loc="left")
    axes[1].set_ylabel("Yield (%)")
    axes[1].set_xlabel("Year")
    axes[1].yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.1f}%"))

    fig.suptitle("TY price and implied yield, 1983–2026",
                 color=COL_NAVY, fontsize=14, fontweight="bold", y=0.99)
    _credit(axes[1])
    _save(fig, "repl_ty_price_yield.png")


# ----------------------------------------------------------------------------
# 2. Push-response grid (multi-τ)
# ----------------------------------------------------------------------------
def push_response(prices: np.ndarray, tau: int, n_bins: int = 25):
    """Compute the conditional mean response per push-bin."""
    diffs = prices[tau:] - prices[:-tau]
    push = diffs[:-tau]
    response = diffs[tau:]
    # Bin the pushes into n_bins equally-populated buckets via quantiles
    if push.size < n_bins * 5:
        return None, None
    edges = np.quantile(push, np.linspace(0, 1, n_bins + 1))
    edges[0] -= 1e-9
    edges[-1] += 1e-9
    centres = []
    means = []
    for i in range(n_bins):
        mask = (push > edges[i]) & (push <= edges[i + 1])
        if mask.sum() < 5:
            continue
        centres.append(push[mask].mean())
        means.append(response[mask].mean())
    return np.array(centres), np.array(means)


def figure_pr_grid(market: str):
    if market == "TY":
        prices = _load_close("TY-5minHLV.csv").values
        taus = [1, 6, 12, 24, 32, 48, 72, 96, 144, 192, 288, 350]
        title = "Push-Response Test for TY Futures: short to medium horizons"
        out = "repl_ty_pr_grid.png"
        color = COL_NAVY
    else:
        prices = _load_close("BTC-5minHLV.csv").values
        taus = [1, 12, 24, 48, 96, 144, 288, 432, 576, 864, 1152, 1440]
        title = "Push-Response Test for BTC Futures: short to medium horizons"
        out = "repl_btc_pr_grid.png"
        color = COL_GOLD

    fig, axes = plt.subplots(3, 4, figsize=(13.5, 8.0))
    for ax, tau in zip(axes.flat, taus):
        c, m = push_response(prices, tau)
        if c is None:
            ax.set_axis_off()
            continue
        ax.axhline(0, color=COL_BLUE, lw=0.7)
        ax.axvline(0, color=COL_BLUE, lw=0.7)
        ax.plot(c, m, color=color, lw=1.4)
        ax.set_title(f"τ = {tau}", color=COL_NAVY, fontsize=10)
        ax.set_xlabel("push", fontsize=8)
        ax.set_ylabel("avg response", fontsize=8)
        ax.tick_params(labelsize=7)
    fig.suptitle(title, color=COL_NAVY, fontsize=14, fontweight="bold", y=1.00)
    fig.tight_layout()
    _save(fig, out)


# ----------------------------------------------------------------------------
# 3. Variance ratio curves
# ----------------------------------------------------------------------------
def variance_ratio_curve(prices: np.ndarray, q_values: np.ndarray) -> np.ndarray:
    """Lo–MacKinlay VR(q) on price differences."""
    diffs = np.diff(prices)
    var1 = diffs.var(ddof=1)
    out = np.zeros(len(q_values))
    for i, q in enumerate(q_values):
        if q <= 1:
            out[i] = 1.0
            continue
        # Variance of q-bar differences
        d = prices[q:] - prices[:-q]
        out[i] = d.var(ddof=1) / (q * var1)
    return out


def figure_vr_curve(market: str):
    if market == "TY":
        prices = _load_close("TY-5minHLV.csv").values
        title = "Variance Ratio vs q — TY 5-min price differences"
        out = "repl_ty_vr_curve.png"
        color = COL_NAVY
    else:
        prices = _load_close("BTC-5minHLV.csv").values
        title = "Variance Ratio vs q — BTC 5-min price differences"
        out = "repl_btc_vr_curve.png"
        color = COL_GOLD

    qs = np.unique(np.concatenate([
        np.arange(1, 50, 1),
        np.arange(50, 500, 10),
        np.arange(500, 5001, 50),
    ])).astype(int)
    vr = variance_ratio_curve(prices, qs)

    fig, ax = plt.subplots(figsize=(11.5, 5.5))
    ax.axhline(1.0, color=COL_BLUE, lw=1.2, ls="--", label="Random walk benchmark")
    ax.plot(qs, vr, color=color, lw=1.6, marker="o", ms=2.5,
            markerfacecolor=color, markeredgecolor=color)
    ax.set_xlabel("q (aggregation horizon, 5-min bars)")
    ax.set_ylabel("Variance Ratio")
    ax.set_title(title, color=COL_NAVY, fontsize=14, loc="left")
    ax.legend(loc="upper left")
    _credit(ax)
    _save(fig, out)


# ----------------------------------------------------------------------------
# 4. VR by backward 10-year windows
# ----------------------------------------------------------------------------
def figure_vr_decade_windows(market: str):
    if market == "TY":
        s = _load_close("TY-5minHLV.csv")
        windows = [(2016, 2026), (2006, 2016), (1996, 2006), (1986, 1996)]
        out = "repl_ty_vr_decade_windows.png"
        title = "Variance Ratio by backward 10-year windows — TY 5-min"
        cmap = [COL_NAVY, COL_GOLD, COL_GREEN, COL_RED]
    else:
        s = _load_close("BTC-5minHLV.csv")
        windows = [(2024, 2026), (2022, 2024), (2020, 2022), (2018, 2020)]
        out = "repl_btc_vr_decade_windows.png"
        title = "Variance Ratio by backward 2-year windows — BTC 5-min"
        cmap = [COL_NAVY, COL_GOLD, COL_GREEN, COL_RED]

    qs = np.unique(np.concatenate([
        np.arange(1, 50, 1),
        np.arange(50, 500, 10),
        np.arange(500, 5001, 50),
    ])).astype(int)

    fig, ax = plt.subplots(figsize=(11.5, 5.5))
    ax.axhline(1.0, color=COL_BLUE, lw=1.2, ls="--", label="Benchmark")
    for (yr0, yr1), color in zip(windows, cmap):
        sub = s.loc[f"{yr0}-01-01":f"{yr1}-01-01"]
        if sub.empty:
            continue
        prices = sub.values
        vr = variance_ratio_curve(prices, qs)
        ax.plot(qs, vr, color=color, lw=1.6, label=f"{yr0}–{yr1}")
    ax.set_xlabel("q, aggregation horizon in 5-minute bars")
    ax.set_ylabel("Variance Ratio")
    ax.set_title(title, color=COL_NAVY, fontsize=14, loc="left")
    ax.legend(loc="lower right" if market == "TY" else "best")
    _credit(ax)
    _save(fig, out)


# ----------------------------------------------------------------------------
# 5. VR by past 10/20/30/40 year lookbacks (TY)
# ----------------------------------------------------------------------------
def figure_ty_vr_lookback():
    s = _load_close("TY-5minHLV.csv")
    end = s.index.max()
    lookbacks = [10, 20, 30, 40]
    qs = np.unique(np.concatenate([
        np.arange(1, 50, 1),
        np.arange(50, 500, 10),
        np.arange(500, 5001, 50),
    ])).astype(int)

    fig, ax = plt.subplots(figsize=(11.5, 5.5))
    ax.axhline(1.0, color=COL_BLUE, lw=1.2, ls="--", label="Random walk benchmark")
    cmap = [COL_NAVY, COL_GOLD, COL_GREEN, COL_RED]
    for years, color in zip(lookbacks, cmap):
        start = end - pd.Timedelta(days=int(years * 365.25))
        sub = s.loc[start:end]
        prices = sub.values
        vr = variance_ratio_curve(prices, qs)
        ax.plot(qs, vr, color=color, lw=1.6, label=f"Past {years} years")
    ax.set_xlabel("q, aggregation horizon in 5-minute bars")
    ax.set_ylabel("Variance Ratio")
    ax.set_title("Variance Ratio Test for TY Futures: past 10/20/30/40 years",
                 color=COL_NAVY, fontsize=14, loc="left")
    ax.legend(loc="best")
    _credit(ax)
    _save(fig, "repl_ty_vr_lookback.png")


# ----------------------------------------------------------------------------
# 6. % return per trade — distribution
# ----------------------------------------------------------------------------
def figure_pct_returns(market: str):
    if market == "TY":
        ledger = pd.read_csv(WF / "TY_5m" / "TY_5m_walkforward_ledger.csv")
        title = "TY (10-yr Treasury futures) — out-of-sample trade % return distribution"
        out = "repl_ty_pct_returns.png"
        color = COL_NAVY
    else:
        ledger = pd.read_csv(WF / "BTC_5m" / "BTC_5m_walkforward_ledger.csv")
        title = "BTC (CME Bitcoin futures) — out-of-sample trade % return distribution"
        out = "repl_btc_pct_returns.png"
        color = COL_GOLD

    # Two complementary % views
    direction = ledger["direction"].astype(int)
    entry = ledger["entry_price"].astype(float)
    exit_ = ledger["exit_price"].astype(float)
    # 1) Price-move % per trade — the underlying's directional move captured
    pct_price = (exit_ - entry) / entry * 100.0 * direction
    # 2) Equity-return % per trade — pnl as % of $100k starting capital
    pct_equity = ledger["pnl"].astype(float) / 100_000 * 100.0

    fig, axes = plt.subplots(1, 2, figsize=(13.0, 5.0))

    for ax, vals, label in [
        (axes[0], pct_price, "Price-move % per trade  (= (exit/entry − 1) × direction × 100%)"),
        (axes[1], pct_equity, "Equity-return % per trade  (= PnL / $100 000 × 100%)"),
    ]:
        wins = vals[vals > 0]
        loss = vals[vals <= 0]
        ax.hist(loss, bins=40, color=COL_RED, alpha=0.65, label=f"Losers (n={len(loss):,d})")
        ax.hist(wins, bins=40, color=COL_GREEN, alpha=0.80, label=f"Winners (n={len(wins):,d})")
        ax.axvline(0, color=COL_INK, lw=0.8)
        ax.axvline(vals.mean(), color=COL_NAVY, lw=1.4, ls="--",
                   label=f"Mean = {vals.mean():+.2f}%")
        ax.set_xlabel(label)
        ax.set_ylabel("Trade count")
        ax.legend(loc="upper right", fontsize=9)
        # Stats box
        med = float(np.median(vals))
        p99 = float(np.quantile(vals, 0.99))
        p01 = float(np.quantile(vals, 0.01))
        stats = (
            f"Mean: {vals.mean():+.2f}%   |   Median: {med:+.2f}%\n"
            f"Best: {vals.max():+.2f}%   |   Worst: {vals.min():+.2f}%\n"
            f"P99: {p99:+.2f}%   |   P01: {p01:+.2f}%"
        )
        ax.text(0.01, 0.97, stats, transform=ax.transAxes, va="top", ha="left",
                fontsize=9, family="DejaVu Sans Mono",
                bbox=dict(boxstyle="round", fc=COL_CREAM, ec=COL_INK, lw=0.5))

    fig.suptitle(title, color=COL_NAVY, fontsize=14, fontweight="bold", y=1.02)
    _credit(axes[1])
    _save(fig, out)


# ----------------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------------
def main() -> None:
    apply_theme()
    figure_ty_price_yield()
    figure_pr_grid("TY")
    figure_pr_grid("BTC")
    figure_vr_curve("TY")
    figure_vr_curve("BTC")
    figure_vr_decade_windows("TY")
    figure_vr_decade_windows("BTC")
    figure_ty_vr_lookback()
    figure_pct_returns("TY")
    figure_pct_returns("BTC")
    print(f"[ok] replica figures written to {OUT.resolve()}")
    for p in sorted(OUT.glob("repl_*.png")):
        print(" -", p.name)


if __name__ == "__main__":
    main()
