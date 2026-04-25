"""
Random Walk Tests for TY 10-Year U.S. Treasury Note Futures

This script runs:
1. Variance Ratio Test
2. Push-Response Test

Input:
    TY-5minHLV.csv

Outputs:
    outputs/random_walk_TY_summary.csv
    outputs/variance_ratio_TY.png
    outputs/push_response_TY.png
"""

import math
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# -----------------------------
# 1. Load TY 5-minute data
# -----------------------------
def load_ty_data(file_path: str) -> pd.DataFrame:
    df = pd.read_csv(file_path)

    required_cols = ["Date", "Time", "Close"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    df["datetime"] = pd.to_datetime(
        df["Date"].astype(str) + " " + df["Time"].astype(str),
        errors="coerce"
    )

    df = df.dropna(subset=["datetime", "Close"]).copy()
    df = df.sort_values("datetime").reset_index(drop=True)

    return df


# -----------------------------
# 2. Variance Ratio Test
# -----------------------------
def variance_ratio_test(df: pd.DataFrame, q: int) -> dict:
    """
    Variance Ratio idea:
    If price follows a random walk, then:
        Var(q-period return) ≈ q * Var(1-period return)

    VR(q) > 1: positive serial dependence, trend-following tendency
    VR(q) < 1: negative serial dependence, mean-reversion tendency
    """

    log_price = np.log(df["Close"].astype(float))
    one_period_return = log_price.diff().dropna()
    q_period_return = log_price.diff(q).dropna()

    n = len(one_period_return)

    var_1 = np.var(one_period_return, ddof=1)
    var_q = np.var(q_period_return, ddof=1)

    vr = var_q / (q * var_1)

    # Simple asymptotic z-test under homoskedastic random walk assumption
    # theta(q) = 2(2q - 1)(q - 1) / (3qN)
    theta = 2 * (2 * q - 1) * (q - 1) / (3 * q * n)

    if theta > 0:
        z_stat = (vr - 1) / math.sqrt(theta)
        p_value = math.erfc(abs(z_stat) / math.sqrt(2))
    else:
        z_stat = np.nan
        p_value = np.nan

    return {
        "variance_ratio": vr,
        "vr_z_stat": z_stat,
        "vr_p_value": p_value
    }


# -----------------------------
# 3. Push-Response Test
# -----------------------------
def push_response_test(df: pd.DataFrame, tau: int) -> dict:
    """
    Push:
        price_t - price_{t - tau}

    Response:
        price_{t + tau} - price_t

    If slope > 0:
        Past movement tends to continue -> trend-following

    If slope < 0:
        Past movement tends to reverse -> mean-reversion
    """

    price = df["Close"].astype(float)

    push = price - price.shift(tau)
    response = price.shift(-tau) - price

    temp = pd.DataFrame({
        "push": push,
        "response": response
    }).dropna()

    if len(temp) < 10:
        return {
            "push_response_slope": np.nan,
            "push_response_corr": np.nan,
            "n_obs": len(temp)
        }

    x = temp["push"].values
    y = temp["response"].values

    slope = np.cov(x, y, ddof=1)[0, 1] / np.var(x, ddof=1)
    corr = np.corrcoef(x, y)[0, 1]

    return {
        "push_response_slope": slope,
        "push_response_corr": corr,
        "n_obs": len(temp)
    }


# -----------------------------
# 4. Classification rule
# -----------------------------
def classify_result(vr: float, vr_p: float, pr_slope: float) -> str:
    """
    This is a simple interpretation rule for the report.
    """

    vr_significant = vr_p < 0.05

    if vr > 1 and pr_slope > 0:
        if vr_significant:
            return "trend-following evidence"
        else:
            return "weak trend-following evidence"

    if vr < 1 and pr_slope < 0:
        if vr_significant:
            return "mean-reversion evidence"
        else:
            return "weak mean-reversion evidence"

    return "mixed or weak evidence"


# -----------------------------
# 5. Main analysis
# -----------------------------
def main():
    input_file = "TY-5minHLV.csv"
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)

    df = load_ty_data(input_file)

    # Time scales measured in 5-minute bars
    # Example: 12 bars = 60 minutes; 96 bars = 480 minutes = 8 hours
    scales = [1, 3, 6, 12, 24, 48, 96, 192, 384, 768, 1152]

    results = []

    for q in scales:
        vr_result = variance_ratio_test(df, q)
        pr_result = push_response_test(df, q)

        vr = vr_result["variance_ratio"]
        vr_p = vr_result["vr_p_value"]
        pr_slope = pr_result["push_response_slope"]

        results.append({
            "market": "TY",
            "q_or_tau_5min_bars": q,
            "approx_minutes": q * 5,
            "approx_hours": q * 5 / 60,
            "variance_ratio": vr,
            "vr_z_stat": vr_result["vr_z_stat"],
            "vr_p_value": vr_p,
            "push_response_slope": pr_slope,
            "push_response_corr": pr_result["push_response_corr"],
            "n_obs": pr_result["n_obs"],
            "interpretation": classify_result(vr, vr_p, pr_slope)
        })

    summary = pd.DataFrame(results)

    # Save summary table
    summary_path = output_dir / "random_walk_TY_summary.csv"
    summary.to_csv(summary_path, index=False)

    print("\nRandom Walk Test Summary for TY:")
    print(summary)
    print(f"\nSaved summary to: {summary_path}")

    # -----------------------------
    # Plot 1: Variance Ratio
    # -----------------------------
    plt.figure(figsize=(8, 4))
    plt.plot(
        summary["q_or_tau_5min_bars"],
        summary["variance_ratio"],
        marker="o"
    )
    plt.axhline(1, linestyle="--")
    plt.xlabel("Time scale q, measured in 5-minute bars")
    plt.ylabel("Variance Ratio")
    plt.title("Variance Ratio Test for TY")
    plt.tight_layout()

    vr_plot_path = output_dir / "variance_ratio_TY.png"
    plt.savefig(vr_plot_path, dpi=200)
    plt.close()

    # -----------------------------
    # Plot 2: Push-Response Slope
    # -----------------------------
    plt.figure(figsize=(8, 4))
    plt.plot(
        summary["q_or_tau_5min_bars"],
        summary["push_response_slope"],
        marker="o"
    )
    plt.axhline(0, linestyle="--")
    plt.xlabel("Time scale tau, measured in 5-minute bars")
    plt.ylabel("Push-Response Slope")
    plt.title("Push-Response Test for TY")
    plt.tight_layout()

    pr_plot_path = output_dir / "push_response_TY.png"
    plt.savefig(pr_plot_path, dpi=200)
    plt.close()

    print(f"Saved plot to: {vr_plot_path}")
    print(f"Saved plot to: {pr_plot_path}")


if __name__ == "__main__":
    main()
