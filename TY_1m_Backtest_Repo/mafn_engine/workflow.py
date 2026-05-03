from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from .config import default_tf_grid, get_market, infer_bar_minutes_from_index, professor_reference_tau
from .diagnostics import load_ohlc, prepare_analysis_frame, run_diagnostics, validate_ohlc
from .metrics import performance_from_ledger, split_metric_sections
from .strategies import run_backtest
from .walkforward import select_modal_configuration, walk_forward, walk_forward_surface


def _nearest_grid_value(values: np.ndarray, target: float, *, as_int: bool) -> float | int:
    arr = np.asarray(values, dtype=float)
    if len(arr) == 0:
        raise ValueError("Grid values cannot be empty.")
    idx = int(np.abs(arr - float(target)).argmin())
    value = float(arr[idx])
    return int(round(value)) if as_int else value


def _extract_vr_marker(vr_curve_df: pd.DataFrame, q: int) -> dict[str, object]:
    if vr_curve_df is None or len(vr_curve_df) == 0:
        return {"q": int(q), "VR": np.nan, "Z2": np.nan, "p2": np.nan, "time_scale": "n/a"}
    curve = vr_curve_df.copy()
    curve["distance"] = (curve["q"].astype(int) - int(q)).abs()
    row = curve.sort_values(["distance", "q"]).iloc[0]
    return {
        "q": int(row["q"]),
        "VR": float(row["VR"]),
        "Z2": float(row["Z2"]) if np.isfinite(row["Z2"]) else np.nan,
        "p2": float(row["p2"]) if np.isfinite(row["p2"]) else np.nan,
        "time_scale": str(row["time_scale"]),
    }


def _extract_pr_marker(diagram: dict[str, object] | None) -> dict[str, object]:
    if not diagram:
        return {
            "push_bars": np.nan,
            "push_scale": "n/a",
            "rho": np.nan,
            "p_value": np.nan,
            "pattern": "n/a",
        }
    return {
        "push_bars": int(diagram["push_bars"]),
        "push_scale": str(diagram["push_scale"]),
        "rho": float(diagram["spearman_rho"]),
        "p_value": float(diagram["spearman_p"]),
        "pattern": str(diagram["pattern"]),
    }


def _extract_professor_vr_shape(
    vr_curve_df: pd.DataFrame,
    short_tau: int,
    reference_tau: int,
) -> dict[str, dict[str, object] | float | bool]:
    curve = vr_curve_df.sort_values("q").reset_index(drop=True)
    short_row = _extract_vr_marker(curve, short_tau)
    reference_row = _extract_vr_marker(curve, reference_tau)
    terminal = curve.iloc[-1]
    mid_curve = curve[
        (curve["q"].astype(int) >= int(short_row["q"]))
        & (curve["q"].astype(int) <= int(reference_row["q"]))
    ]
    if len(mid_curve) == 0:
        mid_curve = curve[curve["q"].astype(int) >= int(short_row["q"])]
    trough = mid_curve.loc[mid_curve["VR"].idxmin()] if len(mid_curve) else curve.loc[curve["VR"].idxmin()]

    late_curve = curve[curve["q"].astype(int) >= int(trough["q"])].copy()
    late_slope = (
        float(np.polyfit(np.log(late_curve["q"].astype(float)), late_curve["VR"].astype(float), 1)[0])
        if len(late_curve) > 1
        else np.nan
    )
    return {
        "short": short_row,
        "trough": {
            "q": int(trough["q"]),
            "VR": float(trough["VR"]),
            "Z2": float(trough["Z2"]) if np.isfinite(trough["Z2"]) else np.nan,
            "p2": float(trough["p2"]) if np.isfinite(trough["p2"]) else np.nan,
            "time_scale": str(trough["time_scale"]),
        },
        "reference": reference_row,
        "terminal": {
            "q": int(terminal["q"]),
            "VR": float(terminal["VR"]),
            "Z2": float(terminal["Z2"]) if np.isfinite(terminal["Z2"]) else np.nan,
            "p2": float(terminal["p2"]) if np.isfinite(terminal["p2"]) else np.nan,
            "time_scale": str(terminal["time_scale"]),
        },
        "recovery_to_reference": float(reference_row["VR"] - float(trough["VR"])),
        "recovery_to_terminal": float(float(terminal["VR"]) - float(trough["VR"])),
        "late_slope": late_slope,
        "late_recovery": bool((reference_row["VR"] - float(trough["VR"])) > 0.02 or late_slope > 0.01),
    }


