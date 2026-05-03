from __future__ import annotations

from itertools import product

import numpy as np
import pandas as pd
from numba import jit

from .config import get_market, infer_bar_minutes_from_index, resolve_round_turn_cost


LEDGER_COLUMNS = [
    "entry_bar",
    "exit_bar",
    "entry_time",
    "exit_time",
    "direction",
    "entry_price",
    "exit_price",
    "duration_bars",
    "pnl",
    "slippage",
    "is_oos",
]


def _empty_ledger() -> pd.DataFrame:
    return pd.DataFrame(columns=LEDGER_COLUMNS)


@jit(nopython=True, cache=True)
def _channel_core(
    Open,
    High,
    Low,
    Close,
    L,
    S,
    slpg,
    PV,
    E0,
    barsBack,
    eval_start,
    rebase_at_eval_start,
):
    N = len(Close)
    E = np.zeros(N) + E0
    DD = np.zeros(N)
    position_arr = np.zeros(N, dtype=np.int64)
    trade_weights = np.zeros(N)

    HH = np.zeros(N)
    LL = np.zeros(N)
    for k in range(L, N):
        HH[k] = np.max(High[k - L : k])
        LL[k] = np.min(Low[k - L : k])

    t_entry_bar = np.full(N, -1, dtype=np.int64)
    t_exit_bar = np.full(N, -1, dtype=np.int64)
    t_dir = np.zeros(N, dtype=np.int64)
    t_entry_px = np.zeros(N)
    t_exit_px = np.zeros(N)
    t_pnl = np.zeros(N)
    t_slpg = np.zeros(N)
    t_is_oos = np.zeros(N, dtype=np.int64)
    n_closed = 0

    open_entry_bar = -1
    open_entry_px = 0.0
    open_dir = 0
    position = 0
    benchmarkLong = 0.0
    benchmarkShort = 0.0
    Emax = E0

    start_k = max(L, barsBack)
    for k in range(start_k, N):
        traded = False
        delta = PV * (Close[k] - Close[k - 1]) * position

        if position == 0:
            buy = High[k] >= HH[k]
            sell = Low[k] <= LL[k]

            if buy and sell:
                delta = -slpg + PV * (LL[k] - HH[k])
                trade_weights[k] = 1.0
                t_entry_bar[n_closed] = k
                t_exit_bar[n_closed] = k
                t_dir[n_closed] = 1
                t_entry_px[n_closed] = HH[k]
                t_exit_px[n_closed] = LL[k]
                t_pnl[n_closed] = PV * (LL[k] - HH[k]) - slpg
                t_slpg[n_closed] = slpg
                t_is_oos[n_closed] = 1 if k >= eval_start else 0
                n_closed += 1
            else:
                if buy:
                    delta = -slpg / 2.0 + PV * (Close[k] - HH[k])
                    position = 1
                    traded = True
                    benchmarkLong = High[k]
                    trade_weights[k] = 0.5
                    open_entry_bar = k
                    open_entry_px = HH[k]
                    open_dir = 1
                if sell:
                    delta = -slpg / 2.0 - PV * (Close[k] - LL[k])
                    position = -1
                    traded = True
                    benchmarkShort = Low[k]
                    trade_weights[k] = 0.5
                    open_entry_bar = k
                    open_entry_px = LL[k]
                    open_dir = -1

        elif position == 1 and not traded:
            sellShort = Low[k] <= LL[k]
            sell = Low[k] <= benchmarkLong * (1.0 - S)

            if sellShort and sell:
                delta = delta - slpg - 2.0 * PV * (Close[k] - LL[k])
                trade_weights[k] = 1.0
                t_entry_bar[n_closed] = open_entry_bar
                t_exit_bar[n_closed] = k
                t_dir[n_closed] = open_dir
                t_entry_px[n_closed] = open_entry_px
                t_exit_px[n_closed] = LL[k]
                t_pnl[n_closed] = PV * (LL[k] - open_entry_px) * open_dir - slpg
                t_slpg[n_closed] = slpg
                t_is_oos[n_closed] = 1 if k >= eval_start else 0
                n_closed += 1

                position = -1
                benchmarkShort = Low[k]
                open_entry_bar = k
                open_entry_px = LL[k]
                open_dir = -1
            else:
                if sell:
                    exit_px = benchmarkLong * (1.0 - S)
                    delta = delta - slpg / 2.0 - PV * (Close[k] - exit_px)
                    trade_weights[k] = 0.5
                    t_entry_bar[n_closed] = open_entry_bar
                    t_exit_bar[n_closed] = k
                    t_dir[n_closed] = open_dir
                    t_entry_px[n_closed] = open_entry_px
                    t_exit_px[n_closed] = exit_px
                    t_pnl[n_closed] = PV * (exit_px - open_entry_px) * open_dir - slpg
                    t_slpg[n_closed] = slpg
                    t_is_oos[n_closed] = 1 if k >= eval_start else 0
                    n_closed += 1

                    position = 0
                    open_entry_bar = -1
                    open_entry_px = 0.0
                    open_dir = 0

                if sellShort:
                    delta = delta - slpg - 2.0 * PV * (Close[k] - LL[k])
                    trade_weights[k] = 1.0
                    t_entry_bar[n_closed] = open_entry_bar
                    t_exit_bar[n_closed] = k
                    t_dir[n_closed] = open_dir
                    t_entry_px[n_closed] = open_entry_px
                    t_exit_px[n_closed] = LL[k]
                    t_pnl[n_closed] = PV * (LL[k] - open_entry_px) * open_dir - slpg
                    t_slpg[n_closed] = slpg
                    t_is_oos[n_closed] = 1 if k >= eval_start else 0
                    n_closed += 1

                    position = -1
                    benchmarkShort = Low[k]
                    open_entry_bar = k
                    open_entry_px = LL[k]
                    open_dir = -1

            benchmarkLong = max(High[k], benchmarkLong)

        elif position == -1 and not traded:
            buyLong = High[k] >= HH[k]
            buy = High[k] >= benchmarkShort * (1.0 + S)

            if buyLong and buy:
                delta = delta - slpg + 2.0 * PV * (Close[k] - HH[k])
                trade_weights[k] = 1.0
                t_entry_bar[n_closed] = open_entry_bar
                t_exit_bar[n_closed] = k
                t_dir[n_closed] = open_dir
                t_entry_px[n_closed] = open_entry_px
                t_exit_px[n_closed] = HH[k]
                t_pnl[n_closed] = PV * (HH[k] - open_entry_px) * open_dir - slpg
                t_slpg[n_closed] = slpg
                t_is_oos[n_closed] = 1 if k >= eval_start else 0
                n_closed += 1

                position = 1
                benchmarkLong = High[k]
                open_entry_bar = k
                open_entry_px = HH[k]
                open_dir = 1
            else:
                if buy:
                    exit_px = benchmarkShort * (1.0 + S)
                    delta = delta - slpg / 2.0 + PV * (Close[k] - exit_px)
                    trade_weights[k] = 0.5
                    t_entry_bar[n_closed] = open_entry_bar
                    t_exit_bar[n_closed] = k
                    t_dir[n_closed] = open_dir
                    t_entry_px[n_closed] = open_entry_px
                    t_exit_px[n_closed] = exit_px
                    t_pnl[n_closed] = PV * (exit_px - open_entry_px) * open_dir - slpg
                    t_slpg[n_closed] = slpg
                    t_is_oos[n_closed] = 1 if k >= eval_start else 0
                    n_closed += 1

                    position = 0
                    open_entry_bar = -1
                    open_entry_px = 0.0
                    open_dir = 0

                if buyLong:
                    delta = delta - slpg + 2.0 * PV * (Close[k] - HH[k])
                    trade_weights[k] = 1.0
                    t_entry_bar[n_closed] = open_entry_bar
                    t_exit_bar[n_closed] = k
                    t_dir[n_closed] = open_dir
                    t_entry_px[n_closed] = open_entry_px
                    t_exit_px[n_closed] = HH[k]
                    t_pnl[n_closed] = PV * (HH[k] - open_entry_px) * open_dir - slpg
                    t_slpg[n_closed] = slpg
                    t_is_oos[n_closed] = 1 if k >= eval_start else 0
                    n_closed += 1

                    position = 1
                    benchmarkLong = High[k]
                    open_entry_bar = k
                    open_entry_px = HH[k]
                    open_dir = 1

            benchmarkShort = min(Low[k], benchmarkShort)

        E[k] = E[k - 1] + delta
        Emax = max(Emax, E[k])
        DD[k] = E[k] - Emax
        position_arr[k] = position

    if rebase_at_eval_start and eval_start > 0:
        base = E[eval_start - 1]
        offset = base - E0
        for k in range(N):
            if k < eval_start:
                E[k] = E0
                DD[k] = 0.0
            else:
                E[k] = E[k] - offset

        Emax2 = E0
        for k in range(eval_start, N):
            Emax2 = max(Emax2, E[k])
            DD[k] = E[k] - Emax2

    return (
        E,
        DD,
        position_arr,
        t_entry_bar[:n_closed],
        t_exit_bar[:n_closed],
        t_dir[:n_closed],
        t_entry_px[:n_closed],
        t_exit_px[:n_closed],
        t_pnl[:n_closed],
        t_slpg[:n_closed],
        t_is_oos[:n_closed],
        trade_weights,
        n_closed,
    )


