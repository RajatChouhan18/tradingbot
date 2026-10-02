"""
txcore.analysis.mtf
~~~~~~~~~~~~~~~~~~~
Multi-Timeframe Confirmation (MTF) Engine.
Provides pure resampling algorithms, higher-timeframe trend evaluation,
and directional trend alignment verification across multiple timeframes.
Market-agnostic: operates on Forex, Equities, Crypto, and Commodities.
"""

from typing import Optional, Dict, Any, Tuple, Union
import pandas as pd
from txcore.models.types import Direction
from txcore.analysis.indicators import analyze_trend


def timeframe_to_pandas_freq(timeframe: str) -> str:
    """
    Converts standard timeframe string to pandas resample frequency alias.
    e.g. '1m' -> '1min', '5m' -> '5min', '15m' -> '15min', '1h' -> '1h', '1d' -> '1D'.
    """
    tf = timeframe.lower().strip()
    if tf.endswith("m") and tf[:-1].isdigit():
        return f"{tf[:-1]}min"
    elif tf.endswith("h") and tf[:-1].isdigit():
        return f"{tf[:-1]}h"
    elif tf.endswith("d") and tf[:-1].isdigit():
        return f"{tf[:-1]}D"
    return "15min"


def resample_to_timeframe(df: pd.DataFrame, target_timeframe: str) -> pd.DataFrame:
    """
    Resamples an OHLCV DataFrame from a lower timeframe into a higher timeframe.
    Pure vectorized function without network dependencies.
    Aggregation rules:
      - open: first
      - high: max
      - low: min
      - close: last
      - volume: sum
    """
    if df is None or df.empty or len(df) < 2:
        return df.copy() if df is not None else pd.DataFrame()

    clean = df.copy()
    clean["time"] = pd.to_datetime(clean["time"], utc=True)
    clean = clean.sort_values("time").drop_duplicates(subset=["time"]).set_index("time")

    freq = timeframe_to_pandas_freq(target_timeframe)
    agg_rules = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
    }
    if "volume" in clean.columns:
        agg_rules["volume"] = "sum"

    resampled = clean.resample(freq).agg(agg_rules).dropna(subset=["open", "high", "low", "close"])
    return resampled.reset_index()


def evaluate_mtf_trend(
    df: pd.DataFrame,
    base_timeframe: str = "5m",
    higher_timeframe: str = "15m",
    provider: Optional[Any] = None,
    symbol: str = "",
) -> Dict[str, Any]:
    """
    Evaluates trend regime on higher timeframe either by resampling local data
    or fetching higher timeframe candles directly from provider if available.
    """
    htf_df: Optional[pd.DataFrame] = None

    # Option A: Fetch directly from provider if provided
    if provider is not None and hasattr(provider, "get_candles") and symbol:
        try:
            htf_df = provider.get_candles(symbol, timeframe=higher_timeframe, lookback_bars=60)
        except Exception:
            htf_df = None

    # Option B: Resample local lower timeframe data
    if htf_df is None or htf_df.empty or len(htf_df) < 5:
        if df is not None and not df.empty and len(df) >= 10:
            htf_df = resample_to_timeframe(df, target_timeframe=higher_timeframe)

    if htf_df is None or len(htf_df) < 5:
        return {
            "symbol": symbol.upper() if symbol else "ASSET",
            "timeframe": higher_timeframe,
            "trend": "INSUFFICIENT_DATA",
            "summary": f"Insufficient bars to construct {higher_timeframe} trend context",
            "is_aligned": True,
        }

    trend_info = analyze_trend(htf_df, symbol=symbol, timeframe=higher_timeframe)
    return trend_info


def validate_mtf_confirmation(
    direction: Union[Direction, str],
    htf_trend: str,
    strict: bool = False,
) -> Tuple[bool, str]:
    """
    Verifies directional alignment between a lower-timeframe signal and higher-timeframe trend.
    
    Rules:
      - CALL Signal:
        - Blocked if HTF is STRONG_DOWNTREND (major counter-trend trap).
        - If strict=True, requires HTF in (STRONG_UPTREND, MODERATE_UPTREND).
        - Otherwise, permits sideways/neutral and moderate uptrends.
      - PUT Signal:
        - Blocked if HTF is STRONG_UPTREND (major counter-trend trap).
        - If strict=True, requires HTF in (STRONG_DOWNTREND, MODERATE_DOWNTREND).
        - Otherwise, permits sideways/neutral and moderate downtrends.
        
    Returns (is_confirmed: bool, reason: str).
    """
    dir_str = direction.value if isinstance(direction, Direction) else str(direction).upper()

    if dir_str == "CALL":
        if htf_trend == "STRONG_DOWNTREND":
            return False, "Counter-trend CALL blocked: higher timeframe is in STRONG_DOWNTREND."
        if strict and htf_trend not in ("STRONG_UPTREND", "MODERATE_UPTREND"):
            return False, f"Strict MTF: higher timeframe trend is {htf_trend}, not an uptrend."
        return True, f"MTF confirmed: higher timeframe trend is {htf_trend}."

    elif dir_str == "PUT":
        if htf_trend == "STRONG_UPTREND":
            return False, "Counter-trend PUT blocked: higher timeframe is in STRONG_UPTREND."
        if strict and htf_trend not in ("STRONG_DOWNTREND", "MODERATE_DOWNTREND"):
            return False, f"Strict MTF: higher timeframe trend is {htf_trend}, not a downtrend."
        return True, f"MTF confirmed: higher timeframe trend is {htf_trend}."

    return True, "Neutral direction."