def choose_tf_story_configuration(
    ticker: str,
    tf_grid: dict[str, np.ndarray] | None = None,
    params_df: pd.DataFrame | None = None,
    bar_minutes: int = 5,
) -> dict[str, object]:
    tf_grid = default_tf_grid(ticker, quick=True, bar_minutes=bar_minutes) if tf_grid is None else tf_grid
    modal = select_modal_configuration(params_df if params_df is not None else pd.DataFrame())
    if modal and str(modal.get("family", "")).lower() == "tf":
        return {"family": "tf", "L": int(modal["L"]), "S": float(modal["S"])}

    l_values = np.asarray(tf_grid.get("L", []), dtype=int)
    s_values = np.asarray(tf_grid.get("S", []), dtype=float)
    target_l = professor_reference_tau(ticker, bar_minutes=bar_minutes)
    target_s = 0.02 if ticker.upper() == "TY" else 0.03
    return {
        "family": "tf",
        "L": _nearest_grid_value(l_values, target_l, as_int=True),
        "S": _nearest_grid_value(s_values, target_s, as_int=False),
    }


def build_market_story_rows(
    ticker: str,
    diagnostics_bundle: dict[str, object],
    tf_config: dict[str, object] | None = None,
    wf_bundle: dict[str, object] | None = None,
    oos_metrics: dict[str, float] | None = None,
    full_sample_metrics: dict[str, float] | None = None,
) -> dict[str, dict[str, object]]:
    spec = get_market(ticker)
    trend_profile = diagnostics_bundle["trend_profile"]
    professor_bundle = diagnostics_bundle["professor_bundle"]
    vr_shape = _extract_professor_vr_shape(
        professor_bundle["vr_curve_df"],
        int(professor_bundle["short_tau"]),
        int(professor_bundle["reference_tau"]),
    )

    short_vr = vr_shape["short"]
    reference_vr = vr_shape["reference"]
    trough_vr = vr_shape["trough"]
    terminal_vr = vr_shape["terminal"]
    short_pr = _extract_pr_marker(professor_bundle["short_pr"])
    reference_pr = _extract_pr_marker(professor_bundle["reference_pr"])

    diag_row = {
        "Ticker": spec.ticker,
        "Market": spec.name,
        "Short Horizon": short_vr["time_scale"],
        "Reference Horizon": reference_vr["time_scale"],
        "Short VR": short_vr["VR"],
        "VR Trough": trough_vr["VR"],
        "VR Trough Scale": trough_vr["time_scale"],
        "Reference VR": reference_vr["VR"],
        "Terminal VR": terminal_vr["VR"],
        "VR Recovery to Reference": vr_shape["recovery_to_reference"],
        "VR Recovery to End": vr_shape["recovery_to_terminal"],
        "Short PR Rho": short_pr["rho"],
        "Reference PR Rho": reference_pr["rho"],
        "TF Bias": trend_profile["tf_speed_bias"],
        "Peak VR Scale": trend_profile["peak_vr_scale"],
        "Peak PR Scale": trend_profile["peak_pr_scale"],
        "Narrative Focus": "Delayed trend-following" if spec.ticker == "TY" else "Earlier trend-following",
    }

    if wf_bundle is not None and len(wf_bundle.get("params", pd.DataFrame())):
        dominant_l = float(wf_bundle["params"]["L"].median()) if "L" in wf_bundle["params"] else np.nan
        n_periods = int(len(wf_bundle["params"]))
    else:
        dominant_l = np.nan
        n_periods = 0

    strategy_row = {
        "Ticker": spec.ticker,
        "Story Family": "tf",
        "Modal L": int(tf_config["L"]) if tf_config else np.nan,
        "Modal S": float(tf_config["S"]) if tf_config else np.nan,
        "Median WF L": dominant_l,
        "WF Periods": n_periods,
        "OOS Profit": float(oos_metrics["Total Profit"]) if oos_metrics else np.nan,
        "OOS MaxDD": float(oos_metrics["Max Drawdown $"]) if oos_metrics else np.nan,
        "OOS RoA": float(oos_metrics["Return on Account"]) if oos_metrics else np.nan,
        "OOS Sharpe": float(oos_metrics["Sharpe Ratio"]) if oos_metrics else np.nan,
        "Full Profit": float(full_sample_metrics["Total Profit"]) if full_sample_metrics else np.nan,
        "Full MaxDD": float(full_sample_metrics["Max Drawdown $"]) if full_sample_metrics else np.nan,
        "Full RoA": float(full_sample_metrics["Return on Account"]) if full_sample_metrics else np.nan,
        "Full Sharpe": float(full_sample_metrics["Sharpe Ratio"]) if full_sample_metrics else np.nan,
    }
    return {"diagnostics": diag_row, "strategy": strategy_row}


