#!/usr/bin/env python3
"""
Run Variance Ratio and Push-Response tests on 5-minute TY close data.

Example:
python3 run_efficiency_tests.py \
  --input "/Users/maggiezhu/Downloads/TY-5minHLV.csv" \
  --output-dir "outputs/ty_tests_v1"
"""

from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np


@dataclass
class VarianceRatioResult:
    q_bars: int
    q_minutes: int
    variance_ratio: float
    z_stat: float
    p_value: float


@dataclass
class PushResponseResult:
    q_bars: int
    q_minutes: int
    slope: float
    corr: float
    n_obs: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute TY random walk diagnostics.")
    parser.add_argument("--input", required=True, help="CSV path with a Close column.")
    parser.add_argument(
        "--output-dir",
        default="outputs/ty_tests_v1",
        help="Directory for CSV and PNG outputs.",
    )
    parser.add_argument(
        "--q-bars",
        default="1,3,6,12,24,48,96,192,384,768,1152",
        help="Comma-separated horizons measured in 5-minute bars.",
    )
    return parser.parse_args()


def load_close_prices(csv_path: Path) -> np.ndarray:
    values: list[float] = []
    with csv_path.open("r", newline="") as handle:
        reader = csv.DictReader(handle)
        if "Close" not in (reader.fieldnames or []):
            raise ValueError("Input CSV must include a Close column.")
        for row in reader:
            raw = row.get("Close", "")
            try:
                c = float(raw)
            except (TypeError, ValueError):
                continue
            if c > 0:
                values.append(c)
    if len(values) < 50:
        raise ValueError("Not enough valid close data points.")
    return np.array(values, dtype=float)


def compute_variance_ratio(log_price: np.ndarray, q: int) -> tuple[float, float, float]:
    r1 = np.diff(log_price)
    rq = log_price[q:] - log_price[:-q]
    if len(r1) < 2 or len(rq) < 2:
        return np.nan, np.nan, np.nan

    var_1 = float(np.var(r1, ddof=1))
    var_q = float(np.var(rq, ddof=1))
    vr = var_q / (q * var_1) if var_1 > 0 else np.nan

    n = len(r1)
    theta = 2 * (2 * q - 1) * (q - 1) / (3 * q * n)
    if theta > 0 and np.isfinite(vr):
        z = (vr - 1.0) / np.sqrt(theta)
        p = float(math.erfc(abs(z) / np.sqrt(2)))
    else:
        z = np.nan
        p = np.nan
    return float(vr), float(z), float(p)


def variance_ratio_results(log_price: np.ndarray, q_values: Iterable[int]) -> list[VarianceRatioResult]:
    out: list[VarianceRatioResult] = []
    for q in q_values:
        if q < 1 or q >= len(log_price):
            continue
        vr, z, p = compute_variance_ratio(log_price, q)
        out.append(VarianceRatioResult(q, q * 5, vr, z, p))
    return out


def push_response_results(close: np.ndarray, q_values: Iterable[int]) -> list[PushResponseResult]:
    out: list[PushResponseResult] = []
    n = len(close)
    for q in q_values:
        if q < 1 or 2 * q >= n:
            continue
        push = close[q:] - close[:-q]
        response = close[2 * q :] - close[q:-q]
        m = min(len(push), len(response))
        x = push[:m]
        y = response[:m]
        valid = np.isfinite(x) & np.isfinite(y)
        x = x[valid]
        y = y[valid]
        if len(x) < 10:
            out.append(PushResponseResult(q, q * 5, np.nan, np.nan, len(x)))
            continue

        var_x = float(np.var(x, ddof=1))
        cov_xy = float(np.cov(x, y, ddof=1)[0, 1])
        slope = cov_xy / var_x if var_x > 0 else np.nan
        corr = float(np.corrcoef(x, y)[0, 1])
        out.append(PushResponseResult(q, q * 5, float(slope), float(corr), len(x)))
    return out


def write_variance_ratio_csv(results: list[VarianceRatioResult], path: Path) -> None:
    with path.open("w", newline="") as handle:
        w = csv.writer(handle)
        w.writerow(["q_bars", "q_minutes", "variance_ratio", "z_stat", "p_value"])
        for r in results:
            w.writerow([r.q_bars, r.q_minutes, f"{r.variance_ratio:.10f}", f"{r.z_stat:.6f}", f"{r.p_value:.10f}"])


