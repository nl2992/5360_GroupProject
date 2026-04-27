import glob
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


# ============================================================
# Load all walk-forward OOS equity files
# ============================================================

equity_files = sorted(glob.glob("walk_forward_oos_equity_curve_IS*_OOS*_STEP*.csv"))

if len(equity_files) == 0:
    raise FileNotFoundError("No walk_forward_oos_equity_curve_IS*_OOS*_STEP*.csv files found.")

E0 = 100000.0

all_eq = {}
metrics_rows = []

for file in equity_files:
    match = re.search(r"IS\d+_OOS\d+_STEP\d+", file)
    tag = match.group(0) if match else file

    eq = pd.read_csv(file)

    eq["datetime"] = pd.to_datetime(
        eq["date"].astype(str) + " " + eq["time"].astype(str),
        errors="coerce"
    )

    eq = eq.dropna(subset=["datetime"]).sort_values("datetime").reset_index(drop=True)

    eq["barPnL"] = pd.to_numeric(eq["barPnL"], errors="coerce").fillna(0.0)
    eq["oosEquity"] = pd.to_numeric(eq["oosEquity"], errors="coerce")
    eq["tradeSize"] = pd.to_numeric(eq["tradeSize"], errors="coerce").fillna(0.0)
    eq["position"] = pd.to_numeric(eq["position"], errors="coerce").fillna(0)

    eq = eq.dropna(subset=["oosEquity"]).reset_index(drop=True)

    eq["cummax"] = eq["oosEquity"].cummax()
    eq["drawdown"] = eq["oosEquity"] - eq["cummax"]
    eq["drawdown_pct"] = eq["drawdown"] / eq["cummax"]

    eq["date_only"] = eq["datetime"].dt.date

    daily = (
        eq.groupby("date_only")
        .agg(
            daily_pnl=("barPnL", "sum"),
            equity=("oosEquity", "last"),
            trades=("tradeSize", "sum")
        )
        .reset_index()
    )

    daily["date_only"] = pd.to_datetime(daily["date_only"])
    daily = daily.sort_values("date_only").reset_index(drop=True)

    daily["daily_return"] = daily["equity"].pct_change()

    if len(daily) > 0:
        daily.loc[0, "daily_return"] = daily.loc[0, "daily_pnl"] / E0

    start_date = eq["datetime"].iloc[0]
    end_date = eq["datetime"].iloc[-1]
    days = (end_date - start_date).days
    years = days / 365.25 if days > 0 else np.nan

    ending_equity = eq["oosEquity"].iloc[-1]
    total_profit = ending_equity - E0
    total_return = ending_equity / E0 - 1

    cagr = (ending_equity / E0) ** (1 / years) - 1 if years > 0 and ending_equity > 0 else np.nan

    max_dd_dollar = eq["drawdown"].min()
    max_dd_pct = eq["drawdown_pct"].min()

    daily_mean = daily["daily_return"].mean()
    daily_std = daily["daily_return"].std()

    sharpe = np.sqrt(252) * daily_mean / daily_std if daily_std != 0 and pd.notna(daily_std) else np.nan

    gross_profit = eq.loc[eq["barPnL"] > 0, "barPnL"].sum()
    gross_loss = eq.loc[eq["barPnL"] < 0, "barPnL"].sum()

    profit_factor = gross_profit / abs(gross_loss) if gross_loss != 0 else np.nan

    calmar = cagr / abs(max_dd_pct) if max_dd_pct < 0 and pd.notna(cagr) else np.nan

    num_trades = eq["tradeSize"].sum()

    metrics_rows.append({
        "Config": tag,
        "Start": start_date,
        "End": end_date,
        "Years": years,
        "Ending Equity": ending_equity,
        "Total Profit": total_profit,
        "Total Return": total_return,
        "CAGR": cagr,
        "Max DD $": max_dd_dollar,
        "Max DD %": max_dd_pct,
        "Sharpe": sharpe,
        "Calmar": calmar,
        "Profit Factor": profit_factor,
        "Trade Size Sum": num_trades,
    })

    all_eq[tag] = eq


