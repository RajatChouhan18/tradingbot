"""
txcore.analysis.candle
~~~~~~~~~~~~~~~~~~~~~~
Single candle geometry, anatomy, and pattern classification engine.
Designed with mathematical precision, zero-division safety, and floating-point tolerance.
"""

import math
from typing import Union, Dict, Any
import pandas as pd
from txcore.models.types import Candle, CandleType


def candle_parts(row: Union[pd.Series, Dict[str, Any], Candle]) -> Candle:
    """
    Normalizes any row or dictionary representation into a strongly-typed Candle.
    Safely calculates body, upper wick, and lower wick.
    """
    if isinstance(row, Candle):
        return row

    t = row.get("time") if "time" in row else row.name
    o = float(row["open"])
    h = float(row["high"])
    l = float(row["low"])
    c = float(row["close"])
    v = float(row.get("volume", 0.0))

    # Defensive sanity check: high cannot be lower than max(o, c), low cannot be higher than min(o, c)
    h = max(h, o, c)
    l = min(l, o, c)

    return Candle(time=t, open=o, high=h, low=l, close=c, volume=v)


def is_doji(candle: Union[Candle, pd.Series, Dict[str, Any]], threshold: float = 0.10) -> bool:
    """
    Doji: Body is <= 10% of total range.
    Corner cases handled: zero-range bars return False.
    """
    c = candle_parts(candle)
    rng = c.range
    if rng <= 0 or math.isclose(rng, 0.0, abs_tol=1e-9):
        return False
    return c.body <= rng * threshold


def is_dragonfly_doji(candle: Union[Candle, pd.Series, Dict[str, Any]], threshold: float = 0.10) -> bool:
    """
    Dragonfly Doji: Small body near the high with a long lower shadow and virtually no upper shadow.
    Inherently bullish reversal signal (buyers strongly rejected lows).
    """
    c = candle_parts(candle)
    if not is_doji(c, threshold):
        return False
    rng = c.range
    return c.upper_wick <= rng * 0.10 and c.lower_wick >= rng * 0.55


def is_gravestone_doji(candle: Union[Candle, pd.Series, Dict[str, Any]], threshold: float = 0.10) -> bool:
    """
    Gravestone Doji: Small body near the low with a long upper shadow and virtually no lower shadow.
    Inherently bearish reversal signal (sellers strongly rejected highs).
    """
    c = candle_parts(candle)
    if not is_doji(c, threshold):
        return False
    rng = c.range
    return c.lower_wick <= rng * 0.10 and c.upper_wick >= rng * 0.55


def is_long_legged_doji(candle: Union[Candle, pd.Series, Dict[str, Any]], threshold: float = 0.10) -> bool:
    """
    Long-Legged Doji: Tiny body with long upper and lower shadows, reflecting intense two-sided indecision.
    """
    c = candle_parts(candle)
    if not is_doji(c, threshold):
        return False
    rng = c.range
    return c.upper_wick >= rng * 0.25 and c.lower_wick >= rng * 0.25


def is_bullish_doji(candle: Union[Candle, pd.Series, Dict[str, Any]], threshold: float = 0.10) -> bool:
    """
    Bullish Doji:
    Meets doji criteria and reflects net bullish pressure:
      1. Dragonfly Doji (inherent bullish rejection of lows), OR
      2. Dominant lower wick rejection (lower_wick > 1.3x upper_wick), OR
      3. Balanced wicks where close > open and sellers did NOT dominate the upper wick.
    Guarantees that a candle with massive upper wick selling rejection is NEVER labeled Bullish Doji.
    """
    c = candle_parts(candle)
    if not is_doji(c, threshold):
        return False
    if is_dragonfly_doji(c, threshold):
        return True
    if is_gravestone_doji(c, threshold):
        return False

    # Dominant buyer rejection at lows
    if c.lower_wick > c.upper_wick * 1.3:
        return True

    # Sellers dominated the upper wick -> CANNOT be bullish
    if c.upper_wick > c.lower_wick * 1.3:
        return False

    # Balanced wicks: color determines bias only if close > open and not floating-point flat
    return c.is_bullish and not math.isclose(c.close, c.open, abs_tol=1e-5)


def is_bearish_doji(candle: Union[Candle, pd.Series, Dict[str, Any]], threshold: float = 0.10) -> bool:
    """
    Bearish Doji:
    Meets doji criteria and reflects net bearish pressure:
      1. Gravestone Doji (inherent bearish rejection of highs), OR
      2. Dominant upper wick rejection (upper_wick > 1.3x lower_wick), OR
      3. Balanced wicks where close < open and buyers did NOT dominate the lower wick.
    Guarantees that a candle with massive lower wick buying support is NEVER labeled Bearish Doji.
    """
    c = candle_parts(candle)
    if not is_doji(c, threshold):
        return False
    if is_gravestone_doji(c, threshold):
        return True
    if is_dragonfly_doji(c, threshold):
        return False

    # Dominant seller rejection at highs
    if c.upper_wick > c.lower_wick * 1.3:
        return True

    # Buyers dominated the lower wick -> CANNOT be bearish
    if c.lower_wick > c.upper_wick * 1.3:
        return False

    # Balanced wicks: color determines bias only if close < open and not floating-point flat
    return c.is_bearish and not math.isclose(c.close, c.open, abs_tol=1e-5)