def write_push_response_csv(results: list[PushResponseResult], path: Path) -> None:
    with path.open("w", newline="") as handle:
        w = csv.writer(handle)
        w.writerow(["q_bars", "q_minutes", "push_response_slope", "push_response_corr", "n_obs"])
        for r in results:
            w.writerow([r.q_bars, r.q_minutes, f"{r.slope:.10f}", f"{r.corr:.10f}", r.n_obs])


def write_summary(out_dir: Path, input_path: Path, n_close: int, vr: list[VarianceRatioResult], pr: list[PushResponseResult]) -> None:
    lines = [
        f"input_csv: {input_path}",
        f"n_close: {n_close}",
        f"horizons_tested: {len(vr)}",
        f"vr_lt_1_count: {sum(1 for x in vr if x.variance_ratio < 1)}",
        f"vr_gt_1_count: {sum(1 for x in vr if x.variance_ratio > 1)}",
        f"push_slope_pos_count: {sum(1 for x in pr if x.slope > 0)}",
        f"push_slope_neg_count: {sum(1 for x in pr if x.slope < 0)}",
    ]
    (out_dir / "run_summary.txt").write_text("\n".join(lines), encoding="utf-8")


def make_plots(vr: list[VarianceRatioResult], pr: list[PushResponseResult], out_dir: Path) -> None:
    import matplotlib.pyplot as plt

    q = [x.q_bars for x in vr]
    vr_vals = [x.variance_ratio for x in vr]
    z_vals = [x.z_stat for x in vr]

    plt.figure(figsize=(8, 4))
    plt.plot(q, vr_vals, marker="o")
    plt.axhline(1.0, linestyle="--")
    plt.xlabel("Time scale q, measured in 5-minute bars")
    plt.ylabel("Variance Ratio")
    plt.title("Variance Ratio Test for TY")
    plt.tight_layout()
    plt.savefig(out_dir / "variance_ratio_curve.png", dpi=200)
    plt.close()

    plt.figure(figsize=(8, 4))
    plt.plot(q, z_vals, marker="o")
    plt.axhline(0.0, linestyle="--")
    plt.axhline(1.96, linestyle=":")
    plt.axhline(-1.96, linestyle=":")
    plt.xlabel("Time scale q, measured in 5-minute bars")
    plt.ylabel("VR z-stat")
    plt.title("Variance Ratio z-stat for TY")
    plt.tight_layout()
    plt.savefig(out_dir / "variance_ratio_zstat.png", dpi=200)
    plt.close()

    q2 = [x.q_bars for x in pr]
    slopes = [x.slope for x in pr]
    corr = [x.corr for x in pr]

    plt.figure(figsize=(8, 4))
    plt.plot(q2, slopes, marker="o")
    plt.axhline(0.0, linestyle="--")
    plt.xlabel("Time scale tau, measured in 5-minute bars")
    plt.ylabel("Push-Response Slope")
    plt.title("Push-Response Test for TY")
    plt.tight_layout()
    plt.savefig(out_dir / "push_response_beta.png", dpi=200)
    plt.close()

    plt.figure(figsize=(8, 4))
    plt.plot(q2, corr, marker="o")
    plt.axhline(0.0, linestyle="--")
    plt.xlabel("Time scale tau, measured in 5-minute bars")
    plt.ylabel("Push-Response Correlation")
    plt.title("Push-Response Correlation for TY")
    plt.tight_layout()
    plt.savefig(out_dir / "push_response_spread.png", dpi=200)
    plt.close()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    q_values = sorted(set(int(x.strip()) for x in args.q_bars.split(",") if x.strip()))

    close = load_close_prices(input_path)
    log_price = np.log(close)

    vr = variance_ratio_results(log_price, q_values)
    pr = push_response_results(close, q_values)

    write_variance_ratio_csv(vr, output_dir / "variance_ratio_results.csv")
    write_push_response_csv(pr, output_dir / "push_response_results.csv")
    write_summary(output_dir, input_path, len(close), vr, pr)

    try:
        make_plots(vr, pr, output_dir)
    except ModuleNotFoundError as exc:
        (output_dir / "plot_warning.txt").write_text(
            f"Plotting skipped: {exc}\nInstall matplotlib to enable PNG output.\n",
            encoding="utf-8",
        )

    print(f"Completed. Outputs written to: {output_dir}")


if __name__ == "__main__":
    main()
