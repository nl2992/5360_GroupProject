from __future__ import annotations

import numpy as np
import pandas as pd

from .config import bars_per_year, get_market


def drawdown_family(equity: np.ndarray, alpha: float = 0.05) -> dict[str, float]:
    E = np.asarray(equity, dtype=float)
    if len(E) == 0:
        return {
            "MaxDD": 0.0,
            "AvgDD": 0.0,
            "CDD": 0.0,
            "Underwater": np.array([]),
            "DD_duration_bars": 0,
            "Recovery_bars": np.nan,
        }

    peak = np.maximum.accumulate(E)
    dd_mag = peak - E
    underwater = -dd_mag
    max_dd = float(dd_mag.max())
    avg_dd = float(dd_mag.mean())
    k = max(1, int(np.ceil(alpha * len(E))))
    cdd = float(np.sort(dd_mag)[-k:].mean())

    run = 0
    run_max = 0
    for value in dd_mag > 0:
        if value:
            run += 1
            run_max = max(run_max, run)
        else:
            run = 0

    trough = int(np.argmax(dd_mag))
    prior_peak = peak[trough]
    recover = np.where(E[trough:] >= prior_peak)[0]
    recovery = float(recover[0]) if len(recover) else np.nan

    return {
        "MaxDD": max_dd,
        "AvgDD": avg_dd,
        "CDD": cdd,
        "Underwater": underwater,
        "DD_duration_bars": int(run_max),
        "Recovery_bars": recovery,
    }


def performance_from_ledger(
    ledger: pd.DataFrame,
    equity: np.ndarray,
    ticker: str,
    alpha: float = 0.05,
    bar_minutes: int | None = None,
) -> dict[str, float]:
    spec = get_market(ticker)
    bpy = bars_per_year(ticker, bar_minutes=bar_minutes)
    E0 = spec.E0
    E = np.asarray(equity, dtype=float)
    if len(E) == 0:
        E = np.array([E0], dtype=float)

    if len(E) < 2:
        rets = np.array([0.0])
    else:
        safe = E[E > 0]
        rets = np.diff(safe) / safe[:-1] if len(safe) > 1 else np.array([0.0])

    avg_r = float(np.mean(rets))
    std_r = float(np.std(rets, ddof=1)) if len(rets) > 1 else 0.0
    ann_r = avg_r * bpy
    ann_v = std_r * np.sqrt(bpy)
    sharpe = ann_r / ann_v if ann_v > 0 else 0.0

    dd = drawdown_family(E, alpha=alpha)
    peak = np.maximum.accumulate(E)
    dd_mag = peak - E
    trough = int(np.argmax(dd_mag))
    max_dd_pct = float(dd_mag[trough] / peak[trough]) if peak[trough] > 0 else 0.0

    pnl = ledger["pnl"].to_numpy(dtype=float) if len(ledger) else np.array([])
    winners = pnl[pnl > 0]
    losers = pnl[pnl < 0]
    n_trades = int(len(pnl))
    gross_profit = float(winners.sum()) if len(winners) else 0.0
    gross_loss = float(-losers.sum()) if len(losers) else 0.0

    return {
        "Total Profit": float(E[-1] - E0),
        "Return %": float((E[-1] / E0 - 1.0) * 100),
        "Ann. Return %": ann_r * 100,
        "Ann. Volatility %": ann_v * 100,
        "Sharpe Ratio": sharpe,
        "Max Drawdown $": dd["MaxDD"],
        "Max Drawdown %": max_dd_pct * 100,
        "Avg Drawdown $": dd["AvgDD"],
        "CDD (α=0.05) $": dd["CDD"],
        "DD Duration (bars)": dd["DD_duration_bars"],
        "Recovery (bars)": dd["Recovery_bars"],
        "Return on Account": float((E[-1] - E0) / dd["MaxDD"]) if dd["MaxDD"] > 0 else 0.0,
        "Total Trades": n_trades,
        "Win Rate %": float((len(winners) / n_trades) * 100) if n_trades else 0.0,
        "Avg Winner $": float(winners.mean()) if len(winners) else 0.0,
        "Avg Loser $": float(losers.mean()) if len(losers) else 0.0,
        "Win/Loss Ratio": abs(float(winners.mean() / losers.mean())) if len(winners) and len(losers) else 0.0,
        "Profit Factor": float(gross_profit / gross_loss) if gross_loss > 0 else np.inf,
        "Gross Profit $": gross_profit,
        "Gross Loss $": gross_loss,
        "Avg Trade PnL $": float(pnl.mean()) if n_trades else 0.0,
        "Avg Duration (bars)": float(ledger["duration_bars"].mean()) if len(ledger) else 0.0,
    }


def summarise_performance_table(metrics: dict[str, float]) -> pd.DataFrame:
    return pd.DataFrame([metrics])


HEADLINE_METRIC_KEYS = [
    "Total Profit",
    "Return %",
    "Ann. Return %",
    "Ann. Volatility %",
    "Sharpe Ratio",
    "Max Drawdown $",
    "Max Drawdown %",
    "Avg Drawdown $",
    "CDD (α=0.05) $",
    "DD Duration (bars)",
    "Recovery (bars)",
    "Return on Account",
]

TRADE_METRIC_KEYS = [
    "Total Trades",
    "Win Rate %",
    "Avg Winner $",
    "Avg Loser $",
    "Win/Loss Ratio",
    "Profit Factor",
    "Gross Profit $",
    "Gross Loss $",
    "Avg Trade PnL $",
    "Avg Duration (bars)",
]


def split_metric_sections(metrics: dict[str, float]) -> dict[str, dict[str, float]]:
    headline = {key: metrics[key] for key in HEADLINE_METRIC_KEYS if key in metrics}
    trade = {key: metrics[key] for key in TRADE_METRIC_KEYS if key in metrics}
    residual = {
        key: value
        for key, value in metrics.items()
        if key not in headline and key not in trade
    }
    return {
        "headline": headline,
        "trade": trade,
        "residual": residual,
    }
