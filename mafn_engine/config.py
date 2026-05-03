from __future__ import annotations

from dataclasses import dataclass

import matplotlib as mpl
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class MarketSpec:
    ticker: str
    name: str
    exchange: str
    PV: float
    slpg: float
    tick_value: float
    pv_multiplier: float = 1.0
    E0: float = 100_000.0
    session_start: str | None = None
    session_end: str | None = None
    session_minutes: int = 390
    bars_per_session: int = 78
    trading_days_per_year: int = 252
    use_session_filter: bool = False
    start_price: float = 100.0
    synthetic_sigma: float = 0.0003
    cost_source: str = ""


COLUMBIA_BLUE = "#B9D9EB"
COLUMBIA_CORE = "#75AADB"
COLUMBIA_NAVY = "#012169"
COLUMBIA_DARK = "#1D4F91"
COLUMBIA_ACCENT = "#C4D8E2"
COLUMBIA_GREY = "#4B4B4B"
COLUMBIA_WARM = "#E08119"
COLUMBIA_RED = "#8B0000"

COLUMBIA_CMAP = LinearSegmentedColormap.from_list(
    "columbia",
    [COLUMBIA_NAVY, COLUMBIA_DARK, COLUMBIA_CORE, COLUMBIA_BLUE, "#FFFFFF"],
)
COLUMBIA_DIVERGING = LinearSegmentedColormap.from_list(
    "columbia_div",
    [COLUMBIA_RED, COLUMBIA_WARM, "#FFFFFF", COLUMBIA_CORE, COLUMBIA_NAVY],
)


