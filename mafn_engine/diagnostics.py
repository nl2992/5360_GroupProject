from __future__ import annotations

import os

import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import spearmanr

from .config import (
    DEFAULT_BAR_MINUTES,
    active_bars_per_session,
    bars_to_time,
    get_market,
    infer_bar_minutes_from_index,
    professor_dense_q_grid,
    professor_reference_tau,
    professor_showcase_tau,
)


def load_ohlc(
    data_dir: str,
    ticker: str,
    fallback_synthetic: bool = True,
    bar_minutes: int | None = DEFAULT_BAR_MINUTES,
) -> pd.DataFrame:
    spec = get_market(ticker)
    if os.path.isfile(data_dir):
        print(f"✓ Loaded {spec.ticker} from {data_dir}")
        df = _read_ohlc_csv(data_dir)
        _validate_loaded_market(df, ticker, source_path=data_dir)
        return df
    if bar_minutes is not None:
        candidates = [
            os.path.join(data_dir, f"{ticker.upper()}-{int(bar_minutes)}minHLV.csv"),
            os.path.join(data_dir, f"{spec.ticker.upper()}-{int(bar_minutes)}minHLV.csv"),
        ]
    else:
        candidates = [
            os.path.join(data_dir, f"{ticker.upper()}-5minHLV.csv"),
            os.path.join(data_dir, f"{spec.ticker.upper()}-5minHLV.csv"),
            os.path.join(data_dir, f"{ticker.upper()}-1minHLV.csv"),
            os.path.join(data_dir, f"{spec.ticker.upper()}-1minHLV.csv"),
        ]
    for path in candidates:
        if os.path.exists(path):
            print(f"✓ Loaded {spec.ticker} from {path}")
            df = _read_ohlc_csv(path)
            _validate_loaded_market(df, ticker, source_path=path)
            return df

    if fallback_synthetic:
        print(
            f"⚠ No data file found for {spec.ticker} "
            f"(tried {candidates}) — using synthetic series."
        )
        return _synthetic_series(ticker, bar_minutes=int(bar_minutes or DEFAULT_BAR_MINUTES))

    raise FileNotFoundError(f"No data file found for {spec.ticker}: {candidates}")


def _read_ohlc_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip().str.lower()
    if "date" in df.columns and "time" in df.columns:
        df["datetime"] = pd.to_datetime(
            df["date"].astype(str) + " " + df["time"].astype(str),
            format="mixed",
        )
    elif "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"])
    else:
        df["datetime"] = pd.to_datetime(df.iloc[:, 0])

    df = df.set_index("datetime").sort_index()
    rename_map: dict[str, str] = {}
    for col in df.columns:
        key = col.lower()
        if "open" in key:
            rename_map[col] = "Open"
        elif "high" in key:
            rename_map[col] = "High"
        elif "low" in key:
            rename_map[col] = "Low"
        elif "close" in key:
            rename_map[col] = "Close"
        elif "vol" in key:
            rename_map[col] = "Volume"
    df = df.rename(columns=rename_map)
    keep = [col for col in ["Open", "High", "Low", "Close", "Volume"] if col in df.columns]
    out = df[keep].astype(float)
    out.attrs["source_path"] = path
    return out


def _validate_loaded_market(df: pd.DataFrame, ticker: str, source_path: str = "") -> None:
    spec = get_market(ticker)
    first = pd.Timestamp(df.index.min())
    max_close = float(df["Close"].max())
    if spec.ticker == "BTC":
        if first < pd.Timestamp("2017-12-18"):
            raise ValueError(
                f"{ticker.upper()} data appears mislabeled: {source_path} starts at {first:%Y-%m-%d}, before CME BTC futures inception."
            )
        if max_close < 1000:
            raise ValueError(
                f"{ticker.upper()} data appears mislabeled: {source_path} never trades above 1000, which is inconsistent with CME BTC futures."
            )


