#!/usr/bin/env python3

import argparse
import csv
import math
from pathlib import Path

import numpy as np


def read_ohlc(path):
    with open(path, "r", newline="") as f:
        r = csv.DictReader(f)
        names = r.fieldnames or []
        lower = {x.lower(): x for x in names}

        def col(*xs):
            for x in xs:
                if x.lower() in lower:
                    return lower[x.lower()]
            raise ValueError(f"Missing column: {xs}")

        c_date = lower.get("date") or lower.get("datetime") or lower.get("timestamp") or lower.get("time")
        c_open = col("Open")
        c_high = col("High")
        c_low = col("Low")
        c_close = col("Close")

        dates, o, h, l, c = [], [], [], [], []
        for row in r:
            try:
                oo = float(row[c_open])
                hh = float(row[c_high])
                ll = float(row[c_low])
                cc = float(row[c_close])
            except Exception:
                continue
            if oo > 0 and hh > 0 and ll > 0 and cc > 0:
                dates.append(row[c_date] if c_date else str(len(c)))
                o.append(oo)
                h.append(hh)
                l.append(ll)
                c.append(cc)

    return dates, np.array(o), np.array(h), np.array(l), np.array(c)


def max_drawdown(eq):
    if len(eq) == 0:
        return 0.0
    peak = eq[0]
    dd = 0.0
    for x in eq:
        if x > peak:
            peak = x
        d = peak - x
        if d > dd:
            dd = d
    return dd


def channel_backtest(close, high, low, chn_len, stp_pct, point_value=1000.0, slippage=0.0, start_pos=0):
    n = len(close)
    pos = start_pos
    entry = 0.0
    peak = 0.0
    trough = 0.0
    cash = 0.0
    equity = []
    trades = []

    for i in range(chn_len, n):
        prev = close[i - 1]
        px = close[i]
        upper = np.max(high[i - chn_len:i])
        lower = np.min(low[i - chn_len:i])

        if pos == 0:
            if px > upper:
                pos = 1
                entry = px
                peak = px
                cash -= slippage / 2
            elif px < lower:
                pos = -1
                entry = px
                trough = px
                cash -= slippage / 2

        elif pos == 1:
            if px > peak:
                peak = px
            stop = peak * (1.0 - stp_pct)
            if px < stop or px < lower:
                pnl = (px - entry) * point_value - slippage
                cash += (px - entry) * point_value - slippage / 2
                trades.append([i, "LONG", entry, px, pnl])
                pos = 0
                entry = 0.0

        elif pos == -1:
            if px < trough:
                trough = px
            stop = trough * (1.0 + stp_pct)
            if px > stop or px > upper:
                pnl = (entry - px) * point_value - slippage
                cash += (entry - px) * point_value - slippage / 2
                trades.append([i, "SHORT", entry, px, pnl])
                pos = 0
                entry = 0.0

        mtm = cash
        if pos == 1:
            mtm += (px - entry) * point_value
        elif pos == -1:
            mtm += (entry - px) * point_value
        equity.append(mtm)

    return np.array(equity), trades, pos


def perf(equity, trades):
    if len(equity) < 2:
        return {}
    ret = np.diff(equity)
    net = equity[-1] - equity[0]
    dd = max_drawdown(equity)
    std = float(np.std(ret, ddof=1)) if len(ret) > 1 else 0.0
    avg = float(np.mean(ret)) if len(ret) else 0.0
    sharpe = avg / std * math.sqrt(252 * 78) if std > 0 else 0.0
    pnls = np.array([x[4] for x in trades], dtype=float) if trades else np.array([])
    wins = pnls[pnls > 0]
    losses = pnls[pnls < 0]
    return {
        "net_profit": net,
        "max_drawdown": dd,
        "return_on_account": net / dd if dd > 0 else 0.0,
        "sharpe": sharpe,
        "num_trades": len(trades),
        "win_rate": len(wins) / len(pnls) if len(pnls) else 0.0,
        "avg_winner": float(np.mean(wins)) if len(wins) else 0.0,
        "avg_loser": float(np.mean(losses)) if len(losses) else 0.0,
        "profit_factor": float(np.sum(wins) / abs(np.sum(losses))) if len(losses) and abs(np.sum(losses)) > 0 else 0.0,
    }


