#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import os
import zipfile
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# In[ ]:


MARKETS = {
    "TY": {"file": "TY-5minHLV.csv", "slpg": 19, "point_value": 1000.0},
    "BTC": {"file": "BTC-5minHLV.csv", "slpg":25, "point_value":5.0}
}

E0 = 100000.0
BARS_BACK = 0
IN_SAMPLE_YEARS = 4
OOS_MONTHS = 3

# Use "small" to test the full pipeline quickly; use "full" for final project results.
RUN_MODE = "small"
if RUN_MODE == "full":
    LENGTH_GRID = range(500, 10001, 10)
    STOP_GRID = np.round(np.arange(0.005, 0.1001, 0.001), 3)
elif RUN_MODE == "small":
    LENGTH_GRID = [500, 1000, 2000]
    STOP_GRID = [0.010,0.030]
else:
    raise ValueError("RUN_MODE must be 'small' or 'full'.")

OUTPUT_DIR = f"channel_dd_results_{RUN_MODE}"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# In[ ]:


# helper
def load_hlv_file(path):
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    df["Datetime"] = pd.to_datetime(df["Date"].astype(str) + " " + df["Time"].astype(str), errors="coerce")
    df = df.dropna(subset=["Datetime"]).sort_values("Datetime").reset_index(drop=True)
    for c in ["Open", "High", "Low", "Close"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna(subset=["High", "Low", "Close"]).reset_index(drop=True)

def compute_hh_ll(high, low, length):
    return pd.Series(high).shift(1).rolling(length).max().to_numpy(), pd.Series(low).shift(1).rolling(length).min().to_numpy()


# In[3]:


# trade strategy
def run_channel_dd_strategy(df, length, stop_pct, bars_back, slpg, point_value, initial_equity=E0, record_trades=False):
    high, low, close = df["High"].to_numpy(), df["Low"].to_numpy(), df["Close"].to_numpy()
    time = df["Datetime"].to_numpy()
    n = len(df)
    start_k = max(bars_back, length)
    hh, ll = compute_hh_ll(high, low, length)
    equity = np.ones(n) * initial_equity
    drawdown = np.zeros(n)
    trades = np.zeros(n)
    position = 0
    benchmark_long = np.nan
    benchmark_short = np.nan
    equity_max = initial_equity
    trade_records = []

    for k in range(start_k, n):
        traded = False
        delta = point_value * (close[k] - close[k - 1]) * position
        action = None
        trade_price = np.nan
        old_position = position

        if position == 0:
            buy = high[k] >= hh[k]
            sell = low[k] <= ll[k]
            if buy and sell:
                delta = -slpg + point_value * (ll[k] - hh[k])
                trades[k] = 1
                action = "flat_buy_and_sell_same_bar"
            else:
                if buy:
                    delta = -slpg / 2 + point_value * (close[k] - hh[k])
                    position = 1; traded = True; benchmark_long = high[k]; trades[k] = 0.5
                    action = "enter_long"; trade_price = hh[k]
                if sell:
                    delta = -slpg / 2 - point_value * (close[k] - ll[k])
                    position = -1; traded = True; benchmark_short = low[k]; trades[k] = 0.5
                    action = "enter_short"; trade_price = ll[k]

        if position == 1 and not traded:
            sell_short = low[k] <= ll[k]
            sell_stop = low[k] <= benchmark_long * (1 - stop_pct)
            if sell_short and sell_stop:
                delta = delta - slpg - 2 * point_value * (close[k] - ll[k])
                position = -1; benchmark_short = low[k]; trades[k] = 1
                action = "reverse_long_to_short"; trade_price = ll[k]
            else:
                if sell_stop:
                    stop_price = benchmark_long * (1 - stop_pct)
                    delta = delta - slpg / 2 - point_value * (close[k] - stop_price)
                    position = 0; trades[k] = 0.5
                    action = "exit_long_stop"; trade_price = stop_price
                if sell_short:
                    delta = delta - slpg - 2 * point_value * (close[k] - ll[k])
                    position = -1; benchmark_short = low[k]; trades[k] = 1
                    action = "reverse_long_to_short"; trade_price = ll[k]
            benchmark_long = max(high[k], benchmark_long)

        if position == -1 and not traded:
            buy_long = high[k] >= hh[k]
            buy_stop = high[k] >= benchmark_short * (1 + stop_pct)
            if buy_long and buy_stop:
                delta = delta - slpg + 2 * point_value * (close[k] - hh[k])
                position = 1; benchmark_long = high[k]; trades[k] = 1
                action = "reverse_short_to_long"; trade_price = hh[k]
            else:
                if buy_stop:
                    stop_price = benchmark_short * (1 + stop_pct)
                    delta = delta - slpg / 2 + point_value * (close[k] - stop_price)
                    position = 0; trades[k] = 0.5
                    action = "exit_short_stop"; trade_price = stop_price
                if buy_long:
                    delta = delta - slpg + 2 * point_value * (close[k] - hh[k])
                    position = 1; benchmark_long = high[k]; trades[k] = 1
                    action = "reverse_short_to_long"; trade_price = hh[k]
            benchmark_short = min(low[k], benchmark_short)

        equity[k] = equity[k - 1] + delta
        equity_max = max(equity_max, equity[k])
        drawdown[k] = equity[k] - equity_max

        if record_trades and trades[k] > 0:
            trade_records.append({"Datetime": time[k], "Action": action, "OldPosition": old_position, "NewPosition": position,
                                  "TradePrice": trade_price, "Close": close[k], "DeltaPnL": delta,
                                  "StrategyEquity": equity[k], "TradeCount": trades[k], "Length": length, "StopPct": stop_pct})
    out = {"Equity": equity, "Drawdown": drawdown, "Trades": trades, "HH": hh, "LL": ll}
    if record_trades:
        out["TradeTable"] = pd.DataFrame(trade_records)
    return out

def pnl_from_equity(equity):
    return np.diff(equity, prepend=equity[0])


# In[ ]:


# metrics
def summarize_metrics(profit, worst_drawdown, avg_pnl, std_pnl, period_trades, trade_pnls):
    winners = trade_pnls[trade_pnls > 0]
    losers = trade_pnls[trade_pnls < 0]
    gross_profit = np.sum(winners) if len(winners) else 0.0
    gross_loss = abs(np.sum(losers)) if len(losers) else 0.0
    return {
        "Profit": profit,
        "WorstDrawdown": worst_drawdown,
        "StdPnL": std_pnl,
        "AvgPnL": avg_pnl,
        "SharpeLike": avg_pnl / std_pnl if std_pnl != 0 else np.nan,
        "TotalTrades": np.sum(period_trades),
        "ReturnOnAccount": profit / abs(worst_drawdown) if worst_drawdown != 0 else np.nan,
        "PctWinners": len(winners) / len(trade_pnls) if len(trade_pnls) else np.nan,
        "AvgWinner": np.mean(winners) if len(winners) else np.nan,
        "AvgLoser": np.mean(losers) if len(losers) else np.nan,
        "ProfitFactor": gross_profit / gross_loss if gross_loss != 0 else np.nan,
    }

def metrics_from_equity(equity, drawdown, trades, start_idx, end_idx):
    pnl = pnl_from_equity(equity)
    period_pnl = pnl[start_idx:end_idx + 1]
    period_trades = trades[start_idx:end_idx + 1]
    profit = equity[end_idx] - equity[start_idx]
    worst_drawdown = np.min(drawdown[start_idx:end_idx + 1])
    return summarize_metrics(profit, worst_drawdown, np.mean(period_pnl), np.std(period_pnl), period_trades, period_pnl[period_trades > 0])

def metrics_from_oos_pnl(period_pnl, period_trades, starting_equity):
    local_equity = starting_equity + np.cumsum(period_pnl)
    local_max = np.maximum.accumulate(np.r_[starting_equity, local_equity])[:-1]
    local_drawdown = local_equity - local_max
    metrics = summarize_metrics(np.sum(period_pnl), np.min(local_drawdown) if len(local_drawdown) else 0,
                                np.mean(period_pnl), np.std(period_pnl), period_trades, period_pnl[period_trades > 0])
    metrics["EndingEquity"] = local_equity[-1] if len(local_equity) else starting_equity
    return metrics, local_equity, local_drawdown

def objective_score(metrics):
    dd = metrics["WorstDrawdown"]
    return metrics["Profit"] / abs(dd) if dd != 0 and not np.isnan(dd) else -np.inf

def date_to_index(df, date):
    return int(np.searchsorted(df["Datetime"].values, np.datetime64(date), side="left"))


# In[ ]:


# optimization
def rolling_windows(df, in_sample_years=IN_SAMPLE_YEARS, oos_months=OOS_MONTHS):
    start_date, end_date = df["Datetime"].min(), df["Datetime"].max()
    oos_start = start_date + pd.DateOffset(years=in_sample_years)
    windows = []
    while True:
        is_start, is_end = oos_start - pd.DateOffset(years=in_sample_years), oos_start
        oos_end = oos_start + pd.DateOffset(months=oos_months)
        if oos_end > end_date:
            break
        windows.append({"IS_StartDate": is_start, "IS_EndDate": is_end, "OOS_StartDate": oos_start, "OOS_EndDate": oos_end,
                        "IS_StartIdx": date_to_index(df, is_start), "IS_EndIdx": date_to_index(df, is_end) - 1,
                        "OOS_StartIdx": date_to_index(df, oos_start), "OOS_EndIdx": date_to_index(df, oos_end) - 1})
        oos_start = oos_start + pd.DateOffset(months=oos_months)
    return windows
    
def optimize_one_window(df, window, length_grid, stop_grid, bars_back, slpg, point_value):
    best_score, best_row = -np.inf, None
    for length in length_grid:
        if length >= window["IS_EndIdx"] - window["IS_StartIdx"]:
            continue
        for stop_pct in stop_grid:
            result = run_channel_dd_strategy(df, length, stop_pct, bars_back, slpg, point_value)
            metrics = metrics_from_equity(result["Equity"], result["Drawdown"], result["Trades"], window["IS_StartIdx"], window["IS_EndIdx"])
            score = objective_score(metrics)
            if score > best_score:
                best_score = score
                best_row = {"Length": length, "StopPct": stop_pct, "Score": score, **metrics}
    return best_row

def run_rolling_project_for_market(market_name, file_path, slpg, point_value):
    df = load_hlv_file(file_path)
    windows = rolling_windows(df)
    print(f"Running {market_name}: {len(df)} rows, {len(windows)} windows, mode={RUN_MODE}")
    parameter_rows, performance_rows, all_oos_equity, all_trades = [], [], [], []
    stitched_equity_start = E0

    for w_id, window in enumerate(windows, start=1):
        print(f"Window {w_id}/{len(windows)}: IS {window['IS_StartDate'].date()} to {window['IS_EndDate'].date()}, OOS {window['OOS_StartDate'].date()} to {window['OOS_EndDate'].date()}")
        best = optimize_one_window(df, window, LENGTH_GRID, STOP_GRID, BARS_BACK, slpg, point_value)
        if best is None:
            continue
        length_best, stop_best = int(best["Length"]), float(best["StopPct"])
        parameter_rows.append({"Market": market_name, "Window": w_id, "IS_Start": window["IS_StartDate"], "IS_End": window["IS_EndDate"],
                               "OOS_Start": window["OOS_StartDate"], "OOS_End": window["OOS_EndDate"], "Best_Length": length_best,
                               "Best_StopPct": stop_best, "IS_Score": best["Score"], "IS_Profit": best["Profit"],
                               "IS_WorstDrawdown": best["WorstDrawdown"], "IS_TotalTrades": best["TotalTrades"]})
        oos_result = run_channel_dd_strategy(df, length_best, stop_best, BARS_BACK, slpg, point_value, record_trades=True)
        raw_pnl = pnl_from_equity(oos_result["Equity"])
        idx = np.arange(window["OOS_StartIdx"], window["OOS_EndIdx"] + 1)
        metrics, local_equity, local_drawdown = metrics_from_oos_pnl(raw_pnl[idx], oos_result["Trades"][idx], stitched_equity_start)
        stitched_equity_start = metrics["EndingEquity"]
        performance_rows.append({"Market": market_name, "Window": w_id, "OOS_Start": window["OOS_StartDate"], "OOS_End": window["OOS_EndDate"],
                                 "Length": length_best, "StopPct": stop_best, **metrics})
        all_oos_equity.append(pd.DataFrame({"Market": market_name, "Window": w_id, "Datetime": df.loc[idx, "Datetime"].values,
                                            "OOSPnL": raw_pnl[idx], "OOSStitchedEquity": local_equity,
                                            "OOSStitchedDrawdown": local_drawdown, "TradeCount": oos_result["Trades"][idx],
                                            "Length": length_best, "StopPct": stop_best}))
        tt = oos_result["TradeTable"]
        tt = tt[(tt["Datetime"] >= window["OOS_StartDate"]) & (tt["Datetime"] < window["OOS_EndDate"])].copy()
        if len(tt):
            tt["Market"] = market_name; tt["Window"] = w_id; all_trades.append(tt)

    params_df = pd.DataFrame(parameter_rows)
    perf_df = pd.DataFrame(performance_rows)
    equity_df = pd.concat(all_oos_equity, ignore_index=True) if all_oos_equity else pd.DataFrame()
    trades_df = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()
    params_df.to_csv(f"{OUTPUT_DIR}/{market_name}_quarterly_best_params.csv", index=False)
    perf_df.to_csv(f"{OUTPUT_DIR}/{market_name}_oos_performance.csv", index=False)
    equity_df.to_csv(f"{OUTPUT_DIR}/{market_name}_oos_equity_curve.csv", index=False)
    trades_df.to_csv(f"{OUTPUT_DIR}/{market_name}_oos_trade_table.csv", index=False)
    return {"data": df, "params": params_df, "performance": perf_df, "equity": equity_df, "trades": trades_df}

def full_sample_optimization(df, slpg, point_value):
    return optimize_one_window(df, {"IS_StartIdx": BARS_BACK, "IS_EndIdx": len(df) - 1}, LENGTH_GRID, STOP_GRID, BARS_BACK, slpg, point_value)


# In[ ]:


# summary
def make_summary(perf_df, params_df, market_name):
    return pd.DataFrame([{
        "Market": market_name, "RunMode": RUN_MODE,
        "Total OOS Equity Change": perf_df["Profit"].sum(),
        "Total Walk-Forward Windows": perf_df["Window"].nunique(),
        "Avg IS Trades per Window": params_df["IS_TotalTrades"].mean(),
        "Avg IS Net Profit": params_df["IS_Profit"].mean(),
        "Avg IS Max Drawdown": params_df["IS_WorstDrawdown"].abs().mean(),
        "Avg OOS Net Profit": perf_df["Profit"].mean(),
        "Avg OOS SharpeLike": perf_df["SharpeLike"].mean(),
        "Avg OOS ReturnOnAccount": perf_df["ReturnOnAccount"].mean(),
        "Positive OOS Windows": (perf_df["Profit"] > 0).sum(),
        "Negative OOS Windows": (perf_df["Profit"] < 0).sum(),
        "OOS Window Win Rate": (perf_df["Profit"] > 0).mean(),
    }])


# In[4]:


all_summaries = []
all_results = {}

for market_name, cfg in MARKETS.items():
    result = run_rolling_project_for_market(market_name, cfg["file"], cfg["slpg"], cfg["point_value"])
    all_results[market_name] = result

    full_best = full_sample_optimization(result["data"], cfg["slpg"], cfg["point_value"])
    pd.DataFrame([full_best]).to_csv(f"{OUTPUT_DIR}/{market_name}_full_sample_best.csv", index=False)

    summary_df = make_summary(result["performance"], result["params"], market_name)
    summary_df.to_csv(f"{OUTPUT_DIR}/{market_name}_summary.csv", index=False)
    all_summaries.append(summary_df)

    print(f"\n{market_name} summary")
    display(summary_df)
    print(f"\n{market_name} full-sample best")
    display(pd.DataFrame([full_best]))

combined_summary = pd.concat(all_summaries, ignore_index=True) if all_summaries else pd.DataFrame()
if len(combined_summary):
    combined_summary.to_csv(f"{OUTPUT_DIR}/all_market_summary.csv", index=False)
    print("Combined summary")
    display(combined_summary)

print(f"Finished. Results saved in: {OUTPUT_DIR}")