@jit(nopython=True, cache=True)
def _mr_core(
    Open,
    High,
    Low,
    Close,
    N1,
    N2,
    VolLen,
    MALen,
    StpPct,
    slpg,
    PV,
    E0,
    barsBack,
    eval_start,
):
    N = len(Close)
    E = np.zeros(N) + E0
    DD = np.zeros(N)
    position_arr = np.zeros(N, dtype=np.int64)

    rets = np.zeros(N)
    for i in range(1, N):
        if Close[i - 1] != 0:
            rets[i] = (Close[i] - Close[i - 1]) / Close[i - 1]

    max_closed = 2 * N
    t_entry_bar = np.full(max_closed, -1, dtype=np.int64)
    t_exit_bar = np.full(max_closed, -1, dtype=np.int64)
    t_dir = np.zeros(max_closed, dtype=np.int64)
    t_entry_px = np.zeros(max_closed)
    t_exit_px = np.zeros(max_closed)
    t_pnl = np.zeros(max_closed)
    t_slpg = np.zeros(max_closed)
    t_is_oos = np.zeros(max_closed, dtype=np.int64)
    n_closed = 0

    open_entry_bar = np.full(2, -1, dtype=np.int64)
    open_entry_px = np.zeros(2)
    open_dir = np.zeros(2, dtype=np.int64)
    open_count = 0

    position = 0
    can_trade = True
    prev_ma = 0.0
    Emax = E0
    one_way = slpg / 2.0

    start_k = barsBack
    if MALen > start_k:
        start_k = MALen
    if VolLen + 1 > start_k:
        start_k = VolLen + 1
    if start_k < 2:
        start_k = 2

    for k in range(start_k, N):
        ma_sum = 0.0
        for i in range(k - MALen, k):
            ma_sum += Close[i]
        ma = ma_sum / MALen

        mean_r = 0.0
        for i in range(k - VolLen, k):
            mean_r += rets[i]
        mean_r = mean_r / VolLen

        var_r = 0.0
        for i in range(k - VolLen, k):
            diff = rets[i] - mean_r
            var_r += diff * diff
        vol = np.sqrt(var_r / VolLen)

        slpg_pct = 0.0
        if ma > 0:
            slpg_pct = slpg / (PV * ma)
        bnd1 = N1 * vol + 0.5 * slpg_pct
        bnd2 = bnd1 + N2 * vol

        if not can_trade and k > start_k:
            if (
                (Close[k - 1] < prev_ma and High[k] >= ma)
                or (Close[k - 1] > prev_ma and Low[k] <= ma)
                or (High[k] >= ma and Low[k] <= ma)
            ):
                can_trade = True

        delta = PV * (Close[k] - Close[k - 1]) * position
        stopped_this_bar = False

        if position != 0 and open_count > 0:
            avg_entry = 0.0
            for i in range(open_count):
                avg_entry += open_entry_px[i]
            avg_entry = avg_entry / open_count

            if position > 0:
                stop_px = avg_entry * (1.0 - StpPct)
                ma_hit = High[k] >= ma
                stop_hit = Low[k] <= stop_px
                if stop_hit or ma_hit:
                    exit_px = stop_px if stop_hit else ma
                    dq = -position
                    delta += PV * (Close[k] - exit_px) * dq - one_way * abs(dq)
                    for i in range(open_count):
                        t_entry_bar[n_closed] = open_entry_bar[i]
                        t_exit_bar[n_closed] = k
                        t_dir[n_closed] = open_dir[i]
                        t_entry_px[n_closed] = open_entry_px[i]
                        t_exit_px[n_closed] = exit_px
                        t_pnl[n_closed] = PV * (exit_px - open_entry_px[i]) * open_dir[i] - slpg
                        t_slpg[n_closed] = slpg
                        t_is_oos[n_closed] = 1 if k >= eval_start else 0
                        n_closed += 1
                    position = 0
                    open_count = 0
                    if stop_hit:
                        can_trade = False
                        stopped_this_bar = True

            else:
                stop_px = avg_entry * (1.0 + StpPct)
                ma_hit = Low[k] <= ma
                stop_hit = High[k] >= stop_px
                if stop_hit or ma_hit:
                    exit_px = stop_px if stop_hit else ma
                    dq = -position
                    delta += PV * (Close[k] - exit_px) * dq - one_way * abs(dq)
                    for i in range(open_count):
                        t_entry_bar[n_closed] = open_entry_bar[i]
                        t_exit_bar[n_closed] = k
                        t_dir[n_closed] = open_dir[i]
                        t_entry_px[n_closed] = open_entry_px[i]
                        t_exit_px[n_closed] = exit_px
                        t_pnl[n_closed] = PV * (exit_px - open_entry_px[i]) * open_dir[i] - slpg
                        t_slpg[n_closed] = slpg
                        t_is_oos[n_closed] = 1 if k >= eval_start else 0
                        n_closed += 1
                    position = 0
                    open_count = 0
                    if stop_hit:
                        can_trade = False
                        stopped_this_bar = True

        if can_trade and not stopped_this_bar:
            if position == 0:
                buy_px = ma * (1.0 - bnd1)
                sell_px = ma * (1.0 + bnd1)
                buy_hit = Low[k] <= buy_px
                sell_hit = High[k] >= sell_px
                if not (buy_hit and sell_hit):
                    if buy_hit:
                        delta += PV * (Close[k] - buy_px) - one_way
                        position = 1
                        open_entry_bar[0] = k
                        open_entry_px[0] = buy_px
                        open_dir[0] = 1
                        open_count = 1
                    elif sell_hit:
                        delta += PV * (Close[k] - sell_px) * (-1) - one_way
                        position = -1
                        open_entry_bar[0] = k
                        open_entry_px[0] = sell_px
                        open_dir[0] = -1
                        open_count = 1

            elif position == 1 and open_count == 1:
                add_px = ma * (1.0 - bnd2)
                if Low[k] <= add_px:
                    delta += PV * (Close[k] - add_px) - one_way
                    position = 2
                    open_entry_bar[1] = k
                    open_entry_px[1] = add_px
                    open_dir[1] = 1
                    open_count = 2

            elif position == -1 and open_count == 1:
                add_px = ma * (1.0 + bnd2)
                if High[k] >= add_px:
                    delta += PV * (Close[k] - add_px) * (-1) - one_way
                    position = -2
                    open_entry_bar[1] = k
                    open_entry_px[1] = add_px
                    open_dir[1] = -1
                    open_count = 2

        E[k] = E[k - 1] + delta
        Emax = max(Emax, E[k])
        DD[k] = E[k] - Emax
        position_arr[k] = position
        prev_ma = ma

    if eval_start > 0:
        base = E[eval_start - 1]
        offset = base - E0
        for k in range(N):
            if k < eval_start:
                E[k] = E0
                DD[k] = 0.0
            else:
                E[k] = E[k] - offset

        Emax2 = E0
        for k in range(eval_start, N):
            Emax2 = max(Emax2, E[k])
            DD[k] = E[k] - Emax2

    return (
        E,
        DD,
        position_arr,
        t_entry_bar[:n_closed],
        t_exit_bar[:n_closed],
        t_dir[:n_closed],
        t_entry_px[:n_closed],
        t_exit_px[:n_closed],
        t_pnl[:n_closed],
        t_slpg[:n_closed],
        t_is_oos[:n_closed],
        n_closed,
    )