def build_market_narrative(
    ticker: str,
    diagnostics_bundle: dict[str, object],
    tf_config: dict[str, object] | None = None,
) -> list[str]:
    spec = get_market(ticker)
    trend_profile = diagnostics_bundle["trend_profile"]
    professor_bundle = diagnostics_bundle["professor_bundle"]
    vr_shape = _extract_professor_vr_shape(
        professor_bundle["vr_curve_df"],
        int(professor_bundle["short_tau"]),
        int(professor_bundle["reference_tau"]),
    )

    short_vr = vr_shape["short"]
    trough_vr = vr_shape["trough"]
    reference_vr = vr_shape["reference"]
    terminal_vr = vr_shape["terminal"]
    short_pr = _extract_pr_marker(professor_bundle["short_pr"])
    reference_pr = _extract_pr_marker(professor_bundle["reference_pr"])

    lines: list[str] = []
    if spec.ticker == "TY":
        lines.append(
            "Treasury futures should be presented as short-horizon mean-reverting or mixed, but longer-horizon trend-following."
        )
        if float(vr_shape["recovery_to_reference"]) > 0.02:
            lines.append(
                f"The variance-ratio curve does not need to jump above 1 immediately. The key signal is that it first dips from "
                f"{short_vr['VR']:.3f} at {short_vr['time_scale']} to a trough near {trough_vr['VR']:.3f} at {trough_vr['time_scale']}, "
                f"then recovers toward {reference_vr['VR']:.3f} by {reference_vr['time_scale']} and {terminal_vr['VR']:.3f} by {terminal_vr['time_scale']}."
            )
        else:
            lines.append(
                f"The variance-ratio curve does not need to jump above 1 immediately. The key signal is that it first dips from "
                f"{short_vr['VR']:.3f} at {short_vr['time_scale']} to {reference_vr['VR']:.3f} by {reference_vr['time_scale']}; "
                "on the full sample we care about whether the long-horizon segment bends upward or flattens relative to that earlier decline."
            )
        lines.append(
            "On the full sample, we still care about the late-horizon recovery shape rather than demanding that variance ratio exceed 1 at the first few horizons."
        )
        lines.append(
            f"The professor reference horizon is about one month at {int(professor_bundle['reference_tau'])} bars "
            f"({professor_bundle['reference_scale']}), where the push-response shape should look more trend-consistent "
            f"(rho={reference_pr['rho']:+.3f}) than it does at the short horizon (rho={short_pr['rho']:+.3f})."
        )
        lines.append(
            "That is the narrative to keep in the write-up: macro and rate-consensus changes diffuse slowly, so the trend-following property emerges only at larger holding periods."
        )
    else:
        lines.append(
            "Bitcoin should be presented as a clearer, faster trend-following market than Treasuries."
        )
        lines.append(
            f"Here the variance-ratio story becomes supportive earlier, with the professor reference horizon at "
            f"{int(professor_bundle['reference_tau'])} bars ({professor_bundle['reference_scale']})."
        )
        lines.append(
            f"The push-response diagram is expected to look more obviously trend-following around that horizon "
            f"(rho={reference_pr['rho']:+.3f}), which justifies a shorter and more reactive TF implementation than TY."
        )

    if tf_config is not None:
        lines.append(
            f"The trend-following backtest layer should therefore emphasize channel lookbacks around L={int(tf_config['L'])} bars "
            f"with a stop fraction near S={float(tf_config['S']):.3f}."
        )

    lines.append(str(trend_profile["narrative"]))
    return lines


