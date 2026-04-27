import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


# ============================================================
# Load data
# ============================================================

summary_file = "walk_forward_quarterly_summary_IS48_OOS12_STEP12.csv"
equity_file = "walk_forward_oos_equity_curve_IS48_OOS12_STEP12.csv"
trades_file = "walk_forward_oos_trade_events_IS48_OOS12_STEP12.csv"

summary = pd.read_csv(summary_file)
eq = pd.read_csv(equity_file)
trades = pd.read_csv(trades_file)


# ============================================================
# Clean datetime
# ============================================================

eq["datetime"] = pd.to_datetime(
    eq["date"].astype(str) + " " + eq["time"].astype(str),
    errors="coerce"
)

trades["datetime"] = pd.to_datetime(
    trades["date"].astype(str) + " " + trades["time"].astype(str),
    errors="coerce"
)

summary["InStart"] = pd.to_datetime(summary["InStart"], errors="coerce")
summary["InEnd"] = pd.to_datetime(summary["InEnd"], errors="coerce")
summary["OutStart"] = pd.to_datetime(summary["OutStart"], errors="coerce")
summary["OutEnd"] = pd.to_datetime(summary["OutEnd"], errors="coerce")

eq = eq.dropna(subset=["datetime"]).sort_values("datetime").reset_index(drop=True)
trades = trades.dropna(subset=["datetime"]).sort_values("datetime").reset_index(drop=True)
summary = summary.dropna(subset=["OutStart"]).sort_values("OutStart").reset_index(drop=True)


# ============================================================
# Basic checks
# ============================================================

if eq.empty:
    raise ValueError("walk_forward_oos_equity_curve.csv is empty or datetime parsing failed.")

E0 = 100000.0

required_cols = ["barPnL", "oosEquity", "position", "tradeSize"]

for col in required_cols:
    if col not in eq.columns:
        raise ValueError(f"Missing column in equity file: {col}")

eq["barPnL"] = pd.to_numeric(eq["barPnL"], errors="coerce").fillna(0.0)
eq["oosEquity"] = pd.to_numeric(eq["oosEquity"], errors="coerce")
eq["position"] = pd.to_numeric(eq["position"], errors="coerce").fillna(0)
eq["tradeSize"] = pd.to_numeric(eq["tradeSize"], errors="coerce").fillna(0.0)

eq = eq.dropna(subset=["oosEquity"]).reset_index(drop=True)

if not trades.empty:
    trades["tradeSize"] = pd.to_numeric(trades["tradeSize"], errors="coerce").fillna(0.0)
    trades["barPnL"] = pd.to_numeric(trades["barPnL"], errors="coerce").fillna(0.0)
    trades["oosEquity"] = pd.to_numeric(trades["oosEquity"], errors="coerce")


# ============================================================
# Equity, drawdown, daily PnL
# ============================================================

eq["cummax"] = eq["oosEquity"].cummax()
eq["drawdown"] = eq["oosEquity"] - eq["cummax"]
eq["drawdown_pct"] = eq["drawdown"] / eq["cummax"]

eq["date_only"] = eq["datetime"].dt.date

daily = (
    eq.groupby("date_only")
    .agg(
        daily_pnl=("barPnL", "sum"),
        equity=("oosEquity", "last"),
        tradeSize=("tradeSize", "sum"),
        avg_position=("position", "mean")
    )
    .reset_index()
)

daily["date_only"] = pd.to_datetime(daily["date_only"])
daily = daily.sort_values("date_only").reset_index(drop=True)

daily["daily_return"] = daily["equity"].pct_change()

if len(daily) > 0:
    daily.loc[0, "daily_return"] = daily.loc[0, "daily_pnl"] / E0

daily["cummax"] = daily["equity"].cummax()
daily["drawdown"] = daily["equity"] - daily["cummax"]
daily["drawdown_pct"] = daily["drawdown"] / daily["cummax"]


# ============================================================
# Metrics
# ============================================================

start_date = eq["datetime"].iloc[0]
end_date = eq["datetime"].iloc[-1]

days = (end_date - start_date).days
years = days / 365.25 if days > 0 else np.nan

ending_equity = eq["oosEquity"].iloc[-1]
total_profit = ending_equity - E0
total_return = ending_equity / E0 - 1

if years and years > 0 and ending_equity > 0:
    cagr = (ending_equity / E0) ** (1 / years) - 1
else:
    cagr = np.nan

max_drawdown_dollar = eq["drawdown"].min()
max_drawdown_pct = eq["drawdown_pct"].min()

if pd.notna(cagr) and max_drawdown_pct < 0:
    calmar = cagr / abs(max_drawdown_pct)
else:
    calmar = np.nan

daily_mean = daily["daily_return"].mean()
daily_std = daily["daily_return"].std()

if daily_std != 0 and pd.notna(daily_std):
    annualized_sharpe = np.sqrt(252) * daily_mean / daily_std
else:
    annualized_sharpe = np.nan

downside_returns = daily.loc[daily["daily_return"] < 0, "daily_return"]
downside_std = downside_returns.std()

if downside_std != 0 and pd.notna(downside_std):
    sortino = np.sqrt(252) * daily_mean / downside_std