def _build_ledger(
    df: pd.DataFrame,
    slice_start: int,
    entry_bar: np.ndarray,
    exit_bar: np.ndarray,
    direction: np.ndarray,
    entry_price: np.ndarray,
    exit_price: np.ndarray,
    pnl: np.ndarray,
    slippage: np.ndarray,
    is_oos: np.ndarray,
) -> pd.DataFrame:
    if len(entry_bar) == 0:
        return _empty_ledger()
    n = len(df)
    g_entry = entry_bar + slice_start
    g_exit = exit_bar + slice_start
    ledger = pd.DataFrame(
        {
            "entry_bar": g_entry,
            "exit_bar": g_exit,
            "entry_time": df.index[np.clip(g_entry, 0, n - 1)],
            "exit_time": df.index[np.clip(g_exit, 0, n - 1)],
            "direction": direction,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "duration_bars": (exit_bar - entry_bar).astype(int),
            "pnl": pnl,
            "slippage": slippage,
            "is_oos": is_oos.astype(bool),
        }
    )
    return ledger


def _post_process_result(
    family: str,
    params: dict[str, float | int],
    df: pd.DataFrame,
    slice_start: int,
    eval_start: int,
    eval_end: int,
    warmup_bars: int,
    round_turn_cost: float,
    output: tuple,
) -> dict[str, object]:
    if len(output) == 13:
        (
            equity,
            drawdown,
            position,
            entry_bar,
            exit_bar,
            direction,
            entry_price,
            exit_price,
            pnl,
            slippage,
            is_oos,
            trade_weights,
            n_closed,
        ) = output
    else:
        (
            equity,
            drawdown,
            position,
            entry_bar,
            exit_bar,
            direction,
            entry_price,
            exit_price,
            pnl,
            slippage,
            is_oos,
            n_closed,
        ) = output
        trade_weights = np.zeros_like(equity, dtype=float)
    ledger = _build_ledger(
        df,
        slice_start,
        entry_bar,
        exit_bar,
        direction,
        entry_price,
        exit_price,
        pnl,
        slippage,
        is_oos,
    )
    profit = float(equity[-1] - equity[0])
    max_dd = float(abs(drawdown.min()))
    objective = profit / max_dd if max_dd > 0 else 0.0
    oos_ledger = ledger[ledger["is_oos"]] if len(ledger) else ledger
    bar_pnl = np.zeros_like(equity, dtype=float)
    if len(equity) > 1:
        bar_pnl[1:] = np.diff(equity)
    return {
        "error": False,
        "family": family,
        "params": params,
        "Profit": profit,
        "MaxDD": max_dd,
        "Objective": objective,
        "NumTrades": int(len(oos_ledger)),
        "NumTradesAll": int(n_closed),
        "Equity": equity,
        "Drawdown": drawdown,
        "Position": position,
        "BarPnL": bar_pnl,
        "TradeWeights": trade_weights,
        "SliceStart": int(slice_start),
        "EvalStart": int(eval_start),
        "EvalEnd": int(eval_end),
        "WarmupBars": int(warmup_bars),
        "BarMinutes": int(infer_bar_minutes_from_index(df.index)),
        "RoundTurnCost": float(round_turn_cost),
        "Ledger": ledger,
    }


