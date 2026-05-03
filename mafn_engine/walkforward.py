from __future__ import annotations

from collections import Counter

import numpy as np
import pandas as pd

from .config import bars_per_year, default_mr_grid, default_tf_grid, get_market, infer_bar_minutes_from_index
from .diagnostics import choose_regime_family, run_diagnostics
from .strategies import evaluate_family, run_backtest


def _normalise_grids(
    ticker: str,
    tf_grid: dict[str, np.ndarray] | None = None,
    mr_grid: dict[str, np.ndarray] | None = None,
    quick: bool = True,
    bar_minutes: int = 5,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    if tf_grid is None:
        tf_grid = default_tf_grid(ticker, quick=quick, bar_minutes=bar_minutes)
    if mr_grid is None:
        mr_grid = default_mr_grid(ticker, quick=quick)
    return tf_grid, mr_grid


def _concat_oos_equity(
    market_e0: float,
    chunks: list[pd.Series],
) -> pd.DataFrame:
    if not chunks:
        return pd.DataFrame(columns=["OOS_PnL_cum", "OOS_Equity"])
    pnl = pd.concat(chunks)
    pnl = pnl[~pnl.index.duplicated(keep="first")]
    cum_pnl = pnl.cumsum()
    return pd.DataFrame({"OOS_PnL_cum": cum_pnl, "OOS_Equity": market_e0 + cum_pnl})


def _tau_bars(
    ticker: str,
    tau_value: int,
    tau_unit: str,
    *,
    bar_minutes: int = 5,
    df: pd.DataFrame | None = None,
) -> int:
    spec = get_market(ticker)
    unit = tau_unit.lower().rstrip("s")
    if unit == "quarter":
        return int(tau_value * bars_per_year(ticker, bar_minutes=bar_minutes, df=df) / 4)
    if unit == "month":
        return int(tau_value * bars_per_year(ticker, bar_minutes=bar_minutes, df=df) / 12)
    raise ValueError("tau_unit must be 'quarters' or 'months'")


def _tau_label(tau_value: int, tau_unit: str) -> str:
    unit = tau_unit.lower().rstrip("s")
    suffix = "Q" if unit == "quarter" else "M"
    return f"{tau_value}{suffix}"


def parameter_stability_tables(params_df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    if params_df is None or len(params_df) == 0:
        empty = pd.DataFrame()
        return {
            "timeline": empty,
            "L_frequency": empty,
            "S_frequency": empty,
        }

    cols = [col for col in ["Period", "Family", "IS_start", "IS_end", "OOS_start", "OOS_end", "L", "S"] if col in params_df.columns]
    timeline = params_df[cols].copy()

    if "L" in params_df.columns:
        l_frequency = (
            params_df["L"]
            .dropna()
            .astype(int)
            .value_counts()
            .sort_index()
            .rename_axis("L")
            .reset_index(name="count")
        )
    else:
        l_frequency = pd.DataFrame(columns=["L", "count"])

    if "S" in params_df.columns:
        s_frequency = (
            params_df["S"]
            .dropna()
            .astype(float)
            .round(6)
            .value_counts()
            .sort_index()
            .rename_axis("S")
            .reset_index(name="count")
        )
    else:
        s_frequency = pd.DataFrame(columns=["S", "count"])

    return {
        "timeline": timeline,
        "L_frequency": l_frequency,
        "S_frequency": s_frequency,
    }


def select_modal_configuration(params_df: pd.DataFrame) -> dict[str, object] | None:
    if params_df is None or len(params_df) == 0:
        return None

    family_params = {
        "tf": ["L", "S"],
        "mr": ["N1", "N2", "VolLen", "MALen", "StpPct"],
    }
    configs: list[dict[str, object]] = []

    for _, row in params_df.iterrows():
        family_raw = row.get("Family")
        if pd.isna(family_raw):
            continue
        family = str(family_raw).lower()
        config: dict[str, object] = {"family": family}
        for col in family_params.get(family, []):
            if col not in params_df.columns:
                continue
            value = row.get(col)
            if pd.isna(value):
                continue
            if col in {"L", "VolLen", "MALen"}:
                config[col] = int(float(value))
            else:
                config[col] = float(value)
        if len(config) > 1:
            configs.append(config)

    if not configs:
        return None

    key_counts = Counter(tuple(sorted(cfg.items())) for cfg in configs)
    best_key = key_counts.most_common(1)[0][0]
    return dict(best_key)


def walk_forward(
    df: pd.DataFrame,
    ticker: str,
    mode: str = "dynamic",
    tf_grid: dict[str, np.ndarray] | None = None,
    mr_grid: dict[str, np.ndarray] | None = None,
    T_years: int = 4,
    tau_quarters: int = 1,
    tau_unit: str = "quarters",
    quick: bool = True,
    verbose: bool = True,
    round_turn_cost: float | None = None,
    cost_multiplier: float = 1.0,
) -> dict[str, object]:
    mode = mode.lower()
    if mode not in {"dynamic", "tf", "mr"}:
        raise ValueError("mode must be 'dynamic', 'tf', or 'mr'")

    bar_minutes = infer_bar_minutes_from_index(df.index)
    tf_grid, mr_grid = _normalise_grids(
        ticker,
        tf_grid=tf_grid,
        mr_grid=mr_grid,
        quick=quick,
        bar_minutes=bar_minutes,
    )
    spec = get_market(ticker)
    bpy = bars_per_year(ticker, bar_minutes=bar_minutes, df=df)
    is_bars = int(T_years * bpy)
    tau_value = int(tau_quarters)
    oos_bars = _tau_bars(ticker, tau_value, tau_unit, bar_minutes=bar_minutes, df=df)
    tau_text = _tau_label(tau_value, tau_unit)

    if verbose:
        print(
            f"Walk-Forward [{ticker.upper()}] mode={mode}: "
            f"IS={T_years}yr ({is_bars:,} bars), OOS={tau_text} ({oos_bars:,} bars), "
            f"cost={float(cost_multiplier):.2f}x"
        )

    idx = 0
    period = 1
    params_rows: list[dict[str, object]] = []
    equity_chunks: list[pd.Series] = []
    ledger_chunks: list[pd.DataFrame] = []

    while idx + is_bars + oos_bars <= len(df):
        is_start = idx
        is_end = is_start + is_bars
        oos_start = is_end
        oos_end = oos_start + oos_bars

        if mode == "dynamic":
            is_df = df.iloc[is_start:is_end]
            diag_bundle = run_diagnostics(is_df, ticker)
            diag_choice = dict(diag_bundle["regime_choice"])
            family = str(diag_choice["family"])
        else:
            family = mode
            diag_choice = {
                "family": family,
                "reason": f"forced_{family}",
                "ambiguous": False,
                "tf_votes": int(family == "tf"),
                "mr_votes": int(family == "mr"),
                "median_vr_shift": np.nan,
                "median_pr_rho": np.nan,
            }

        family_grid = tf_grid if family == "tf" else mr_grid
        best_is = evaluate_family(
            df,
            ticker,
            family,
            family_grid,
            eval_start=is_start,
            eval_end=is_end,
            round_turn_cost=round_turn_cost,
            cost_multiplier=cost_multiplier,
        )
        if best_is.get("error"):
            if verbose:
                print(f"  Period {period}: no valid {family} configuration on IS")
            idx += oos_bars
            period += 1
            continue

        best_params = dict(best_is["params"])
        best_oos = run_backtest(
            df,
            ticker,
            family,
            best_params,
            eval_start=oos_start,
            eval_end=oos_end,
            round_turn_cost=round_turn_cost,
            cost_multiplier=cost_multiplier,
        )
        if best_oos.get("error"):
            if verbose:
                print(f"  Period {period}: OOS evaluation failed for {family}")
            idx += oos_bars
            period += 1
            continue

        if verbose:
            print(
                f"  P{period} {family.upper()} "
                f"IS_obj={float(best_is['Objective']):+.3f} "
                f"OOS_obj={float(best_oos['Objective']):+.3f} "
                f"votes(tf={diag_choice['tf_votes']}, mr={diag_choice['mr_votes']})"
            )

        row = {
            "Period": period,
            "Family": family,
            "Mode": mode,
            "TauValue": tau_value,
            "TauUnit": tau_unit,
            "TauLabel": tau_text,
            "CostMultiplier": float(cost_multiplier),
            "RoundTurnCost": float(best_oos.get("RoundTurnCost", np.nan)),
            "IS_start": df.index[is_start],
            "IS_end": df.index[is_end - 1],
            "OOS_start": df.index[oos_start],
            "OOS_end": df.index[oos_end - 1],
            "Decision_family": diag_choice["family"],
            "Decision_reason": diag_choice["reason"],
            "Decision_ambiguous": diag_choice["ambiguous"],
            "TF_votes": diag_choice["tf_votes"],
            "MR_votes": diag_choice["mr_votes"],
            "Median_VR_shift": diag_choice["median_vr_shift"],
            "Median_PR_rho": diag_choice["median_pr_rho"],
            "IS_Objective": best_is["Objective"],
            "IS_Profit": best_is["Profit"],
            "IS_MaxDD": best_is["MaxDD"],
            "IS_Trades": best_is["NumTrades"],
            "IS_Combinations": best_is.get("tested", np.nan),
            "OOS_Objective": best_oos["Objective"],
            "OOS_Profit": best_oos["Profit"],
            "OOS_MaxDD": best_oos["MaxDD"],
            "OOS_Trades": best_oos["NumTrades"],
        }
        row.update(best_params)
        params_rows.append(row)

        local_start = oos_start - int(best_oos["SliceStart"])
        local_end = oos_end - int(best_oos["SliceStart"])
        oos_equity = np.asarray(best_oos["Equity"][local_start:local_end], dtype=float)
        oos_pnl = np.diff(np.r_[spec.E0, oos_equity])
        equity_chunks.append(pd.Series(oos_pnl, index=df.index[oos_start:oos_end], name="OOS_PnL"))

        if len(best_oos["Ledger"]):
            lg = best_oos["Ledger"]
            lg = lg[lg["is_oos"]].copy()
            lg.insert(0, "Period", period)
            lg.insert(1, "Family", family)
            for key, value in best_params.items():
                lg[key] = value
            ledger_chunks.append(lg)

        idx += oos_bars
        period += 1

    params_df = pd.DataFrame(params_rows)
    equity_df = _concat_oos_equity(spec.E0, equity_chunks)
    ledger_df = (
        pd.concat(ledger_chunks, ignore_index=True)
        if ledger_chunks
        else pd.DataFrame(columns=["Period", "Family"])
    )
    return {
        "params": params_df,
        "equity": equity_df,
        "ledger": ledger_df,
        "stability": parameter_stability_tables(params_df),
        "mode": mode,
        "ticker": ticker.upper(),
        "tau_value": tau_value,
        "tau_unit": tau_unit,
        "tau_label": tau_text,
        "cost_multiplier": float(cost_multiplier),
        "round_turn_cost": float(params_df["RoundTurnCost"].iloc[0]) if "RoundTurnCost" in params_df.columns and len(params_df) else np.nan,
    }


def walk_forward_surface(
    df: pd.DataFrame,
    ticker: str,
    mode: str = "dynamic",
    tf_grid: dict[str, np.ndarray] | None = None,
    mr_grid: dict[str, np.ndarray] | None = None,
    T_values: list[int] | None = None,
    tau_values: list[int] | None = None,
    tau_unit: str = "quarters",
    quick: bool = True,
    verbose: bool = False,
    round_turn_cost: float | None = None,
    cost_multiplier: float = 1.0,
) -> pd.DataFrame:
    if T_values is None:
        T_values = list(range(1, 11))
    if tau_values is None:
        tau_values = [1, 2, 3, 4]

    rows: list[dict[str, object]] = []
    for T in T_values:
        for tau in tau_values:
            bundle = walk_forward(
                df,
                ticker,
                mode=mode,
                tf_grid=tf_grid,
                mr_grid=mr_grid,
                T_years=T,
                tau_quarters=tau,
                tau_unit=tau_unit,
                quick=quick,
                verbose=verbose,
                round_turn_cost=round_turn_cost,
                cost_multiplier=cost_multiplier,
            )
            params_df = bundle["params"]
            if len(params_df) == 0:
                rows.append({"T": T, "tau": tau, "tau_unit": tau_unit, "tau_label": _tau_label(tau, tau_unit), "error": True})
                continue
            avg_is = float(params_df["IS_Objective"].mean())
            avg_oos = float(params_df["OOS_Objective"].mean())
            total_oos = float(params_df["OOS_Profit"].sum())
            decay = avg_oos / avg_is if avg_is > 0 else 0.0
            mode_family = params_df["Family"].mode().iloc[0]
            rows.append(
                {
                    "T": T,
                    "tau": tau,
                    "tau_unit": tau_unit,
                    "tau_label": _tau_label(tau, tau_unit),
                    "n": int(len(params_df)),
                    "avg_is": avg_is,
                    "avg_oos": avg_oos,
                    "decay": decay,
                    "total_oos": total_oos,
                    "dominant_family": mode_family,
                    "cost_multiplier": float(cost_multiplier),
                    "round_turn_cost": float(params_df["RoundTurnCost"].iloc[0]) if "RoundTurnCost" in params_df.columns else np.nan,
                    "error": False,
                }
            )
    return pd.DataFrame(rows)
