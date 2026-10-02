"""
txcore.analysis.levels
~~~~~~~~~~~~~~~~~~~~~~
Dynamic Support & Resistance detection, trend classification, and level rejection analysis.
"""

from typing import Tuple, Union, Dict, Any
import pandas as pd
from txcore.models.types import Candle
from txcore.analysis.candle import candle_parts


def key_levels(df: pd.DataFrame, i: int, lookback: int = 20) -> Tuple[float, float]:
    """
    Computes local dynamic Support and Resistance levels from the lookback window.
    Support = minimum low in lookback window.
    Resistance = maximum high in lookback window.
    Corner case: If lookback window is 0 or flat, falls back to current bar's low/high.
    """
    start = max(0, i - lookback)
    window = df.iloc[start : max(start + 1, i + 1)]

    support = float(window["low"].min())
    resistance = float(window["high"].max())

    # Fallback guard in case window had identical prices
    if support == resistance:
        current = df.iloc[i]
        support = float(current["low"])
        resistance = float(current["high"])

    return round(support, 6), round(resistance, 6)


def prior_downtrend(df: pd.DataFrame, end_index: int, bars: int = 5) -> bool:
    """
    Verifies that the market was in a downtrend preceding the setup.
    Requires at least 4 bars and checks lower highs / lower closes.
    """
    start = max(0, end_index - bars)
    x = df.iloc[start:end_index]
    if len(x) < 4:
        return False

    first_close = float(x.iloc[0]["close"])
    last_close = float(x.iloc[-1]["close"])
    max_high = float(x["high"].max())
    last_high = float(x.iloc[-1]["high"])

    return (last_close < first_close) and (last_high <= max_high)


def prior_uptrend(df: pd.DataFrame, end_index: int, bars: int = 5) -> bool:
    """
    Verifies that the market was in an uptrend preceding the setup.
    Requires at least 4 bars and checks higher lows / higher closes.
    """
    start = max(0, end_index - bars)
    x = df.iloc[start:end_index]
    if len(x) < 4:
        return False

    first_close = float(x.iloc[0]["close"])
    last_close = float(x.iloc[-1]["close"])
    min_low = float(x["low"].min())
    last_low = float(x.iloc[-1]["low"])

    return (last_close > first_close) and (last_low >= min_low)


def rejects_support(candle: Union[Candle, pd.Series, Dict[str, Any]], support: float) -> bool:
    """
    Rejection of Support:
      - The lower shadow touches or dips below support: candle.low <= support
      - The body closes safely above support: candle.close >= support
      - Strong lower wick showing buyers stepping in.
    """
    c = candle_parts(candle)
    touches_level = c.low <= support
    closes_above = c.close >= support
    has_wick = c.lower_wick > 0 or (c.close > c.low)

    return touches_level and closes_above and has_wick


def rejects_resistance(candle: Union[Candle, pd.Series, Dict[str, Any]], resistance: float) -> bool:
    """
    Rejection of Resistance:
      - The upper shadow touches or pierces above resistance: candle.high >= resistance
      - The body closes safely below resistance: candle.close <= resistance
      - Strong upper wick showing sellers stepping in.
    """
    c = candle_parts(candle)
    touches_level = c.high >= resistance
    closes_below = c.close <= resistance
    has_wick = c.upper_wick > 0 or (c.high > c.close)

    return touches_level and closes_below and has_wick