def run_tf_backtest(
    df: pd.DataFrame,
    ticker: str,
    L: int,
    S: float,
    eval_start: int | None = None,
    eval_end: int | None = None,
    warmup_bars: int | None = None,
    bars_back: int | None = None,
    rebase_at_eval_start: bool = True,
    round_turn_cost: float | None = None,
    cost_multiplier: float = 1.0,
) -> dict[str, object]:
    spec = get_market(ticker)
    resolved_cost = resolve_round_turn_cost(ticker, round_turn_cost, cost_multiplier)
    n = len(df)
    if eval_start is None:
        eval_start = 0
    if eval_end is None:
        eval_end = n
    if warmup_bars is None:
        warmup_bars = int(L) + 1

    slice_start = max(0, eval_start - warmup_bars)
    slice_end = eval_end
    min_len = max(int(L), int(warmup_bars), 100) + 5
    if slice_end - slice_start < min_len:
        return {"error": True, "family": "tf", "params": {"L": int(L), "S": float(S)}, "why": "slice too short"}

    local_eval_start = eval_start - slice_start
    if bars_back is None:
        bars_back = max(100, local_eval_start)

    output = _channel_core(
        df["Open"].values[slice_start:slice_end],
        df["High"].values[slice_start:slice_end],
        df["Low"].values[slice_start:slice_end],
        df["Close"].values[slice_start:slice_end],
        int(L),
        float(S),
        float(resolved_cost),
        float(spec.PV),
        float(spec.E0),
        int(bars_back),
        int(local_eval_start),
        bool(rebase_at_eval_start),
    )
    return _post_process_result(
        "tf",
        {"L": int(L), "S": float(S)},
        df,
        slice_start,
        eval_start,
        eval_end,
        warmup_bars,
        float(resolved_cost),
        output,
    )