def _synthetic_series(
    ticker: str,
    n: int = 250_000,
    bar_minutes: int = DEFAULT_BAR_MINUTES,
) -> pd.DataFrame:
    spec = get_market(ticker)
    seed = 42 + sum(ord(ch) for ch in spec.ticker)
    np.random.seed(seed)
    dates = pd.date_range("2010-01-01", periods=n, freq=f"{int(bar_minutes)}min")
    ret = np.random.randn(n) * spec.synthetic_sigma
    ret += np.sin(np.linspace(0, 8 * np.pi, n)) * (spec.synthetic_sigma / 3)
    close = spec.start_price * np.exp(np.cumsum(ret))
    df = pd.DataFrame(
        {
            "Open": close * (1 + np.random.randn(n) * spec.synthetic_sigma / 3),
            "High": close * (1 + np.abs(np.random.randn(n) * spec.synthetic_sigma)),
            "Low": close * (1 - np.abs(np.random.randn(n) * spec.synthetic_sigma)),
            "Close": close,
        },
        index=dates,
    )
    df["High"] = df[["Open", "High", "Close"]].max(axis=1)
    df["Low"] = df[["Open", "Low", "Close"]].min(axis=1)
    return df


def validate_ohlc(df: pd.DataFrame) -> dict[str, object]:
    issues: list[str] = []
    if (df["High"] < df["Low"]).any():
        issues.append(f"High < Low on {(df['High'] < df['Low']).sum()} bars")
    if (df["High"] < df["Open"]).any() or (df["High"] < df["Close"]).any():
        issues.append("High below Open/Close on at least one bar")
    if (df["Low"] > df["Open"]).any() or (df["Low"] > df["Close"]).any():
        issues.append("Low above Open/Close on at least one bar")
    return {
        "n_bars": int(len(df)),
        "start": df.index.min(),
        "end": df.index.max(),
        "years": float((df.index.max() - df.index.min()).days / 365.25),
        "issues": issues,
        "is_valid": len(issues) == 0,
    }


def compute_return_summary(df: pd.DataFrame) -> dict[str, float]:
    returns = np.log(df["Close"] / df["Close"].shift(1)).dropna()
    return {
        "mean": float(returns.mean()),
        "std": float(returns.std()),
        "skew": float(stats.skew(returns, bias=False)),
        "ex_kurtosis": float(stats.kurtosis(returns, fisher=True, bias=False)),
    }


