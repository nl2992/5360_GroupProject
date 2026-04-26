import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

os.makedirs("outputs", exist_ok=True)

wf = pd.read_csv("quarterly_best_params.csv")
eq = pd.read_csv("oos_equity.csv")

eq["datetime"] = pd.to_datetime(eq["datetime"], dayfirst=True, errors="coerce")
eq = eq.dropna(subset=["datetime"]).sort_values("datetime").reset_index(drop=True)
eq_agg = eq.groupby("datetime")["equity"].last().reset_index()

for col in ["is_start", "is_end", "oos_start", "oos_end"]:
    wf[col] = pd.to_datetime(wf[col], dayfirst=True, errors="coerce")

wf_q = wf.groupby("window").first().reset_index()
x = wf_q["oos_start"]  # use date as x axis

# equity curve
fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(eq_agg["datetime"], eq_agg["equity"], color="green", linewidth=0.8)
ax.fill_between(eq_agg["datetime"], eq_agg["equity"], alpha=0.1, color="green")
ax.axhline(eq_agg["equity"].iloc[0], linestyle="--", color="gray", linewidth=0.8)
ax.set_title("OOS Equity Curve - TY Channel Strategy")
ax.set_xlabel("Date")
ax.set_ylabel("P&L (USD)")
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v:,.0f}"))
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("outputs/oos_equity_curve_TY.png", dpi=200)
plt.close()

# best params each window
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 6), sharex=True)
ax1.bar(x, wf_q["chn_len"], color="steelblue", alpha=0.8, width=20)
ax1.set_ylabel("ChnLen")
ax1.set_title("Optimal Params per Quarter - TY")
ax1.grid(True, axis="y", alpha=0.3)

ax2.bar(x, wf_q["stp_pct"] * 100, color="orange", alpha=0.8, width=20)
ax2.set_ylabel("StopPct (%)")
ax2.set_xlabel("Date")
ax2.grid(True, axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig("outputs/optimal_params_TY.png", dpi=200)
plt.close()

# IS profit
fig, ax = plt.subplots(figsize=(12, 5))
colors = ["steelblue" if v >= 0 else "red" for v in wf_q["is_net_profit"]]
ax.bar(x, wf_q["is_net_profit"], color=colors, alpha=0.8, width=20)
ax.axhline(0, color="black", linewidth=0.8)
ax.set_title("In-Sample Net Profit per Quarter - TY")
ax.set_xlabel("Date")
ax.set_ylabel("Net Profit (USD)")
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v:,.0f}"))
ax.grid(True, axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig("outputs/is_profit_TY.png", dpi=200)
plt.close()

# IS drawdown
fig, ax = plt.subplots(figsize=(12, 5))
ax.bar(x, wf_q["is_max_drawdown"], color="red", alpha=0.8, width=20)
ax.axhline(0, color="black", linewidth=0.8)
ax.set_title("In-Sample Max Drawdown per Quarter - TY")
ax.set_xlabel("Date")
ax.set_ylabel("Drawdown (USD)")
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v:,.0f}"))
ax.grid(True, axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig("outputs/is_drawdown_TY.png", dpi=200)
plt.close()

# summary
total_eq_change = eq_agg["equity"].iloc[-1] - eq_agg["equity"].iloc[0]
total_windows = len(wf_q)
avg_trades = wf_q["is_num_trades"].mean()

rows = [
    ["Total OOS Equity Change", f"${total_eq_change:,.0f}"],
    ["Total Walk-Forward Windows", str(total_windows)],
    ["Avg IS Trades per Window", f"{avg_trades:.1f}"],
    ["Avg IS Net Profit", f"${wf_q['is_net_profit'].mean():,.0f}"],
    ["Avg IS Max Drawdown", f"${wf_q['is_max_drawdown'].mean():,.0f}"],
]

fig, ax = plt.subplots(figsize=(7, 3.5))
ax.axis("off")
tbl = ax.table(cellText=rows, colLabels=["Metric", "Value"],
               cellLoc="center", loc="center", bbox=[0, 0, 1, 1])
tbl.auto_set_font_size(False)
tbl.set_fontsize(11)
for (r, c), cell in tbl.get_celld().items():
    if r == 0:
        cell.set_facecolor("#4C72B0")
        cell.set_text_props(color="white", fontweight="bold")
    elif r % 2 == 0:
        cell.set_facecolor("#f0f4ff")
    cell.set_edgecolor("white")
ax.set_title("Performance Summary - TY", fontsize=11, pad=20)
plt.tight_layout()
plt.savefig("outputs/performance_summary_TY.png", dpi=200, bbox_inches="tight")
plt.close()

print("done")