def run_mr_backtest(
    df: pd.DataFrame,
    ticker: str,
    N1: float,
    N2: float,
    VolLen: int,
    MALen: int,
    StpPct: float,
    eval_start: int | None = None,
    eval_end: int | None = None,
    warmup_bars: int | None = None,
    round_turn_cost: float | None = None,
    cost_multiplier: float = 1.0,
) -> dict[str, object]:
    spec = get_market(ticker)
    resolved_cost = resolve_round_turn_cost(ticker, round_turn_cost, cost_multiplier)
    n = len(df)
    if eval_start is None:
        eval_start = 0
    if eval_end is None:
        eval_end = n
    if warmup_bars is None:
        warmup_bars = max(int(VolLen), int(MALen)) + 1

    slice_start = max(0, eval_start - warmup_bars)
    slice_end = eval_end
    min_len = max(int(VolLen), int(MALen), int(warmup_bars), 100) + 5
    if slice_end - slice_start < min_len:
        return {
            "error": True,
            "family": "mr",
            "params": {
                "N1": float(N1),
                "N2": float(N2),
                "VolLen": int(VolLen),
                "MALen": int(MALen),
                "StpPct": float(StpPct),
            },
            "why": "slice too short",
        }

    local_eval_start = eval_start - slice_start
    bars_back = max(2, local_eval_start)
    output = _mr_core(
        df["Open"].values[slice_start:slice_end],
        df["High"].values[slice_start:slice_end],
        df["Low"].values[slice_start:slice_end],
        df["Close"].values[slice_start:slice_end],
        float(N1),
        float(N2),
        int(VolLen),
        int(MALen),
        float(StpPct),
        float(resolved_cost),
        float(spec.PV),
        float(spec.E0),
        int(bars_back),
        int(local_eval_start),
    )
    return _post_process_result(
        "mr",
        {
            "N1": float(N1),
            "N2": float(N2),
            "VolLen": int(VolLen),
            "MALen": int(MALen),
            "StpPct": float(StpPct),
        },
        df,
        slice_start,
        eval_start,
        eval_end,
        warmup_bars,
        float(resolved_cost),
        output,
    )