metrics = pd.DataFrame(metrics_rows)
metrics = metrics.sort_values("Sharpe", ascending=False)

print("\n================ Config Comparison Metrics ================\n")
print(metrics.to_string(index=False))

metrics.to_csv("walk_forward_config_comparison_metrics.csv", index=False)


# ============================================================
# Plot 1: Equity curve comparison
# ============================================================

plt.figure(figsize=(14, 7))

for tag, eq in all_eq.items():
    plt.plot(eq["datetime"], eq["oosEquity"], label=tag, linewidth=1.2)

plt.title("OOS Equity Curve Comparison")
plt.xlabel("Date")
plt.ylabel("OOS Equity")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.savefig("compare_oos_equity_curves.png", dpi=150)
plt.show()


# ============================================================
# Plot 2: Drawdown comparison
# ============================================================

plt.figure(figsize=(14, 7))

for tag, eq in all_eq.items():
    plt.plot(eq["datetime"], eq["drawdown"], label=tag, linewidth=1.2)

plt.title("OOS Drawdown Comparison")
plt.xlabel("Date")
plt.ylabel("Drawdown ($)")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.savefig("compare_oos_drawdowns.png", dpi=150)
plt.show()


# ============================================================
# Plot 3: Sharpe by config
# ============================================================

plt.figure(figsize=(12, 5))
plt.bar(metrics["Config"], metrics["Sharpe"])
plt.title("Annualized Sharpe by Walk-Forward Config")
plt.xlabel("Config")
plt.ylabel("Sharpe")
plt.xticks(rotation=45, ha="right")
plt.grid(True)
plt.tight_layout()
plt.savefig("compare_sharpe_by_config.png", dpi=150)
plt.show()


# ============================================================
# Plot 4: CAGR by config
# ============================================================

plt.figure(figsize=(12, 5))
plt.bar(metrics["Config"], metrics["CAGR"])
plt.title("CAGR by Walk-Forward Config")
plt.xlabel("Config")
plt.ylabel("CAGR")
plt.xticks(rotation=45, ha="right")
plt.grid(True)
plt.tight_layout()
plt.savefig("compare_cagr_by_config.png", dpi=150)
plt.show()


# ============================================================
# Plot 5: Max drawdown percentage by config
# ============================================================

plt.figure(figsize=(12, 5))
plt.bar(metrics["Config"], metrics["Max DD %"])
plt.title("Max Drawdown % by Walk-Forward Config")
plt.xlabel("Config")
plt.ylabel("Max Drawdown %")
plt.xticks(rotation=45, ha="right")
plt.grid(True)
plt.tight_layout()
plt.savefig("compare_maxdd_pct_by_config.png", dpi=150)
plt.show()


# ============================================================
# Plot 6: Profit factor by config
# ============================================================

plt.figure(figsize=(12, 5))
plt.bar(metrics["Config"], metrics["Profit Factor"])
plt.title("Profit Factor by Walk-Forward Config")
plt.xlabel("Config")
plt.ylabel("Profit Factor")
plt.xticks(rotation=45, ha="right")
plt.grid(True)
plt.tight_layout()
plt.savefig("compare_profit_factor_by_config.png", dpi=150)
plt.show()


# ============================================================
# Plot 7: Total profit by config
# ============================================================

plt.figure(figsize=(12, 5))
plt.bar(metrics["Config"], metrics["Total Profit"])
plt.title("Total OOS Profit by Walk-Forward Config")
plt.xlabel("Config")
plt.ylabel("Total Profit")
plt.xticks(rotation=45, ha="right")
plt.grid(True)
plt.tight_layout()
plt.savefig("compare_total_profit_by_config.png", dpi=150)
plt.show()


print("\nSaved:")
print("walk_forward_config_comparison_metrics.csv")
print("compare_oos_equity_curves.png")
print("compare_oos_drawdowns.png")
print("compare_sharpe_by_config.png")
print("compare_cagr_by_config.png")
print("compare_maxdd_pct_by_config.png")
print("compare_profit_factor_by_config.png")
print("compare_total_profit_by_config.png")