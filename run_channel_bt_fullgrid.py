#!/usr/bin/env python3
import argparse
import csv
import math
from pathlib import Path
import numpy as np


def read_ohlc(path):
    with open(path, "r", newline="") as f:
        r = csv.DictReader(f)
        lower = {x.lower(): x for x in (r.fieldnames or [])}

        def col(*xs):
            for x in xs:
                if x.lower() in lower:
                    return lower[x.lower()]
            raise ValueError

        c_open = col("open")
        c_high = col("high")
        c_low = col("low")
        c_close = col("close")

        o, h, l, c = [], [], [], []
        for row in r:
            try:
                oo = float(row[c_open])
                hh = float(row[c_high])
                ll = float(row[c_low])
                cc = float(row[c_close])
            except:
                continue
            if oo > 0 and hh > 0 and ll > 0 and cc > 0:
                o.append(oo); h.append(hh); l.append(ll); c.append(cc)

    return np.array(o), np.array(h), np.array(l), np.array(c)


def max_dd(eq):
    peak = eq[0]
    dd = 0
    for x in eq:
        if x > peak: peak = x
        d = peak - x
        if d > dd: dd = d
    return dd


def backtest(close, high, low, chn, stp, pv, slp):
    pos = 0
    entry = 0
    peak = 0
    trough = 0
    cash = 0
    eq = []
    trades = []

    for i in range(chn, len(close)):
        px = close[i]
        up = np.max(high[i-chn:i])
        lo = np.min(low[i-chn:i])

        if pos == 0:
            if px > up:
                pos = 1; entry = px; peak = px; cash -= slp/2
            elif px < lo:
                pos = -1; entry = px; trough = px; cash -= slp/2

        elif pos == 1:
            if px > peak: peak = px
            if px < peak*(1-stp) or px < lo:
                pnl = (px-entry)*pv - slp
                cash += pnl
                trades.append(pnl)
                pos = 0

        elif pos == -1:
            if px < trough: trough = px
            if px > trough*(1+stp) or px > up:
                pnl = (entry-px)*pv - slp
                cash += pnl
                trades.append(pnl)
                pos = 0

        mtm = cash
        if pos == 1: mtm += (px-entry)*pv
        if pos == -1: mtm += (entry-px)*pv
        eq.append(mtm)

    return np.array(eq), trades


def perf(eq, trades):
    ret = np.diff(eq)
    net = eq[-1] - eq[0]
    dd = max_dd(eq)
    std = np.std(ret, ddof=1)
    avg = np.mean(ret)
    sharpe = avg/std*np.sqrt(252*78) if std>0 else 0
    wins = [x for x in trades if x>0]
    losses = [x for x in trades if x<0]

    return [
        net,
        dd,
        net/dd if dd>0 else 0,
        sharpe,
        len(trades),
        len(wins)/len(trades) if trades else 0,
        np.mean(wins) if wins else 0,
        np.mean(losses) if losses else 0,
        sum(wins)/abs(sum(losses)) if losses else 0
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    args = ap.parse_args()

    o,h,l,c = read_ohlc(args.input)

    bars_per_year = 78*252
    is_len = 4*bars_per_year
    oos_len = 3*21*78

    chn_vals = range(500,10001,10)
    stp_vals = np.arange(0.005,0.1001,0.001)

    all_eq = []
    all_trades = []

    start = 0
    while start+is_len+oos_len <= len(c):
        best = None

        for chn in chn_vals:
            for stp in stp_vals:
                eq,tr = backtest(c[start:start+is_len],h[start:start+is_len],l[start:start+is_len],chn,stp,1000,0)
                p = perf(eq,tr)
                score = p[2]
                if best is None or score > best[0]:
                    best = (score, chn, stp)

        chn, stp = best[1], best[2]
        eq,tr = backtest(c[start+is_len:start+is_len+oos_len],
                         h[start+is_len:start+is_len+oos_len],
                         l[start+is_len:start+is_len+oos_len],
                         chn, stp,1000,0)

        if all_eq: eq = eq + all_eq[-1]
        all_eq.extend(eq)
        all_trades.extend(tr)

        start += oos_len

    final = perf(np.array(all_eq), all_trades)

    out = Path("outputs/ty_backtest_final")
    out.mkdir(parents=True, exist_ok=True)

    with open(out/"performance_summary.csv","w",newline="") as f:
        w=csv.writer(f)
        w.writerow(["net","dd","ret/dd","sharpe","trades","winrate","avgwin","avgloss","pf"])
        w.writerow(final)


if __name__ == "__main__":
    main()