import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

tag = "IS48_OOS12_STEP12"
E0 = 100000.0

is_file = f"walk_forward_is_equity_curve_{tag}.csv"
oos_file = f"walk_forward_oos_equity_curve_{tag}.csv"
summary_file = f"walk_forward_quarterly_summary_{tag}.csv"

is_eq = pd.read_csv(is_file)
oos = pd.read_csv(oos_file)
summary = pd.read_csv(summary_file)

# ============================================================
# Clean datetime
# ============================================================
is_eq["datetime"] = pd.to_datetime(
    is_eq["date"].astype(str) + " " + is_eq["time"].astype(str),
    format="%m/%d/%Y %H:%M",
    errors="coerce"

)

oos["datetime"] = pd.to_datetime(

    oos["date"].astype(str) + " " + oos["time"].astype(str),

    format="%m/%d/%Y %H:%M",

    errors="coerce"

)

summary["InStart"] = pd.to_datetime(summary["InStart"], errors="coerce")
summary["InEnd"] = pd.to_datetime(summary["InEnd"], errors="coerce")
summary["OutStart"] = pd.to_datetime(summary["OutStart"], errors="coerce")
summary["OutEnd"] = pd.to_datetime(summary["OutEnd"], errors="coerce")
print("IS columns:")

print(is_eq.columns.tolist())

print("OOS columns:")

print(oos.columns.tolist())

print("Summary columns:")

print(summary.columns.tolist())
is_eq = is_eq.dropna(subset=["datetime"]).sort_values("datetime")

oos = oos.dropna(subset=["datetime"]).sort_values("datetime")

summary = summary.sort_values("OutStart").reset_index(drop=True)

# numeric

for col in ["barPnL", "isEquity", "tradeSize", "position"]:

    is_eq[col] = pd.to_numeric(is_eq[col], errors="coerce").fillna(0)

for col in ["barPnL", "oosEquity", "tradeSize", "position"]:

    oos[col] = pd.to_numeric(oos[col], errors="coerce").fillna(0)

for col in ["InProfit", "OutProfit", "InWorstDD", "OutWorstDD", "InStd", "OutStd", "InTrades", "OutTrades"]:

    summary[col] = pd.to_numeric(summary[col], errors="coerce")

# ============================================================

# 1. Compare summary statistics by WF window

# ============================================================

summary["InProfit_DD"] = summary["InProfit"] / (summary["InWorstDD"].abs() + 1.0)

summary["OutProfit_DD"] = summary["OutProfit"] / (summary["OutWorstDD"].abs() + 1.0)

summary["OutPositive"] = summary["OutProfit"] > 0

summary["Efficiency_Out_In"] = summary["OutProfit"] / summary["InProfit"].replace(0, np.nan)

compare_stats = pd.DataFrame({

    "Metric": [

        "Number of WF Windows",

        "Mean InProfit",

        "Mean OutProfit",

        "Median InProfit",

        "Median OutProfit",

        "Std InProfit",

        "Std OutProfit",

        "Out Positive Fraction",

        "Corr InProfit vs OutProfit",

        "Mean InWorstDD",

        "Mean OutWorstDD",

        "Mean InProfit/DD",

        "Mean OutProfit/DD",

        "Mean InTrades",

        "Mean OutTrades",

        "Mean Efficiency Out/In",

        "Median Efficiency Out/In",

    ],

    "Value": [

        len(summary),

        summary["InProfit"].mean(),

        summary["OutProfit"].mean(),

        summary["InProfit"].median(),

        summary["OutProfit"].median(),

        summary["InProfit"].std(),

        summary["OutProfit"].std(),

        summary["OutPositive"].mean(),

        summary["InProfit"].corr(summary["OutProfit"]),

        summary["InWorstDD"].mean(),

        summary["OutWorstDD"].mean(),

        summary["InProfit_DD"].mean(),

        summary["OutProfit_DD"].mean(),

        summary["InTrades"].mean(),

        summary["OutTrades"].mean(),

        summary["Efficiency_Out_In"].mean(),

        summary["Efficiency_Out_In"].median(),

    ]

})