def optimize(close, high, low, chn_values, stp_values, point_value, slippage):
    best = None
    for chn in chn_values:
        if chn >= len(close) // 2:
            continue
        for stp in stp_values:
            eq, tr, _ = channel_backtest(close, high, low, chn, stp, point_value, slippage)
            p = perf(eq, tr)
            score = p.get("return_on_account", -1e18)
            if best is None or score > best["score"]:
                best = {"chn_len": chn, "stp_pct": stp, "score": score, **p}
    return best


def write_csv(path, rows, header):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output-dir", default="outputs/ty_backtest_v1")
    ap.add_argument("--point-value", type=float, default=1000.0)
    ap.add_argument("--slippage", type=float, default=0.0)
    ap.add_argument("--bars-per-day", type=int, default=78)
    ap.add_argument("--is-years", type=int, default=4)
    ap.add_argument("--oos-months", type=int, default=3)
    ap.add_argument("--fast", action="store_true")
    args = ap.parse_args()

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    dates, o, h, l, c = read_ohlc(args.input)

    bars_per_year = args.bars_per_day * 126
    is_len = 2 * bars_per_year
    oos_len = 1 * 21 * args.bars_per_day

    if args.fast:
        chn_values = [500, 1000, 1500]
        stp_values = [0.01, 0.02]
    else:
        chn_values = range(500, 10001, 10)
        stp_values = np.arange(0.005, 0.1001, 0.001)

    param_rows = []
    equity_rows = []
    trade_rows = []
    all_equity = []
    offset = 0

    k = 0
    start = 0
    while start + is_len + oos_len <= len(c):
        is_slice = slice(start, start + is_len)
        oos_slice = slice(start + is_len, start + is_len + oos_len)

        best = optimize(c[is_slice], h[is_slice], l[is_slice], chn_values, stp_values, args.point_value, args.slippage)

        eq, trades, _ = channel_backtest(
            c[oos_slice],
            h[oos_slice],
            l[oos_slice],
            int(best["chn_len"]),
            float(best["stp_pct"]),
            args.point_value,
            args.slippage,
        )

        if len(all_equity):
            eq = eq + all_equity[-1]

        for j, x in enumerate(eq):
            idx = start + is_len + j
            equity_rows.append([dates[idx], k, x])
            all_equity.append(x)

        for tr in trades:
            idx = start + is_len + tr[0]
            trade_rows.append([dates[idx], k, tr[1], tr[2], tr[3], tr[4]])

        param_rows.append([
            k,
            dates[start],
            dates[start + is_len - 1],
            dates[start + is_len],
            dates[start + is_len + oos_len - 1],
            best["chn_len"],
            best["stp_pct"],
            best["score"],
            best["net_profit"],
            best["max_drawdown"],
            best["num_trades"],
        ])

        k += 1
        start += oos_len

    final_perf = perf(np.array(all_equity), [[None, None, None, None, x[-1]] for x in trade_rows])

    write_csv(out / "quarterly_best_params.csv", param_rows, [
        "window", "is_start", "is_end", "oos_start", "oos_end",
        "chn_len", "stp_pct", "is_score", "is_net_profit", "is_max_drawdown", "is_num_trades"
    ])

    write_csv(out / "oos_equity.csv", equity_rows, ["datetime", "window", "equity"])

    write_csv(out / "oos_trades.csv", trade_rows, [
        "exit_datetime", "window", "side", "entry_price", "exit_price", "pnl"
    ])

    write_csv(out / "performance_summary.csv", [[k, v] for k, v in final_perf.items()], ["metric", "value"])

    print(f"Completed. Outputs written to: {out}")


if __name__ == "__main__":
    main()