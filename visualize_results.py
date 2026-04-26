"""
Visualization for Channel WithDDControl Strategy — Heating Oil (HO)
Walk-Forward Results + Out-of-Sample Equity Curve

Outputs (saved to outputs/):
    1. oos_equity_curve.png         - Out-of-sample equity curve
    2. insample_vs_oos_profit.png   - In-sample vs OOS profit per window
    3. optimal_params.png           - Best ChnLen and StopPct per window
    4. drawdown_comparison.png      - In-sample vs OOS max drawdown
    5. performance_summary_table.png - Key metrics table
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from pathlib import Path

# ── output folder ──────────────────────────────────────────────
out = Path("outputs")
out.mkdir(exist_ok=True)

# ── load data ──────────────────────────────────────────────────
wf = pd.read_csv("walk_forward_4y_update_results.csv")
eq = pd.read_csv("equity_plot.csv")

# parse dates
for col in ["InStart", "InEnd", "OutStart", "OutEnd"]:
    wf[col] = pd.to_datetime(wf[col], dayfirst=True)

eq["datetime"] = pd.to_datetime(
    eq["date"].astype(str) + " " + eq["time"].astype(str),
    dayfirst=True, errors="coerce"
)
eq = eq.dropna(subset=["datetime"]).sort_values("datetime").reset_index(drop=True)

window_labels = [f"W{i+1}\n{r.OutStart.strftime('%Y')}" for i, r in wf.iterrows()]
x = np.arange(len(wf))

# ── color palette ──────────────────────────────────────────────
C_IN  = "#4C72B0"
C_OUT = "#DD8452"
C_EQ  = "#2ca02c"
C_DD  = "#d62728"

# ══════════════════════════════════════════════════════════════
# 1. OOS Equity Curve
# ══════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(eq["datetime"], eq["E"], color=C_EQ, linewidth=0.8)
ax.fill_between(eq["datetime"], eq["E"], alpha=0.15, color=C_EQ)
ax.axhline(eq["E"].iloc[0], linestyle="--", color="gray", linewidth=0.8)
ax.set_title("Out-of-Sample Equity Curve — Channel WithDDControl (HO)", fontsize=13)
ax.set_xlabel("Date")
ax.set_ylabel("Cumulative P&L (USD)")
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))
# mark each walk-forward window boundary
for _, r in wf.iterrows():
    ax.axvline(r["OutStart"], color="gray", linestyle=":", linewidth=0.6, alpha=0.6)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(out / "oos_equity_curve.png", dpi=200)
plt.close()
print("Saved: oos_equity_curve.png")

# ══════════════════════════════════════════════════════════════
# 2. In-Sample vs OOS Profit per Window
# ══════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(11, 5))
w = 0.35
bars_in  = ax.bar(x - w/2, wf["InProfit"],  w, label="In-Sample Profit",  color=C_IN,  alpha=0.85)
bars_out = ax.bar(x + w/2, wf["OutProfit"], w, label="OOS Profit",         color=C_OUT, alpha=0.85)

ax.axhline(0, color="black", linewidth=0.8)
ax.set_xticks(x)
ax.set_xticklabels(window_labels, fontsize=9)
ax.set_title("In-Sample vs Out-of-Sample Net Profit per Walk-Forward Window", fontsize=12)
ax.set_ylabel("Net Profit (USD)")
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v:,.0f}"))
ax.legend()
ax.grid(True, axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig(out / "insample_vs_oos_profit.png", dpi=200)
plt.close()
print("Saved: insample_vs_oos_profit.png")

# ══════════════════════════════════════════════════════════════
# 3. Optimal Parameters per Window
# ══════════════════════════════════════════════════════════════
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 6), sharex=True)

ax1.bar(x, wf["BestLength"], color=C_IN, alpha=0.85)
ax1.set_ylabel("ChnLen (bars)")
ax1.set_title("Optimal Parameters per Walk-Forward Window", fontsize=12)
ax1.grid(True, axis="y", alpha=0.3)
for i, v in enumerate(wf["BestLength"]):
    ax1.text(i, v + 50, str(int(v)), ha="center", fontsize=8)

ax2.bar(x, wf["BestStopPct"] * 100, color=C_OUT, alpha=0.85)
ax2.set_ylabel("StopPct (%)")
ax2.set_xticks(x)
ax2.set_xticklabels(window_labels, fontsize=9)
ax2.grid(True, axis="y", alpha=0.3)
for i, v in enumerate(wf["BestStopPct"]):
    ax2.text(i, v * 100 + 0.1, f"{v*100:.1f}%", ha="center", fontsize=8)

plt.tight_layout()
plt.savefig(out / "optimal_params.png", dpi=200)
plt.close()
print("Saved: optimal_params.png")

# ══════════════════════════════════════════════════════════════
# 4. Drawdown Comparison
# ══════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(11, 5))
ax.bar(x - w/2, wf["InWorstDD"],  w, label="In-Sample Max DD",  color=C_IN,  alpha=0.85)
ax.bar(x + w/2, wf["OutWorstDD"], w, label="OOS Max DD",         color=C_DD,  alpha=0.85)
ax.axhline(0, color="black", linewidth=0.8)
ax.set_xticks(x)
ax.set_xticklabels(window_labels, fontsize=9)
ax.set_title("In-Sample vs Out-of-Sample Max Drawdown per Window", fontsize=12)
ax.set_ylabel("Max Drawdown (USD)")
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v:,.0f}"))
ax.legend()
ax.grid(True, axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig(out / "drawdown_comparison.png", dpi=200)
plt.close()
print("Saved: drawdown_comparison.png")

# ══════════════════════════════════════════════════════════════
# 5. Performance Summary Table
# ══════════════════════════════════════════════════════════════
total_oos_profit = wf["OutProfit"].sum()
total_oos_dd     = wf["OutWorstDD"].min()
roa              = total_oos_profit / abs(total_oos_dd) if total_oos_dd != 0 else 0
win_windows      = (wf["OutProfit"] > 0).sum()
total_windows    = len(wf)
avg_trades       = wf["OutTrades"].mean()
decay_profit     = (wf["OutProfit"].mean() / wf["InProfit"].mean()) if wf["InProfit"].mean() != 0 else 0
decay_dd         = (wf["OutWorstDD"].mean() / wf["InWorstDD"].mean()) if wf["InWorstDD"].mean() != 0 else 0

metrics = [
    ["Total OOS Net Profit",        f"${total_oos_profit:,.0f}"],
    ["Worst OOS Drawdown",          f"${total_oos_dd:,.0f}"],
    ["OOS Return on Account",       f"{roa:.2f}x"],
    ["Profitable Windows",          f"{win_windows} / {total_windows}"],
    ["Avg OOS Trades per Window",   f"{avg_trades:.1f}"],
    ["Profit Decay (OOS/IS)",       f"{decay_profit:.2f}x"],
    ["Drawdown Decay (OOS/IS)",     f"{decay_dd:.2f}x"],
]

fig, ax = plt.subplots(figsize=(7, 4))
ax.axis("off")
tbl = ax.table(
    cellText=metrics,
    colLabels=["Metric", "Value"],
    cellLoc="center",
    loc="center",
    bbox=[0, 0, 1, 1]
)
tbl.auto_set_font_size(False)
tbl.set_fontsize(11)
for (r, c), cell in tbl.get_celld().items():
    if r == 0:
        cell.set_facecolor("#4C72B0")
        cell.set_text_props(color="white", fontweight="bold")
    elif r % 2 == 0:
        cell.set_facecolor("#f0f4ff")
    cell.set_edgecolor("white")

ax.set_title("Overall OOS Performance Summary — HO Channel Strategy",
             fontsize=11, pad=20)
plt.tight_layout()
plt.savefig(out / "performance_summary_table.png", dpi=200, bbox_inches="tight")
plt.close()
print("Saved: performance_summary_table.png")

print("\nAll done! Check the outputs/ folder.")