def run_backtest(
    df: pd.DataFrame,
    ticker: str,
    family: str,
    params: dict[str, float | int],
    eval_start: int | None = None,
    eval_end: int | None = None,
    warmup_bars: int | None = None,
    round_turn_cost: float | None = None,
    cost_multiplier: float = 1.0,
) -> dict[str, object]:
    family = family.lower()
    if family == "tf":
        return run_tf_backtest(
            df,
            ticker,
            L=int(params["L"]),
            S=float(params["S"]),
            eval_start=eval_start,
            eval_end=eval_end,
            warmup_bars=warmup_bars,
            round_turn_cost=round_turn_cost,
            cost_multiplier=cost_multiplier,
        )
    if family == "mr":
        return run_mr_backtest(
            df,
            ticker,
            N1=float(params["N1"]),
            N2=float(params["N2"]),
            VolLen=int(params["VolLen"]),
            MALen=int(params["MALen"]),
            StpPct=float(params["StpPct"]),
            eval_start=eval_start,
            eval_end=eval_end,
            warmup_bars=warmup_bars,
            round_turn_cost=round_turn_cost,
            cost_multiplier=cost_multiplier,
        )
    raise ValueError(f"Unknown family {family!r}")


def _iter_family_grid(family: str, grid: dict[str, np.ndarray]):
    family = family.lower()
    if family == "tf":
        for L, S in product(grid["L"], grid["S"]):
            yield {"L": int(L), "S": float(S)}
    elif family == "mr":
        for N1, N2, vol_len, ma_len, stop_pct in product(
            grid["N1"],
            grid["N2"],
            grid["VolLen"],
            grid["MALen"],
            grid["StpPct"],
        ):
            yield {
                "N1": float(N1),
                "N2": float(N2),
                "VolLen": int(vol_len),
                "MALen": int(ma_len),
                "StpPct": float(stop_pct),
            }
    else:
        raise ValueError(f"Unknown family {family!r}")


def evaluate_family(
    df: pd.DataFrame,
    ticker: str,
    family: str,
    grid: dict[str, np.ndarray],
    eval_start: int,
    eval_end: int,
    round_turn_cost: float | None = None,
    cost_multiplier: float = 1.0,
) -> dict[str, object]:
    best_result: dict[str, object] | None = None
    best_obj = -np.inf
    tested = 0

    for params in _iter_family_grid(family, grid):
        result = run_backtest(
            df,
            ticker,
            family,
            params,
            eval_start=eval_start,
            eval_end=eval_end,
            round_turn_cost=round_turn_cost,
            cost_multiplier=cost_multiplier,
        )
        if result.get("error"):
            continue
        tested += 1
        if float(result["Objective"]) > best_obj:
            best_obj = float(result["Objective"])
            best_result = result

    if best_result is None:
        return {"error": True, "family": family, "why": "no valid parameter set", "tested": tested}

    best_result = dict(best_result)
    best_result["tested"] = tested
    return best_result