else:
    sortino = np.nan

gross_profit = eq.loc[eq["barPnL"] > 0, "barPnL"].sum()
gross_loss = eq.loc[eq["barPnL"] < 0, "barPnL"].sum()

if gross_loss != 0:
    profit_factor = gross_profit / abs(gross_loss)
else:
    profit_factor = np.nan

winning_bars = int((eq["barPnL"] > 0).sum())
losing_bars = int((eq["barPnL"] < 0).sum())
flat_bars = int((eq["barPnL"] == 0).sum())

if winning_bars + losing_bars > 0:
    bar_win_rate = winning_bars / (winning_bars + losing_bars)
else:
    bar_win_rate = np.nan

num_trade_events = len(trades)
approx_round_turns = eq["tradeSize"].sum()

avg_daily_pnl = daily["daily_pnl"].mean()
daily_pnl_std = daily["daily_pnl"].std()

best_day = daily["daily_pnl"].max()
worst_day = daily["daily_pnl"].min()

positive_days = int((daily["daily_pnl"] > 0).sum())
negative_days = int((daily["daily_pnl"] < 0).sum())

if positive_days + negative_days > 0:
    daily_win_rate = positive_days / (positive_days + negative_days)
else:
    daily_win_rate = np.nan

exposure_long = (eq["position"] == 1).mean()
exposure_short = (eq["position"] == -1).mean()
exposure_flat = (eq["position"] == 0).mean()

metrics = {
    "Start Date": start_date,
    "End Date": end_date,
    "Years": years,
    "Initial Equity": E0,
    "Ending Equity": ending_equity,
    "Total Profit": total_profit,
    "Total Return": total_return,
    "CAGR": cagr,
    "Max Drawdown $": max_drawdown_dollar,
    "Max Drawdown %": max_drawdown_pct,
    "Calmar Ratio": calmar,
    "Annualized Sharpe": annualized_sharpe,
    "Sortino Ratio": sortino,
    "Gross Profit": gross_profit,
    "Gross Loss": gross_loss,
    "Profit Factor": profit_factor,
    "Average Daily PnL": avg_daily_pnl,
    "Daily PnL Std": daily_pnl_std,
    "Best Day": best_day,
    "Worst Day": worst_day,
    "Positive Days": positive_days,
    "Negative Days": negative_days,
    "Daily Win Rate": daily_win_rate,
    "Winning Bars": winning_bars,
    "Losing Bars": losing_bars,
    "Flat Bars": flat_bars,
    "Bar Win Rate": bar_win_rate,
    "Trade Events": num_trade_events,
    "Approx Round Turns": approx_round_turns,
    "Long Exposure": exposure_long,
    "Short Exposure": exposure_short,
    "Flat Exposure": exposure_flat,
}

metrics_df = pd.DataFrame(metrics.items(), columns=["Metric", "Value"])


# ============================================================
# Print metrics
# ============================================================

pd.set_option("display.max_rows", 100)
pd.set_option("display.width", 140)

print("\n================ OOS Metrics ================\n")
print(metrics_df.to_string(index=False))


# ============================================================
# Save processed data
# ============================================================

metrics_df.to_csv("walk_forward_oos_metrics.csv", index=False)
daily.to_csv("walk_forward_oos_daily_pnl.csv", index=False)
eq.to_csv("walk_forward_oos_equity_curve_processed.csv", index=False)

print("\nSaved:")
print("walk_forward_oos_metrics.csv")
print("walk_forward_oos_daily_pnl.csv")
print("walk_forward_oos_equity_curve_processed.csv")


# ============================================================
# Plot 1: OOS equity curve
# ============================================================

plt.figure(figsize=(14, 6))
plt.plot(eq["datetime"], eq["oosEquity"])
plt.title("Walk-Forward Fully Out-of-Sample Equity Curve")
plt.xlabel("Date")
plt.ylabel("OOS Equity")
plt.grid(True)
plt.tight_layout()
plt.savefig("plot_oos_equity_curve.png", dpi=150)
plt.show()


# ============================================================
# Plot 2: OOS drawdown dollar
# ============================================================

plt.figure(figsize=(14, 5))
plt.plot(eq["datetime"], eq["drawdown"])
plt.title("Out-of-Sample Drawdown")
plt.xlabel("Date")
plt.ylabel("Drawdown ($)")
plt.grid(True)
plt.tight_layout()
plt.savefig("plot_oos_drawdown_dollar.png", dpi=150)
plt.show()


# ============================================================
# Plot 3: OOS drawdown percentage
# ============================================================

plt.figure(figsize=(14, 5))
plt.plot(eq["datetime"], eq["drawdown_pct"])
plt.title("Out-of-Sample Drawdown Percentage")
plt.xlabel("Date")
plt.ylabel("Drawdown %")
plt.grid(True)
plt.tight_layout()
plt.savefig("plot_oos_drawdown_pct.png", dpi=150)
plt.show()


# ============================================================
# Plot 4: Daily OOS PnL
# ============================================================