print("\n================ IS vs OOS Window Statistics ================\n")

print(compare_stats.to_string(index=False))

compare_stats.to_csv(f"is_vs_oos_stats_{tag}.csv", index=False)

# ============================================================

# 2. Plot InProfit vs OutProfit by window

# ============================================================

plt.figure(figsize=(14, 5))

plt.plot(summary["OutStart"], summary["InProfit"], label="In-sample Profit")

plt.plot(summary["OutStart"], summary["OutProfit"], label="Out-of-sample Profit")

plt.axhline(0, linestyle="--")

plt.title(f"In-Sample vs Out-of-Sample Profit by Window - {tag}")

plt.xlabel("OOS Start Date")

plt.ylabel("Profit")

plt.legend()

plt.grid(True)

plt.tight_layout()

plt.show()

# ============================================================

# 3. Scatter: InProfit vs OutProfit

# ============================================================

plt.figure(figsize=(7, 6))

plt.scatter(summary["InProfit"], summary["OutProfit"], alpha=0.7)

plt.axhline(0, linestyle="--")

plt.axvline(0, linestyle="--")

plt.title(f"InProfit vs OutProfit - {tag}")

plt.xlabel("In-sample Profit")

plt.ylabel("Out-of-sample Profit")

plt.grid(True)

plt.tight_layout()

plt.show()

# ============================================================

# 4. Compare InProfit_DD vs OutProfit_DD

# ============================================================

plt.figure(figsize=(14, 5))

plt.plot(summary["OutStart"], summary["InProfit_DD"], label="IS Profit/DD")

plt.plot(summary["OutStart"], summary["OutProfit_DD"], label="OOS Profit/DD")

plt.axhline(0, linestyle="--")

plt.title(f"IS vs OOS Profit/Drawdown by Window - {tag}")

plt.xlabel("OOS Start Date")

plt.ylabel("Profit / Drawdown")

plt.legend()

plt.grid(True)

plt.tight_layout()

plt.show()

# ============================================================

# 5. OOS continuous equity curve

# ============================================================

oos["cummax"] = oos["oosEquity"].cummax()

oos["drawdown"] = oos["oosEquity"] - oos["cummax"]

plt.figure(figsize=(14, 6))

plt.plot(oos["datetime"], oos["oosEquity"])

plt.title(f"Continuous OOS Equity Curve - {tag}")

plt.xlabel("Date")

plt.ylabel("OOS Equity")

plt.grid(True)

plt.tight_layout()

plt.show()

plt.figure(figsize=(14, 5))

plt.plot(oos["datetime"], oos["drawdown"])

plt.title(f"Continuous OOS Drawdown - {tag}")

plt.xlabel("Date")

plt.ylabel("Drawdown")

plt.grid(True)

plt.tight_layout()

plt.show()

# ============================================================

# 6. Example IS equity curves

# IS equity curves are overlapping and each starts from E0.

# So don't treat them as one continuous curve.

# ============================================================

unique_windows = (

    is_eq[["InStart", "InEnd", "OutStart", "OutEnd"]]

    .drop_duplicates()

    .head(5)

)

plt.figure(figsize=(14, 6))

for _, row in unique_windows.iterrows():

    mask = (

        (is_eq["InStart"] == row["InStart"]) &

        (is_eq["InEnd"] == row["InEnd"]) &

        (is_eq["OutStart"] == row["OutStart"]) &

        (is_eq["OutEnd"] == row["OutEnd"])

    )

    temp = is_eq.loc[mask].copy()

    label = f'{row["InStart"]} to {row["InEnd"]}'

    plt.plot(temp["datetime"], temp["isEquity"], linewidth=1, label=label)

plt.title(f"Example In-Sample Equity Curves - {tag}")

plt.xlabel("Date")

plt.ylabel("IS Equity")

plt.legend()

plt.grid(True)

plt.tight_layout()

plt.show()