def _market(
    ticker: str,
    name: str,
    exchange: str,
    pv: float,
    slpg: float,
    tick_value: float,
    pv_multiplier: float = 1.0,
    *,
    session_start: str | None = None,
    session_end: str | None = None,
    session_minutes: int = 390,
    trading_days_per_year: int = 252,
    use_session_filter: bool = False,
    start_price: float = 100.0,
    synthetic_sigma: float = 0.0003,
    cost_source: str = "",
) -> MarketSpec:
    return MarketSpec(
        ticker=ticker,
        name=name,
        exchange=exchange,
        PV=pv,
        slpg=slpg,
        tick_value=tick_value,
        pv_multiplier=pv_multiplier,
        session_start=session_start,
        session_end=session_end,
        session_minutes=session_minutes,
        bars_per_session=max(1, session_minutes // 5),
        trading_days_per_year=trading_days_per_year,
        use_session_filter=use_session_filter,
        start_price=start_price,
        synthetic_sigma=synthetic_sigma,
        cost_source=cost_source,
    )


TF_DATA_SOURCE = "/Users/nigelli/Downloads/TF Data (1).xls"
CHINA_TRCOST_SOURCE = "/Users/nigelli/Downloads/TrCostsChina 03-07-2019.xls"
DEFAULT_BAR_MINUTES = 5

MARKETS: dict[str, MarketSpec] = {
    "BO": _market("BO", "Soybean Oil", "CBOT-CME", 600, 39, 6, start_price=30, cost_source=TF_DATA_SOURCE),
    "DX": _market("DX", "Dollar Index", "NYBOT-ICE", 1000, 16.5, 5, start_price=90, cost_source=TF_DATA_SOURCE),
    "HG": _market("HG", "Copper", "COMEX-NYMEX-CME", 250, 59.25, 12.5, start_price=3, cost_source=TF_DATA_SOURCE),
    "HO": _market("HO", "Heating Oil", "NYMEX-CME", 420, 70.2, 4.2, 100, start_price=2, cost_source=TF_DATA_SOURCE),
    "JO": _market("JO", "Orange Juice", "NYBOT-ICE", 150, 183, 7.5, start_price=100, cost_source=TF_DATA_SOURCE),
    "JY": _market("JY", "Japanese Yen", "CME", 1250, 53, 6.25, 100, start_price=0.009, cost_source=TF_DATA_SOURCE),
    "SY": _market("SY", "Soybeans", "CBOT-CME", 50, 35.5, 12.5, start_price=900, cost_source=TF_DATA_SOURCE),
    "SB": _market("SB", "Sugar #11", "NYBOT-ICE", 1120, 56.76, 11.2, start_price=15, cost_source=TF_DATA_SOURCE),
    "SF": _market("SF", "Swiss Franc", "CME", 1250, 25.5, 12.5, 100, start_price=1, cost_source=TF_DATA_SOURCE),
    "TU": _market("TU", "2-Year Treasury", "CBOT-CME", 2000, 18.625, 15.625, start_price=105, cost_source=TF_DATA_SOURCE),
    "TY": _market(
        "TY",
        "10-Year Treasury",
        "CBOT-CME",
        1000,
        18.625,
        15.625,
        session_start="07:20",
        session_end="14:00",
        session_minutes=400,
        trading_days_per_year=252,
        use_session_filter=True,
        start_price=115,
        cost_source=TF_DATA_SOURCE,
    ),
    "WC": _market("WC", "Wheat", "CBOT-CME", 50, 30.5, 12.5, start_price=500, cost_source=TF_DATA_SOURCE),
    "SM": _market("SM", "Soybean Meal", "CBOT-CME", 100, 57, 10, start_price=300, cost_source=TF_DATA_SOURCE),
    "CC": _market("CC", "Cocoa", "NYBOT-ICE", 10, 103, 10, start_price=2500, cost_source=TF_DATA_SOURCE),
    "BZ": _market("BZ", "Schatz", "EUREX", 1000, 10.5, 5, start_price=110, cost_source=TF_DATA_SOURCE),
    "CL": _market("CL", "Crude Oil WTI", "NYMEX-CME", 1000, 46, 10, start_price=60, cost_source=TF_DATA_SOURCE),
    "GC": _market("GC", "Gold 100oz", "COMEX-NYMEX-CME", 100, 65, 10, start_price=1300, cost_source=TF_DATA_SOURCE),
    "SV": _market("SV", "Silver", "COMEX-NYMEX-CME", 5000, 243, 25, 0.01, start_price=15, cost_source=TF_DATA_SOURCE),
    "BTC": _market(
        "BTC",
        "Bitcoin",
        "CME",
        5,
        25,
        25,
        session_start="17:00",
        session_end="16:00",
        session_minutes=1380,
        trading_days_per_year=365,
        use_session_filter=True,
        start_price=20_000,
        synthetic_sigma=0.0015,
        cost_source=TF_DATA_SOURCE,
    ),
    "CO": _market("CO", "Brent Crude Oil", "ICE", 1000, 46, 10, start_price=60, cost_source=TF_DATA_SOURCE),
    "FC": _market("FC", "Feeder Cattle", "CME", 500, 60, 12.5, start_price=150, cost_source=TF_DATA_SOURCE),
    "PL": _market("PL", "Platinum", "NYMEX", 50, 70, 5, start_price=900, cost_source=TF_DATA_SOURCE),
    "XB": _market("XB", "Gasoline (RBOB)", "NYMEX", 420, 70.2, 4.2, 100, start_price=2, cost_source=TF_DATA_SOURCE),
    "COKE": _market("COKE", "Coke Futures", "DCE", 100, 60, 10, start_price=2000, cost_source=CHINA_TRCOST_SOURCE),
    "CS": _market("CS", "Corn Starch Futures", "DCE", 10, 30, 1, start_price=2500, cost_source=CHINA_TRCOST_SOURCE),
    "SOYBN": _market("SOYBN", "No. 1 Soybean Futures", "DCE", 10, 35, 1, start_price=4000, cost_source=CHINA_TRCOST_SOURCE),
    "AUG": _market("AUG", "Gold Futures", "SHFE", 1000, 50, 10, start_price=450, cost_source=CHINA_TRCOST_SOURCE),
    "CUC": _market("CUC", "Copper Cathode Futures", "SHFE", 5, 40, 25, start_price=50_000, cost_source=CHINA_TRCOST_SOURCE),
    "CFC": _market("CFC", "Cotton No. 1 Futures", "CZCE", 5, 40, 25, start_price=15_000, cost_source=CHINA_TRCOST_SOURCE),
}


def get_market(ticker: str) -> MarketSpec:
    key = ticker.upper()
    if key not in MARKETS:
        raise ValueError(f"Unknown market {ticker!r}. Available: {sorted(MARKETS)}")
    return MARKETS[key]


def apply_columbia_theme() -> None:
    mpl.rcParams.update(
        {
            "figure.figsize": (14, 6),
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": COLUMBIA_NAVY,
            "axes.labelcolor": COLUMBIA_NAVY,
            "axes.titlecolor": COLUMBIA_NAVY,
            "axes.titleweight": "bold",
            "axes.titlesize": 13,
            "axes.labelsize": 11,
            "axes.grid": True,
            "grid.color": COLUMBIA_ACCENT,
            "grid.alpha": 0.55,
            "grid.linewidth": 0.7,
            "xtick.color": COLUMBIA_NAVY,
            "ytick.color": COLUMBIA_NAVY,
            "legend.frameon": True,
            "legend.edgecolor": COLUMBIA_NAVY,
            "lines.linewidth": 1.3,
            "font.size": 11,
            "font.family": "DejaVu Sans",
        }
    )

def infer_bar_minutes_from_index(index: pd.Index | pd.DatetimeIndex) -> int:
    if len(index) < 2:
        return DEFAULT_BAR_MINUTES
    if not isinstance(index, pd.DatetimeIndex):
        index = pd.DatetimeIndex(index)
    diffs = index.to_series().diff().dropna().dt.total_seconds().div(60.0)
    diffs = diffs[(diffs > 0) & (diffs <= 120)]
    if len(diffs) == 0:
        return DEFAULT_BAR_MINUTES
    return int(round(float(diffs.mode().iloc[0])))


def active_bars_per_session(
    ticker: str,
    bar_minutes: int | None = None,
    df: pd.DataFrame | None = None,
) -> int:
    spec = get_market(ticker)
    resolved = int(bar_minutes or (infer_bar_minutes_from_index(df.index) if df is not None else DEFAULT_BAR_MINUTES))
    return max(1, int(round(spec.session_minutes / resolved)))


def bars_per_year(
    ticker: str,
    bar_minutes: int | None = None,
    df: pd.DataFrame | None = None,
) -> int:
    spec = get_market(ticker)
    return active_bars_per_session(ticker, bar_minutes=bar_minutes, df=df) * spec.trading_days_per_year


def bars_to_time(
    k: int,
    ticker: str,
    bar_minutes: int | None = None,
    df: pd.DataFrame | None = None,
) -> str:
    spec = get_market(ticker)
    resolved = int(bar_minutes or (infer_bar_minutes_from_index(df.index) if df is not None else DEFAULT_BAR_MINUTES))
    mins = k * resolved
    if mins < 60:
        return f"{mins}min"
    if mins < spec.session_minutes:
        return f"{mins / 60:.1f}hr"
    if spec.ticker == "BTC":
        return f"{mins / spec.session_minutes:.1f}d"
    return f"{mins / spec.session_minutes:.1f}sess"


def _scale_from_5min(values: np.ndarray, bar_minutes: int) -> np.ndarray:
    return np.maximum(1, np.rint(values.astype(float) * DEFAULT_BAR_MINUTES / float(bar_minutes)).astype(int))


def professor_reference_tau(ticker: str, bar_minutes: int = DEFAULT_BAR_MINUTES) -> int:
    spec = get_market(ticker)
    base = spec.bars_per_session
    if spec.ticker == "TY":
        base = 1440
    elif spec.ticker == "BTC":
        base = 1104
    return int(_scale_from_5min(np.array([base], dtype=int), int(bar_minutes))[0])


def professor_showcase_tau(ticker: str, bar_minutes: int = DEFAULT_BAR_MINUTES) -> int:
    spec = get_market(ticker)
    base = professor_reference_tau(ticker, bar_minutes=DEFAULT_BAR_MINUTES)
    if spec.ticker == "BTC":
        base = 3312
    return int(_scale_from_5min(np.array([base], dtype=int), int(bar_minutes))[0])


def professor_dense_q_grid(ticker: str, bar_minutes: int = DEFAULT_BAR_MINUTES) -> np.ndarray:
    spec = get_market(ticker)
    if spec.ticker == "TY":
        q_values = np.unique(
            np.r_[
                1,
                np.arange(2, 4801, 40, dtype=int),
                np.array([80, 160, 400, 800, 1200, 1440, 1600, 2000, 2400, 2880, 3360, 3840, 4320, 4800], dtype=int),
            ]
        )
        return _scale_from_5min(q_values.astype(int), int(bar_minutes))
    if spec.ticker == "BTC":
        q_values = np.unique(
            np.r_[
                1,
                np.arange(2, 5521, 24, dtype=int),
                np.array([276, 552, 828, 1104, 1380, 1656, 2208, 2760, 3312, 4140, 5520], dtype=int),
            ]
        )
        return _scale_from_5min(q_values.astype(int), int(bar_minutes))
    q_values = np.unique(np.r_[1, np.arange(2, spec.bars_per_session * 10 + 1, max(2, spec.bars_per_session // 4), dtype=int)])
    return _scale_from_5min(q_values.astype(int), int(bar_minutes))


def default_tf_grid(ticker: str, quick: bool = True, bar_minutes: int = DEFAULT_BAR_MINUTES) -> dict[str, np.ndarray]:
    ticker = ticker.upper()
    if quick:
        if ticker == "BTC":
            return {
                "L": _scale_from_5min(np.array([276, 552, 828, 1104, 1380, 1656, 2208], dtype=int), int(bar_minutes)),
                "S": np.arange(0.01, 0.07, 0.01, dtype=float),
            }
        if ticker == "TY":
            return {
                "L": _scale_from_5min(np.array([960, 1280, 1440, 1600, 1920, 2240, 3200], dtype=int), int(bar_minutes)),
                "S": np.array([0.01, 0.015, 0.02, 0.03, 0.04], dtype=float),
            }
        return {
            "L": _scale_from_5min(np.arange(1000, 10001, 1000, dtype=int), int(bar_minutes)),
            "S": np.arange(0.01, 0.06, 0.01, dtype=float),
        }
    return {
        "L": _scale_from_5min(np.arange(500, 10001, 10, dtype=int), int(bar_minutes)),
        "S": np.arange(0.005, 0.101, 0.001, dtype=float),
    }


def resolve_round_turn_cost(
    ticker: str,
    round_turn_cost: float | None = None,
    cost_multiplier: float = 1.0,
) -> float:
    spec = get_market(ticker)
    base = float(spec.slpg) if round_turn_cost is None else float(round_turn_cost)
    return base * float(cost_multiplier)


def default_mr_grid(ticker: str, quick: bool = True) -> dict[str, np.ndarray]:
    ticker = ticker.upper()
    if quick:
        vol_ma = np.array([24, 48, 80], dtype=int)
        if ticker == "BTC":
            vol_ma = np.array([24, 48, 96], dtype=int)
        return {
            "N1": np.array([0.5, 1.0, 1.5], dtype=float),
            "N2": np.array([0.5, 1.0], dtype=float),
            "VolLen": vol_ma,
            "MALen": vol_ma,
            "StpPct": np.array([0.01, 0.02, 0.03], dtype=float),
        }
    return {
        "N1": np.array([0.5, 1.0, 1.5, 2.0], dtype=float),
        "N2": np.array([0.5, 1.0, 1.5], dtype=float),
        "VolLen": np.array([24, 48, 80, 160], dtype=int),
        "MALen": np.array([24, 48, 80, 160, 320], dtype=int),
        "StpPct": np.array([0.01, 0.02, 0.03, 0.05], dtype=float),
    }
