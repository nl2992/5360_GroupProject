import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

Path("outputs").mkdir(exist_ok=True)

wf = pd.read_csv("walk_forward_4y_update_results.csv")
eq = pd.read_csv("equity_plot.csv")

for col in ["InStart", "InEnd", "OutStart", "OutEnd"]:
    wf[col] = pd.to_datetime(wf[col], dayfirst=True)

eq["datetime"] = pd.to_datetime(
    eq["date"].astype(str) + " " + eq["time"].astype(str),
    dayfirst=True, errors="coerce"
)
eq = eq.dropna(subset=["datetime"]).sort_values("datetime").reset_index(drop=True)

labels = [f"W{i+1}\n{r.OutStart.strftime('%Y')}" for i, r in wf.iterrows()]
x = np.arange(len(wf))

# plot 1: equity curve
fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(eq["datetime"], eq["E"], color="green", linewidth=0.8)
ax.fill_between(eq["datetime"], eq["E"], alpha=0.1, color="green")
ax.axhline(eq["E"].iloc[0], linestyle="--", color="gray", linewidth=0.8)
for _, r in wf.iterrows():
    ax.axvline(r["OutStart"], color="gray", linestyle=":", linewidth=0.6, alpha=0.5)
ax.set_title("OOS Equity Curve - HO Channel Strategy")
ax.set_xlabel("Date")
ax.set_ylabel("P&L (USD)")
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v:,.0f}"))
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("outputs/oos_equity_curve.png", dpi=200)
plt.close()

# plot 2: in sample vs oos profit
fig, ax = plt.subplots(figsize=(11, 5))
w = 0.35
ax.bar(x - w/2, wf["InProfit"], w, label="In-Sample", color="steelblue", alpha=0.8)
ax.bar(x + w/2, wf["OutProfit"], w, label="OOS", color="orange", alpha=0.8)
ax.axhline(0, color="black", linewidth=0.8)
ax.set_xticks(x)
ax.set_xticklabels(labels, fontsize=9)
ax.set_title("In-Sample vs OOS Profit per Window")
ax.set_ylabel("Net Profit (USD)")
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v:,.0f}"))
ax.legend()
ax.grid(True, axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig("outputs/insample_vs_oos_profit.png", dpi=200)
plt.close()

# plot 3: best params each window
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
ax1.bar(x, wf["BestLength"], color="steelblue", alpha=0.8)
ax1.set_ylabel("ChnLen")
ax1.set_title("Optimal Params per Window")
ax1.grid(True, axis="y", alpha=0.3)
for i, v in enumerate(wf["BestLength"]):
    ax1.text(i, v + 50, str(int(v)), ha="center", fontsize=8)
ax2.bar(x, wf["BestStopPct"] * 100, color="orange", alpha=0.8)
ax2.set_ylabel("StopPct (%)")
ax2.set_xticks(x)
ax2.set_xticklabels(labels, fontsize=9)
ax2.grid(True, axis="y", alpha=0.3)
for i, v in enumerate(wf["BestStopPct"]):
    ax2.text(i, v * 100 + 0.1, f"{v*100:.1f}%", ha="center", fontsize=8)
plt.tight_layout()
plt.savefig("outputs/optimal_params.png", dpi=200)
plt.close()

# plot 4: drawdown
fig, ax = plt.subplots(figsize=(11, 5))
ax.bar(x - w/2, wf["InWorstDD"], w, label="In-Sample DD", color="steelblue", alpha=0.8)
ax.bar(x + w/2, wf["OutWorstDD"], w, label="OOS DD", color="red", alpha=0.8)
ax.axhline(0, color="black", linewidth=0.8)
ax.set_xticks(x)
ax.set_xticklabels(labels, fontsize=9)
ax.set_title("Max Drawdown Comparison")
ax.set_ylabel("Drawdown (USD)")
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v:,.0f}"))
ax.legend()
ax.grid(True, axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig("outputs/drawdown_comparison.png", dpi=200)
plt.close()

# plot 5: summary table
total_profit = wf["OutProfit"].sum()
worst_dd = wf["OutWorstDD"].min()
roa = total_profit / abs(worst_dd) if worst_dd != 0 else 0
win_windows = (wf["OutProfit"] > 0).sum()
avg_trades = wf["OutTrades"].mean()
decay_profit = wf["OutProfit"].mean() / wf["InProfit"].mean() if wf["InProfit"].mean() != 0 else 0
decay_dd = wf["OutWorstDD"].mean() / wf["InWorstDD"].mean() if wf["InWorstDD"].mean() != 0 else 0

rows = [
    ["Total OOS Profit", f"${total_profit:,.0f}"],
    ["Worst OOS Drawdown", f"${worst_dd:,.0f}"],
    ["Return on Account", f"{roa:.2f}x"],
    ["Profitable Windows", f"{win_windows} / {len(wf)}"],
    ["Avg Trades per Window", f"{avg_trades:.1f}"],
    ["Profit Decay (OOS/IS)", f"{decay_profit:.2f}x"],
    ["DD Decay (OOS/IS)", f"{decay_dd:.2f}x"],
]

fig, ax = plt.subplots(figsize=(7, 4))
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
ax.set_title("OOS Performance Summary - HO", fontsize=11, pad=20)
plt.tight_layout()
plt.savefig("outputs/performance_summary_table.png", dpi=200, bbox_inches="tight")
plt.close()

print("done")