def is_neutral_doji(candle: Union[Candle, pd.Series, Dict[str, Any]], threshold: float = 0.10) -> bool:
    """
    Neutral Doji: Meets doji criteria with balanced shadows and flat or indeterminate delta.
    """
    c = candle_parts(candle)
    if not is_doji(c, threshold):
        return False
    if is_dragonfly_doji(c, threshold) or is_gravestone_doji(c, threshold):
        return False
    return not is_bullish_doji(c, threshold) and not is_bearish_doji(c, threshold)


def is_hammer(candle: Union[Candle, pd.Series, Dict[str, Any]]) -> bool:
    """
    Hammer: Lower shadow at least 2x the body, tiny or absent upper shadow, body at upper end.
    """
    c = candle_parts(candle)
    rng = c.range
    if rng <= 0 or c.body <= 0:
        return False
    return (
        c.lower_wick >= (c.body * 2.0)
        and c.upper_wick <= max(c.body * 0.30, rng * 0.05)
    )


def is_inverted_hammer(candle: Union[Candle, pd.Series, Dict[str, Any]]) -> bool:
    """
    Inverted Hammer: Upper shadow at least 2x the body, tiny or absent lower shadow, body at lower end.
    """
    c = candle_parts(candle)
    rng = c.range
    if rng <= 0 or c.body <= 0:
        return False
    return (
        c.upper_wick >= (c.body * 2.0)
        and c.lower_wick <= max(c.body * 0.30, rng * 0.05)
    )


def is_shooting_star(candle: Union[Candle, pd.Series, Dict[str, Any]]) -> bool:
    """
    Shooting Star: Bearish reversal equivalent of Inverted Hammer.
    Long upper shadow, small body near the lower range, tiny or absent lower wick.
    """
    c = candle_parts(candle)
    rng = c.range
    if rng <= 0 or c.body <= 0:
        return False
    return (
        c.upper_wick >= (c.body * 2.0)
        and c.lower_wick <= max(c.body * 0.25, rng * 0.05)
    )


def is_spinning_top(candle: Union[Candle, pd.Series, Dict[str, Any]]) -> bool:
    """
    Spinning Top: Small real body with upper and lower shadows each greater than or equal to the body.
    """
    c = candle_parts(candle)
    rng = c.range
    if rng <= 0:
        return False
    return (
        c.body <= rng * 0.35
        and c.upper_wick >= c.body
        and c.lower_wick >= c.body
    )


def is_marubozu(candle: Union[Candle, pd.Series, Dict[str, Any]], tolerance: float = 0.05) -> bool:
    """
    Marubozu: Substantial body with almost no upper or lower wicks (< 5% of range each).
    """
    c = candle_parts(candle)
    rng = c.range
    if rng <= 0:
        return False
    return (
        c.body >= rng * (1.0 - 2 * tolerance)
        and c.upper_wick <= rng * tolerance
        and c.lower_wick <= rng * tolerance
    )


def weak_bullish(candle: Union[Candle, pd.Series, Dict[str, Any]]) -> bool:
    """
    Weak Bullish (from BO Price Action Book):
    Close > Open, but body is smaller than or equal to 1.5x the larger of the two wicks.
    Represents buying exhaustion / weak retracement.
    """
    c = candle_parts(candle)
    if not c.is_bullish:
        return False
    return c.body <= max(c.upper_wick, c.lower_wick) * 1.5


def weak_bearish(candle: Union[Candle, pd.Series, Dict[str, Any]]) -> bool:
    """
    Weak Bearish (from BO Price Action Book):
    Close < Open, but body is smaller than or equal to 1.5x the larger of the two wicks.
    Represents selling exhaustion / weak retracement.
    """
    c = candle_parts(candle)
    if not c.is_bearish:
        return False
    return c.body <= max(c.upper_wick, c.lower_wick) * 1.5


def classify_candle(candle: Union[Candle, pd.Series, Dict[str, Any]]) -> CandleType:
    """
    Comprehensive rule-based classifier assigning primary candle type.
    Ensures that rejection-based Dojis and Hammers are never inverted by floating-point deltas.
    """
    c = candle_parts(candle)
    rng = c.range
    if rng <= 0 or math.isclose(rng, 0.0, abs_tol=1e-9):
        return CandleType.NEUTRAL_DOJI

    if is_dragonfly_doji(c):
        return CandleType.DRAGONFLY_DOJI
    if is_gravestone_doji(c):
        return CandleType.GRAVESTONE_DOJI
    if is_doji(c):
        if is_bullish_doji(c):
            return CandleType.BULLISH_DOJI
        elif is_bearish_doji(c):
            return CandleType.BEARISH_DOJI
        else:
            return CandleType.NEUTRAL_DOJI
    if is_hammer(c):
        return CandleType.HAMMER
    if is_inverted_hammer(c):
        return CandleType.INVERTED_HAMMER
    if is_shooting_star(c):
        return CandleType.SHOOTING_STAR
    if is_spinning_top(c):
        return CandleType.SPINNING_TOP
    if is_marubozu(c):
        return CandleType.MARUBOZU_BULLISH if c.is_bullish else CandleType.MARUBOZU_BEARISH
    if weak_bullish(c):
        return CandleType.WEAK_BULLISH
    if weak_bearish(c):
        return CandleType.WEAK_BEARISH

    return CandleType.STANDARD_BULLISH if c.is_bullish else CandleType.STANDARD_BEARISH