plt.figure(figsize=(14, 5))
plt.plot(daily["date_only"], daily["daily_pnl"])
plt.title("Daily OOS PnL")
plt.xlabel("Date")
plt.ylabel("Daily PnL")
plt.grid(True)
plt.tight_layout()
plt.savefig("plot_daily_oos_pnl.png", dpi=150)
plt.show()


# ============================================================
# Plot 5: Daily return distribution
# ============================================================

plt.figure(figsize=(10, 5))
plt.hist(daily["daily_return"].dropna(), bins=80)
plt.title("Distribution of Daily OOS Returns")
plt.xlabel("Daily Return")
plt.ylabel("Frequency")
plt.grid(True)
plt.tight_layout()
plt.savefig("plot_daily_return_distribution.png", dpi=150)
plt.show()


# ============================================================
# Plot 6: Rolling Sharpe
# ============================================================

window = 63

daily["rolling_sharpe_63d"] = (
    np.sqrt(252)
    * daily["daily_return"].rolling(window).mean()
    / daily["daily_return"].rolling(window).std()
)

plt.figure(figsize=(14, 5))
plt.plot(daily["date_only"], daily["rolling_sharpe_63d"])
plt.title("63-Day Rolling Sharpe")
plt.xlabel("Date")
plt.ylabel("Rolling Sharpe")
plt.grid(True)
plt.tight_layout()
plt.savefig("plot_rolling_sharpe_63d.png", dpi=150)
plt.show()


# ============================================================
# Plot 7: Rolling 1-year return
# ============================================================

window = 252

daily["rolling_1y_return"] = daily["equity"].pct_change(window)

plt.figure(figsize=(14, 5))
plt.plot(daily["date_only"], daily["rolling_1y_return"])
plt.title("Rolling 1-Year OOS Return")
plt.xlabel("Date")
plt.ylabel("1-Year Return")
plt.grid(True)
plt.tight_layout()
plt.savefig("plot_rolling_1y_return.png", dpi=150)
plt.show()


# ============================================================
# Plot 8: Best Length selected over time
# ============================================================

if "BestLength" in summary.columns and not summary.empty:
    plt.figure(figsize=(14, 5))
    plt.plot(summary["OutStart"], summary["BestLength"], marker="o", linewidth=1)
    plt.title("Best Length Selected Over Time")
    plt.xlabel("OOS Start Date")
    plt.ylabel("Best Length")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("plot_best_length_over_time.png", dpi=150)
    plt.show()


# ============================================================
# Plot 9: Best StopPct selected over time
# ============================================================

if "BestStopPct" in summary.columns and not summary.empty:
    plt.figure(figsize=(14, 5))
    plt.plot(summary["OutStart"], summary["BestStopPct"], marker="o", linewidth=1)
    plt.title("Best StopPct Selected Over Time")
    plt.xlabel("OOS Start Date")
    plt.ylabel("Best StopPct")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("plot_best_stoppct_over_time.png", dpi=150)
    plt.show()


# ============================================================
# Plot 10: Quarterly OOS profit
# ============================================================

if "OutProfit" in summary.columns and not summary.empty:
    plt.figure(figsize=(14, 5))
    plt.bar(summary["OutStart"], summary["OutProfit"], width=60)
    plt.title("Quarterly OOS Profit")
    plt.xlabel("OOS Start Date")
    plt.ylabel("OOS Profit")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("plot_quarterly_oos_profit.png", dpi=150)
    plt.show()


# ============================================================
# Plot 11: Position exposure over time
# ============================================================

plt.figure(figsize=(14, 4))
plt.plot(eq["datetime"], eq["position"])
plt.title("OOS Position Over Time")
plt.xlabel("Date")
plt.ylabel("Position")
plt.yticks([-1, 0, 1])
plt.grid(True)
plt.tight_layout()
plt.savefig("plot_oos_position.png", dpi=150)
plt.show()


# ============================================================
# Plot 12: Monthly trade activity
# ============================================================

if not trades.empty:
    trades_by_month = trades.set_index("datetime").resample("ME")["tradeSize"].sum()

    plt.figure(figsize=(14, 5))
    plt.plot(trades_by_month.index, trades_by_month.values)
    plt.title("Monthly Trade Activity")
    plt.xlabel("Date")
    plt.ylabel("Trade Size Sum")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("plot_monthly_trade_activity.png", dpi=150)
    plt.show()


# ============================================================
# Plot 13: Monthly PnL
# ============================================================

monthly = eq.set_index("datetime").resample("ME").agg(
    monthly_pnl=("barPnL", "sum"),
    equity=("oosEquity", "last"),
    trades=("tradeSize", "sum")
).reset_index()

plt.figure(figsize=(14, 5))
plt.bar(monthly["datetime"], monthly["monthly_pnl"], width=20)
plt.title("Monthly OOS PnL")
plt.xlabel("Date")
plt.ylabel("Monthly PnL")
plt.grid(True)
plt.tight_layout()
plt.savefig("plot_monthly_oos_pnl.png", dpi=150)
plt.show()

monthly.to_csv("walk_forward_oos_monthly_pnl.csv", index=False)

print("walk_forward_oos_monthly_pnl.csv")
print("\nAll plots saved as PNG files.")