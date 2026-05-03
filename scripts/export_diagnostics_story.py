from __future__ import annotations

import argparse
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mafn_engine import (
    COLUMBIA_CORE,
    COLUMBIA_NAVY,
    COLUMBIA_RED,
    COLUMBIA_WARM,
    apply_columbia_theme,
    build_pair_story,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rerun notebook 04 and export exact VR / push-response figures.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "results" / "diagnostics",
        help="Directory for executed notebooks and exported figures.",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=PROJECT_ROOT / "data",
        help="Project data directory.",
    )
    parser.add_argument(
        "--skip-notebook",
        action="store_true",
        help="Skip executing notebook 04 and only export the diagnostics figures.",
    )
    return parser.parse_args()


def _plot_pr(ax: plt.Axes, pr_diag: dict[str, object] | None, title: str) -> None:
    if not pr_diag:
        ax.text(0.5, 0.5, "No push-response data", ha="center", va="center")
        ax.set_title(title)
        return
    x = np.asarray(pr_diag["bin_centre"], dtype=float)
    y = np.asarray(pr_diag["bin_mean"], dtype=float)
    se = np.asarray(pr_diag["bin_se"], dtype=float)
    ax.axhline(0.0, color=COLUMBIA_NAVY, lw=1.0, alpha=0.8)
    ax.axvline(0.0, color=COLUMBIA_NAVY, lw=1.0, alpha=0.8)
    ax.plot(x, y, color=COLUMBIA_CORE, marker="o")
    ax.fill_between(x, y - se, y + se, color=COLUMBIA_WARM, alpha=0.18)
    ax.set_title(f"{title} | rho={float(pr_diag['spearman_rho']):+.3f}")
    ax.set_xlabel("push")
    ax.set_ylabel("average response")


def _save_pair_panel(pair_story: dict[str, object], output_dir: Path, *, panel_name: str, use_showcase: bool) -> Path:
    stories = pair_story["stories"]
    tickers = pair_story["tickers"]
    fig, axes = plt.subplots(len(tickers), 3, figsize=(18, 6 * len(tickers)))
    if len(tickers) == 1:
        axes = np.asarray([axes])

    for row, ticker in enumerate(tickers):
        story = stories[ticker]
        professor_bundle = story["diagnostics"]["professor_bundle"]
        vr_curve_df = professor_bundle["vr_curve_df"]
        ax0, ax1, ax2 = axes[row]
        ax0.plot(vr_curve_df["q"], vr_curve_df["VR"], color=COLUMBIA_CORE)
        ax0.axhline(1.0, color=COLUMBIA_RED, ls="--", lw=1.0)
        ax0.axvline(professor_bundle["short_tau"], color=COLUMBIA_WARM, ls=":", lw=1.2)
        ax0.axvline(professor_bundle["reference_tau"], color=COLUMBIA_NAVY, ls="--", lw=1.2)
        if use_showcase and int(professor_bundle["showcase_tau"]) != int(professor_bundle["reference_tau"]):
            ax0.axvline(professor_bundle["showcase_tau"], color=COLUMBIA_RED, ls="-.", lw=1.2)
        ax0.set_title(f"{ticker}: Variance Ratio vs q")
        ax0.set_xlabel("q (bars)")
        ax0.set_ylabel("VR(q)")
        labels = [
            f"short={professor_bundle['short_scale']}",
            f"ref={professor_bundle['reference_scale']}",
        ]
        if use_showcase and int(professor_bundle["showcase_tau"]) != int(professor_bundle["reference_tau"]):
            labels.append(f"showcase={professor_bundle['showcase_scale']}")
        ax0.text(0.01, 0.05, "\n".join(labels), transform=ax0.transAxes, color=COLUMBIA_NAVY)

        _plot_pr(ax1, professor_bundle["short_pr"], f"{ticker}: Short-Horizon PR")
        pr_diag = professor_bundle["reference_pr"]
        pr_title = f"{ticker}: Reference-Horizon PR"
        if use_showcase and int(professor_bundle["showcase_tau"]) != int(professor_bundle["reference_tau"]) and professor_bundle["showcase_pr"]:
            pr_diag = professor_bundle["showcase_pr"]
            pr_title = f"{ticker}: Showcase-Horizon PR"
        _plot_pr(ax2, pr_diag, pr_title)

    plt.tight_layout()
    out_path = output_dir / panel_name
    fig.savefig(out_path, dpi=220)
    plt.close(fig)
    return out_path


def _save_single_market_exports(pair_story: dict[str, object], output_dir: Path) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for ticker in pair_story["tickers"]:
        story = pair_story["stories"][ticker]
        professor_bundle = story["diagnostics"]["professor_bundle"]
        vr_curve_df = professor_bundle["vr_curve_df"].copy()
        vr_curve_df.to_csv(output_dir / f"{ticker}_vr_curve.csv", index=False)

        for label, pr_key in [
            ("short", "short_pr"),
            ("reference", "reference_pr"),
            ("showcase", "showcase_pr"),
        ]:
            pr_diag = professor_bundle.get(pr_key)
            if not pr_diag:
                continue
            df = pd.DataFrame(
                {
                    "bin_centre": pr_diag["bin_centre"],
                    "bin_mean": pr_diag["bin_mean"],
                    "bin_se": pr_diag["bin_se"],
                    "bin_count": pr_diag["bin_count"],
                }
            )
            df.to_csv(output_dir / f"{ticker}_{label}_pr.csv", index=False)
            rows.append(
                {
                    "Ticker": ticker,
                    "Kind": label,
                    "TauBars": pr_diag["push_bars"],
                    "TauScale": pr_diag["push_scale"],
                    "Rho": pr_diag["spearman_rho"],
                    "PValue": pr_diag["spearman_p"],
                    "Pattern": pr_diag["pattern"],
                }
            )
    out_df = pd.DataFrame(rows)
    out_df.to_csv(output_dir / "push_response_metadata.csv", index=False)
    return out_df


def execute_notebook(input_path: Path, output_path: Path) -> None:
    with input_path.open("r", encoding="utf-8") as fh:
        nb = nbformat.read(fh, as_version=4)
    ep = ExecutePreprocessor(timeout=0, kernel_name="python3")
    ep.preprocess(nb, {"metadata": {"path": str(input_path.parent)}})
    with output_path.open("w", encoding="utf-8") as fh:
        nbformat.write(nb, fh)


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    apply_columbia_theme()

    if not args.skip_notebook:
        notebook_in = PROJECT_ROOT / "notebooks" / "04_Two_Market_Diagnostics_Story.ipynb"
        notebook_out = args.output_dir / "04_Two_Market_Diagnostics_Story.executed.ipynb"
        execute_notebook(notebook_in, notebook_out)

    pair_story = build_pair_story(
        tickers=("TY", "BTC"),
        data_dir=str(args.data_dir),
        quick=True,
        walkforward_mode="tf",
        include_walkforward=False,
        include_surface=False,
        verbose=False,
    )

    _save_pair_panel(pair_story, args.output_dir, panel_name="two_market_diagnostics_reference.png", use_showcase=False)
    _save_pair_panel(pair_story, args.output_dir, panel_name="two_market_diagnostics_showcase.png", use_showcase=True)
    _save_single_market_exports(pair_story, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