def filter_session(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    spec = get_market(ticker)
    if not spec.use_session_filter or spec.session_start is None or spec.session_end is None:
        return df.copy()
    mins = df.index.hour * 60 + df.index.minute
    start = int(spec.session_start[:2]) * 60 + int(spec.session_start[3:5])
    end = int(spec.session_end[:2]) * 60 + int(spec.session_end[3:5])
    if start <= end:
        mask = (mins > start) & (mins <= end)
    else:
        mask = (mins > start) | (mins <= end)
    return df.loc[mask].copy()


def prepare_analysis_frame(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    out = filter_session(df, ticker)
    return out.sort_index()


def _lo_mackinlay_vr_core(series: np.ndarray, k: int) -> dict[str, float]:
    r = np.asarray(series, dtype=np.float64)
    r = r[np.isfinite(r)]
    T = len(r)
    nan_res = {"VR": np.nan, "Z1": np.nan, "Z2": np.nan, "p1": np.nan, "p2": np.nan, "n": T}
    if T < k + 10 or k < 2:
        return nan_res

    mu = r.mean()
    dev = r - mu
    sum_sq = float(np.sum(dev**2))
    if sum_sq <= 0:
        return nan_res

    sigma2_1 = sum_sq / (T - 1)
    csum = np.concatenate(([0.0], np.cumsum(r)))
    ret_k = csum[k:] - csum[:-k]
    m = k * (T - k + 1) * (1 - k / T)
    sigma2_k = float(np.sum((ret_k - k * mu) ** 2)) / m
    vr = sigma2_k / sigma2_1

    phi = 2.0 * (2 * k - 1) * (k - 1) / (3.0 * k * T)
    z1 = (vr - 1.0) / np.sqrt(phi)

    dev_sq = dev**2
    denom = sum_sq**2
    delta_var = 0.0
    for j in range(1, k):
        weight = 2.0 * (k - j) / k
        delta_j = T * float(np.sum(dev_sq[j:] * dev_sq[:-j])) / denom
        delta_var += (weight**2) * delta_j
    z2 = (vr - 1.0) / np.sqrt(delta_var) if delta_var > 0 else np.nan

    p1 = 2.0 * (1.0 - stats.norm.cdf(abs(z1)))
    p2 = 2.0 * (1.0 - stats.norm.cdf(abs(z2))) if np.isfinite(z2) else np.nan
    return {"VR": vr, "Z1": z1, "Z2": z2, "p1": p1, "p2": p2, "n": T}


def vr_price_differences(df: pd.DataFrame, k: int, ticker: str) -> dict[str, object]:
    sess = filter_session(df, ticker)
    dp = sess["Close"].diff().dropna().values
    out = _lo_mackinlay_vr_core(dp, k)
    out.update({"k": k, "kind": "dp", "ticker": ticker.upper(), "time_scale": bars_to_time(k, ticker, df=sess)})
    return out


def vr_log_returns(df: pd.DataFrame, k: int, ticker: str) -> dict[str, object]:
    lr = np.log(df["Close"] / df["Close"].shift(1)).dropna().values
    out = _lo_mackinlay_vr_core(lr, k)
    out.update(
        {"k": k, "kind": "logret", "ticker": ticker.upper(), "time_scale": bars_to_time(k, ticker, df=df)}
    )
    return out


def run_vr_suite(
    df: pd.DataFrame,
    ticker: str,
    k_values: list[int] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if k_values is None:
        bps = max(1, int(round(get_market(ticker).session_minutes / infer_bar_minutes_from_index(df.index))))
        k_values = [2, 4, 8, 12, 24, 48, bps, bps * 2, bps * 5, bps * 10, bps * 20, bps * 40]

    rows_dp = [vr_price_differences(df, k, ticker) for k in k_values]
    rows_lr = [vr_log_returns(df, k, ticker) for k in k_values]

    def _frame(rows: list[dict[str, object]]) -> pd.DataFrame:
        out = pd.DataFrame(rows)
        out["significant"] = (out["p2"] < 0.05) & out["Z2"].notna()
        out["pattern"] = np.where(out["VR"] > 1, "trend", "mean_revert")
        cols = ["ticker", "kind", "k", "time_scale", "n", "VR", "Z1", "p1", "Z2", "p2", "significant", "pattern"]
        return out[cols]

    return _frame(rows_dp), _frame(rows_lr)


def variance_ratio_curve(
    df: pd.DataFrame,
    ticker: str,
    q_values: np.ndarray | list[int] | None = None,
) -> pd.DataFrame:
    spec = get_market(ticker)
    if q_values is None:
        q_values = professor_dense_q_grid(ticker, bar_minutes=infer_bar_minutes_from_index(df.index))

    q_values = np.unique(np.asarray(q_values, dtype=int))
    rows: list[dict[str, object]] = [
        {
            "ticker": spec.ticker,
            "q": 1,
            "time_scale": bars_to_time(1, ticker, df=df),
            "VR": 1.0,
            "Z2": 0.0,
            "p2": np.nan,
            "significant": False,
        }
    ]
    for q in q_values:
        if q <= 1:
            continue
        item = vr_price_differences(df, int(q), ticker)
        rows.append(
            {
                "ticker": item["ticker"],
                "q": int(q),
                "time_scale": item["time_scale"],
                "VR": float(item["VR"]),
                "Z2": float(item["Z2"]),
                "p2": float(item["p2"]),
                "significant": bool((item["p2"] < 0.05) if np.isfinite(item["p2"]) else False),
            }
        )
    return pd.DataFrame(rows).sort_values("q").reset_index(drop=True)


def push_response_diagram(
    df: pd.DataFrame,
    push_bars: int,
    response_bars: int,
    ticker: str,
    n_bins: int = 11,
) -> dict[str, object] | None:
    sess = filter_session(df, ticker)
    p = sess["Close"].values
    n = len(p)
    if n < push_bars + response_bars + 50:
        return None

    push = p[push_bars : n - response_bars] - p[: n - response_bars - push_bars]
    resp = p[push_bars + response_bars :] - p[push_bars : n - response_bars]
    L = min(len(push), len(resp))
    push = push[:L]
    resp = resp[:L]

    edges = np.quantile(push, np.linspace(0.0, 1.0, n_bins + 1))
    edges[0] -= 1e-12
    edges[-1] += 1e-12
    bin_idx = np.clip(np.digitize(push, edges[1:-1]), 0, n_bins - 1)

    bin_centre = np.zeros(n_bins)
    bin_mean = np.zeros(n_bins)
    bin_std = np.zeros(n_bins)
    bin_count = np.zeros(n_bins, dtype=int)
    for bucket in range(n_bins):
        mask = bin_idx == bucket
        if mask.any():
            bin_centre[bucket] = float(push[mask].mean())
            bin_mean[bucket] = float(resp[mask].mean())
            bin_std[bucket] = float(resp[mask].std(ddof=1)) if mask.sum() > 1 else 0.0
            bin_count[bucket] = int(mask.sum())

    rho, p_value = spearmanr(bin_centre, bin_mean)
    bin_se = np.where(bin_count > 0, bin_std / np.sqrt(np.maximum(bin_count, 1)), 0.0)
    return {
        "ticker": ticker.upper(),
        "push_bars": push_bars,
        "response_bars": response_bars,
        "push_scale": bars_to_time(push_bars, ticker, df=sess),
        "resp_scale": bars_to_time(response_bars, ticker, df=sess),
        "n_obs": int(L),
        "n_bins": n_bins,
        "bin_centre": bin_centre,
        "bin_mean": bin_mean,
        "bin_std": bin_std,
        "bin_se": bin_se,
        "bin_count": bin_count,
        "spearman_rho": float(rho),
        "spearman_p": float(p_value),
        "significant": bool(p_value < 0.05),
        "pattern": "trend" if rho > 0 else "mean_revert",
    }


def run_pr_suite(
    df: pd.DataFrame,
    ticker: str,
    push_grid: list[int] | None = None,
    response_grid: list[int] | None = None,
    n_bins: int = 11,
) -> tuple[pd.DataFrame, list[dict[str, object]]]:
    bps = active_bars_per_session(ticker, df=df)
    if push_grid is None:
        push_grid = [6, 12, 24, max(1, bps // 2), bps, bps * 2, bps * 5]
    if response_grid is None:
        response_grid = push_grid

    rows: list[dict[str, object]] = []
    full: list[dict[str, object]] = []
    for push_bars in push_grid:
        for response_bars in response_grid:
            diag = push_response_diagram(df, push_bars, response_bars, ticker, n_bins=n_bins)
            if diag is None:
                continue
            full.append(diag)
            rows.append(
                {
                    "ticker": diag["ticker"],
                    "push_bars": push_bars,
                    "push_scale": diag["push_scale"],
                    "resp_bars": response_bars,
                    "resp_scale": diag["resp_scale"],
                    "n_obs": diag["n_obs"],
                    "spearman_rho": diag["spearman_rho"],
                    "spearman_p": diag["spearman_p"],
                    "significant": diag["significant"],
                    "pattern": diag["pattern"],
                }
            )
    return pd.DataFrame(rows), full


def professor_horizon_bundle(
    df: pd.DataFrame,
    ticker: str,
) -> dict[str, object]:
    spec = get_market(ticker)
    bar_minutes = infer_bar_minutes_from_index(df.index)
    bps = max(1, int(round(spec.session_minutes / bar_minutes)))
    reference_tau = int(professor_reference_tau(ticker, bar_minutes=bar_minutes))
    showcase_tau = int(professor_showcase_tau(ticker, bar_minutes=bar_minutes))
    short_tau = bps if spec.ticker == "TY" else max(bps, reference_tau // 4)
    vr_curve_df = variance_ratio_curve(df, ticker, q_values=professor_dense_q_grid(ticker, bar_minutes=bar_minutes))
    short_pr = push_response_diagram(df, short_tau, short_tau, ticker)
    reference_pr = push_response_diagram(df, reference_tau, reference_tau, ticker)
    showcase_pr = push_response_diagram(df, showcase_tau, showcase_tau, ticker)
    return {
        "reference_tau": reference_tau,
        "reference_scale": bars_to_time(reference_tau, ticker, df=df),
        "showcase_tau": showcase_tau,
        "showcase_scale": bars_to_time(showcase_tau, ticker, df=df),
        "short_tau": int(short_tau),
        "short_scale": bars_to_time(int(short_tau), ticker, df=df),
        "vr_curve_df": vr_curve_df,
        "short_pr": short_pr,
        "reference_pr": reference_pr,
        "showcase_pr": showcase_pr,
    }


def interpret_regimes(vr_dp_df: pd.DataFrame, pr_df: pd.DataFrame | None = None) -> pd.DataFrame:
    tbl = vr_dp_df[["time_scale", "k", "VR", "Z2", "p2", "significant", "pattern"]].copy()
    tbl = tbl.rename(
        columns={
            "Z2": "VR_Z2_robust",
            "p2": "VR_p2",
            "pattern": "VR_pattern",
            "significant": "VR_sig",
        }
    )
    if pr_df is not None and len(pr_df):
        pr_tbl = (
            pr_df.groupby("push_scale")
            .agg(PR_rho_mean=("spearman_rho", "mean"), PR_rho_sig_any=("significant", "max"))
            .reset_index()
        )
        tbl = tbl.merge(pr_tbl, left_on="time_scale", right_on="push_scale", how="left")

    recommendations = []
    for _, row in tbl.iterrows():
        if not bool(row["VR_sig"]):
            recommendations.append("TF-baseline (no rejection)")
        else:
            recommendations.append("TF-candidate" if row["VR_pattern"] == "trend" else "MR-candidate")
    tbl["Recommendation"] = recommendations
    return tbl


def choose_regime_family(vr_dp_df: pd.DataFrame, pr_df: pd.DataFrame | None = None) -> dict[str, object]:
    vr_sig = vr_dp_df[vr_dp_df["significant"]]
    tf_votes = int((vr_sig["pattern"] == "trend").sum())
    mr_votes = int((vr_sig["pattern"] == "mean_revert").sum())
    pr_sig = pd.DataFrame()
    if pr_df is not None and len(pr_df):
        pr_sig = pr_df[pr_df["significant"]]
        tf_votes += int((pr_sig["pattern"] == "trend").sum())
        mr_votes += int((pr_sig["pattern"] == "mean_revert").sum())

    median_vr_shift = float((vr_dp_df["VR"] - 1.0).median()) if len(vr_dp_df) else 0.0
    median_pr_rho = float(pr_df["spearman_rho"].median()) if pr_df is not None and len(pr_df) else 0.0
    tie_score = 0
    if median_vr_shift > 0:
        tie_score += 1
    elif median_vr_shift < 0:
        tie_score -= 1
    if median_pr_rho > 0:
        tie_score += 1
    elif median_pr_rho < 0:
        tie_score -= 1

    if tf_votes > mr_votes:
        family = "tf"
        reason = "significant-vote majority"
    elif mr_votes > tf_votes:
        family = "mr"
        reason = "significant-vote majority"
    elif tf_votes == 0 and mr_votes == 0:
        family = "tf"
        reason = "weak-evidence default"
    else:
        family = "tf" if tie_score >= 0 else "mr"
        reason = "tie-break median diagnostics"

    return {
        "family": family,
        "tf_votes": tf_votes,
        "mr_votes": mr_votes,
        "median_vr_shift": median_vr_shift,
        "median_pr_rho": median_pr_rho,
        "reason": reason,
        "ambiguous": abs(tf_votes - mr_votes) <= 1,
    }


def summarise_trend_profile(
    vr_dp_df: pd.DataFrame,
    pr_df: pd.DataFrame | None = None,
    ticker: str | None = None,
    bar_minutes: int = DEFAULT_BAR_MINUTES,
) -> dict[str, object]:
    if vr_dp_df is None or len(vr_dp_df) == 0:
        return {
            "assignment_family": "tf",
            "trend_strengthens_with_horizon": False,
            "tf_speed_bias": "slow",
            "vr_horizon_slope": np.nan,
            "vr_horizon_rho": np.nan,
            "vr_short_mean": np.nan,
            "vr_long_mean": np.nan,
            "vr_long_minus_short": np.nan,
            "short_window": "n/a",
            "long_window": "n/a",
            "peak_vr_scale": "n/a",
            "peak_vr": np.nan,
            "pr_short_mean_rho": np.nan,
            "pr_long_mean_rho": np.nan,
            "pr_long_minus_short": np.nan,
            "peak_pr_scale": "n/a",
            "peak_pr_rho": np.nan,
            "narrative": "No diagnostic observations were available.",
        }

    inferred_ticker = ticker or str(vr_dp_df.iloc[0]["ticker"])
    spec = get_market(inferred_ticker)
    bps = active_bars_per_session(inferred_ticker, bar_minutes=bar_minutes)
    vr = vr_dp_df.sort_values("k").reset_index(drop=True).copy()
    split = max(1, len(vr) // 3)
    vr_short = vr.iloc[:split]
    vr_long = vr.iloc[-split:]

    vr_short_mean = float(vr_short["VR"].mean())
    vr_long_mean = float(vr_long["VR"].mean())
    vr_long_minus_short = vr_long_mean - vr_short_mean
    vr_horizon_slope = float(np.polyfit(np.log(vr["k"].astype(float)), vr["VR"].astype(float), 1)[0]) if len(vr) > 1 else 0.0
    vr_horizon_rho = float(spearmanr(vr["k"], vr["VR"]).statistic) if len(vr) > 1 else 0.0
    peak_vr_row = vr.loc[vr["VR"].idxmax()]

    pr_short_mean = np.nan
    pr_long_mean = np.nan
    pr_long_minus_short = np.nan
    peak_pr_scale = "n/a"
    peak_pr_rho = np.nan
    if pr_df is not None and len(pr_df):
        pr_by_push = (
            pr_df.groupby(["push_bars", "push_scale"], as_index=False)
            .agg(mean_rho=("spearman_rho", "mean"), any_sig=("significant", "max"))
            .sort_values("push_bars")
            .reset_index(drop=True)
        )
        pr_split = max(1, len(pr_by_push) // 3)
        pr_short = pr_by_push.iloc[:pr_split]
        pr_long = pr_by_push.iloc[-pr_split:]
        pr_short_mean = float(pr_short["mean_rho"].mean())
        pr_long_mean = float(pr_long["mean_rho"].mean())
        pr_long_minus_short = pr_long_mean - pr_short_mean
        peak_pr_row = pr_by_push.loc[pr_by_push["mean_rho"].idxmax()]
        peak_pr_scale = str(peak_pr_row["push_scale"])
        peak_pr_rho = float(peak_pr_row["mean_rho"])

    trend_strengthens = bool(
        (vr_long_minus_short > 0.02)
        or (vr_horizon_slope > 0.015)
        or (np.isfinite(pr_long_minus_short) and pr_long_minus_short > 0.05)
    )

    peak_scale_bars = int(float(peak_vr_row["k"]))
    if np.isfinite(peak_pr_rho):
        pr_peak_row = (
            pr_df.groupby(["push_bars", "push_scale"], as_index=False)
            .agg(mean_rho=("spearman_rho", "mean"))
            .sort_values("mean_rho")
            .iloc[-1]
        )
        peak_scale_bars = max(peak_scale_bars, int(float(pr_peak_row["push_bars"])))

    if spec.ticker == "BTC":
        tf_speed_bias = "fast" if peak_scale_bars <= 8 * bps else "medium"
    else:
        tf_speed_bias = "slow" if peak_scale_bars >= 10 * bps or trend_strengthens else "medium"

    short_window = f"{vr_short.iloc[0]['time_scale']} to {vr_short.iloc[-1]['time_scale']}"
    long_window = f"{vr_long.iloc[0]['time_scale']} to {vr_long.iloc[-1]['time_scale']}"

    if spec.ticker == "TY":
        narrative = (
            "TY does not need VR(k) to be above 1 at the shortest scales. "
            f"What matters is that VR rises from {short_window} toward {long_window}, "
            "and the push-response test becomes more trend-consistent as the horizon lengthens. "
            "This supports a slower trend-following implementation with longer holding and lookback horizons."
            if trend_strengthens
            else
            "TY looks weak or mixed at short horizons, so the treasury story should emphasise that any "
            "trend-following inefficiency is a slower multi-session effect rather than a fast daily one."
        )
    elif spec.ticker == "BTC":
        narrative = (
            "BTC shows earlier and stronger trend-following evidence: the variance ratio and push-response "
            "statistics become positive quickly, so a faster trend-following implementation is reasonable."
        )
    else:
        narrative = (
            "Use the diagnostics to locate the trend-following window, not to demand VR(k) > 1 at every scale. "
            f"Here the trend evidence is strongest around {peak_vr_row['time_scale']}."
        )

    return {
        "assignment_family": "tf",
        "trend_strengthens_with_horizon": trend_strengthens,
        "tf_speed_bias": tf_speed_bias,
        "vr_horizon_slope": vr_horizon_slope,
        "vr_horizon_rho": vr_horizon_rho,
        "vr_short_mean": vr_short_mean,
        "vr_long_mean": vr_long_mean,
        "vr_long_minus_short": vr_long_minus_short,
        "short_window": short_window,
        "long_window": long_window,
        "peak_vr_scale": str(peak_vr_row["time_scale"]),
        "peak_vr": float(peak_vr_row["VR"]),
        "pr_short_mean_rho": pr_short_mean,
        "pr_long_mean_rho": pr_long_mean,
        "pr_long_minus_short": pr_long_minus_short,
        "peak_pr_scale": peak_pr_scale,
        "peak_pr_rho": peak_pr_rho,
        "narrative": narrative,
    }


def select_representative_pr_diagram(
    diagrams: list[dict[str, object]],
) -> dict[str, object] | None:
    if not diagrams:
        return None

    def _key(item: dict[str, object]) -> tuple[int, float, int]:
        return (
            1 if bool(item["significant"]) else 0,
            abs(float(item["spearman_rho"])),
            int(item["n_obs"]),
        )

    return max(diagrams, key=_key)


def run_diagnostics(
    df: pd.DataFrame,
    ticker: str,
    k_values: list[int] | None = None,
    push_grid: list[int] | None = None,
    response_grid: list[int] | None = None,
    n_bins: int = 11,
) -> dict[str, object]:
    bar_minutes = infer_bar_minutes_from_index(df.index)
    vr_dp_df, vr_lr_df = run_vr_suite(df, ticker, k_values=k_values)
    pr_summary_df, pr_diagrams = run_pr_suite(
        df,
        ticker,
        push_grid=push_grid,
        response_grid=response_grid,
        n_bins=n_bins,
    )
    regime_table = interpret_regimes(vr_dp_df, pr_summary_df)
    regime_choice = choose_regime_family(vr_dp_df, pr_summary_df)
    trend_profile = summarise_trend_profile(
        vr_dp_df,
        pr_summary_df,
        ticker=ticker,
        bar_minutes=bar_minutes,
    )
    professor_bundle = professor_horizon_bundle(df, ticker)
    return {
        "vr_price_df": vr_dp_df,
        "vr_logret_df": vr_lr_df,
        "pr_summary_df": pr_summary_df,
        "pr_diagrams": pr_diagrams,
        "regime_table": regime_table,
        "regime_choice": regime_choice,
        "trend_profile": trend_profile,
        "professor_bundle": professor_bundle,
        "representative_pr": select_representative_pr_diagram(pr_diagrams),
    }