def build_market_story(
    ticker: str,
    *,
    data_dir: str | None = None,
    data: pd.DataFrame | None = None,
    bar_minutes: int | None = None,
    quick: bool = True,
    walkforward_mode: str = "tf",
    include_walkforward: bool = True,
    include_surface: bool = False,
    tf_grid: dict[str, np.ndarray] | None = None,
    T_years: int = 4,
    tau_quarters: int = 1,
    tau_unit: str = "quarters",
    surface_T_values: Sequence[int] | None = None,
    surface_tau_values: Sequence[int] | None = None,
    verbose: bool = False,
    round_turn_cost: float | None = None,
    cost_multiplier: float = 1.0,
) -> dict[str, object]:
    spec = get_market(ticker)
    if data is None and data_dir is None:
        raise ValueError("Either data or data_dir must be supplied to build_market_story.")

    full_df = (
        data.copy()
        if data is not None
        else load_ohlc(
            str(data_dir),
            spec.ticker,
            fallback_synthetic=False,
            bar_minutes=bar_minutes,
        )
    )
    bar_minutes = infer_bar_minutes_from_index(full_df.index)
    validation = validate_ohlc(full_df)
    analysis_df = prepare_analysis_frame(full_df, spec.ticker)
    diagnostics_bundle = run_diagnostics(analysis_df, spec.ticker)

    if tf_grid is None:
        tf_grid = default_tf_grid(spec.ticker, quick=quick, bar_minutes=bar_minutes)

    wf_bundle: dict[str, object] | None = None
    surface_df: pd.DataFrame | None = None
    oos_metrics: dict[str, float] | None = None
    full_sample_metrics: dict[str, float] | None = None

    if include_walkforward:
        wf_bundle = walk_forward(
            analysis_df,
            spec.ticker,
            mode=walkforward_mode,
            tf_grid=tf_grid,
            T_years=T_years,
            tau_quarters=tau_quarters,
            tau_unit=tau_unit,
            quick=quick,
            verbose=verbose,
            round_turn_cost=round_turn_cost,
            cost_multiplier=cost_multiplier,
        )
        if len(wf_bundle["equity"]):
            oos_metrics = performance_from_ledger(
                wf_bundle["ledger"],
                wf_bundle["equity"]["OOS_Equity"].to_numpy(dtype=float),
                spec.ticker,
                bar_minutes=bar_minutes,
            )

        if include_surface:
            surface_df = walk_forward_surface(
                analysis_df,
                spec.ticker,
                mode=walkforward_mode,
                tf_grid=tf_grid,
                T_values=list(surface_T_values) if surface_T_values is not None else None,
                tau_values=list(surface_tau_values) if surface_tau_values is not None else None,
                tau_unit=tau_unit,
                quick=quick,
                verbose=verbose,
                round_turn_cost=round_turn_cost,
                cost_multiplier=cost_multiplier,
            )

    tf_config = choose_tf_story_configuration(
        spec.ticker,
        tf_grid=tf_grid,
        params_df=wf_bundle["params"] if wf_bundle is not None else None,
        bar_minutes=bar_minutes,
    )
    full_sample_result = run_backtest(
        analysis_df,
        spec.ticker,
        "tf",
        {"L": tf_config["L"], "S": tf_config["S"]},
        round_turn_cost=round_turn_cost,
        cost_multiplier=cost_multiplier,
    )
    full_sample_metrics = performance_from_ledger(
        full_sample_result["Ledger"],
        np.asarray(full_sample_result["Equity"], dtype=float),
        spec.ticker,
        bar_minutes=bar_minutes,
    )

    story_rows = build_market_story_rows(
        spec.ticker,
        diagnostics_bundle,
        tf_config=tf_config,
        wf_bundle=wf_bundle,
        oos_metrics=oos_metrics,
        full_sample_metrics=full_sample_metrics,
    )
    narrative_lines = build_market_narrative(spec.ticker, diagnostics_bundle, tf_config=tf_config)

    return {
        "ticker": spec.ticker,
        "market": spec,
        "validation": validation,
        "full_df": full_df,
        "analysis_df": analysis_df,
        "diagnostics": diagnostics_bundle,
        "tf_grid": tf_grid,
        "walkforward": wf_bundle,
        "surface": surface_df,
        "tf_config": tf_config,
        "full_sample": full_sample_result,
        "oos_metrics": oos_metrics,
        "oos_metric_sections": split_metric_sections(oos_metrics) if oos_metrics is not None else None,
        "full_sample_metrics": full_sample_metrics,
        "full_sample_metric_sections": split_metric_sections(full_sample_metrics),
        "story_rows": story_rows,
        "narrative_lines": narrative_lines,
    }


def build_pair_story(
    tickers: Sequence[str] = ("TY", "BTC"),
    *,
    data_dir: str | None = None,
    data_map: Mapping[str, pd.DataFrame] | None = None,
    quick: bool = True,
    walkforward_mode: str = "tf",
    include_walkforward: bool = True,
    include_surface: bool = False,
    verbose: bool = False,
    tau_unit: str = "quarters",
    round_turn_cost_map: Mapping[str, float] | None = None,
    cost_multiplier: float = 1.0,
) -> dict[str, object]:
    ordered = [str(ticker).upper() for ticker in tickers]
    stories: dict[str, dict[str, object]] = {}
    diagnostics_rows: list[dict[str, object]] = []
    strategy_rows: list[dict[str, object]] = []

    for ticker in ordered:
        frame = None if data_map is None else data_map.get(ticker)
        story = build_market_story(
            ticker,
            data_dir=data_dir,
            data=frame,
            quick=quick,
            walkforward_mode=walkforward_mode,
            include_walkforward=include_walkforward,
            include_surface=include_surface,
            verbose=verbose,
            tau_unit=tau_unit,
            round_turn_cost=None if round_turn_cost_map is None else round_turn_cost_map.get(ticker),
            cost_multiplier=cost_multiplier,
        )
        stories[ticker] = story
        diagnostics_rows.append(story["story_rows"]["diagnostics"])
        strategy_rows.append(story["story_rows"]["strategy"])

    diagnostics_df = pd.DataFrame(diagnostics_rows)
    strategy_df = pd.DataFrame(strategy_rows)
    narrative_df = pd.DataFrame(
        [{"Ticker": ticker, "Narrative": " ".join(stories[ticker]["narrative_lines"])} for ticker in ordered]
    )
    return {
        "tickers": ordered,
        "stories": stories,
        "diagnostics_df": diagnostics_df,
        "strategy_df": strategy_df,
        "narrative_df": narrative_df,
    }
