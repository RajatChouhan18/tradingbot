"""
txcore.analysis.patterns
~~~~~~~~~~~~~~~~~~~~~~~~
Multi-candle price action pattern recognition algorithms.
Directly implements Ishaq's BO Price Action book rules with boundary and tolerance guards.
"""

import math
import pandas as pd
from txcore.analysis.candle import candle_parts


def bullish_engulfing(df: pd.DataFrame, i: int, strict_wick_engulf: bool = False) -> bool:
    """
    Bullish Engulfing:
      Candle i-1 is Bearish (red).
      Candle i is Bullish (green).
      The body of candle i completely engulfs the body of candle i-1.
      Boundary tolerance: b.close >= a.open (allowing tick equality).
    """
    if i < 1 or i >= len(df):
        return False

    a = candle_parts(df.iloc[i - 1])
    b = candle_parts(df.iloc[i])

    if not (a.is_bearish and b.is_bullish):
        return False

    # Body engulfing condition
    body_engulfs = (b.open <= a.close or math.isclose(b.open, a.close, abs_tol=1e-6)) and (
        b.close >= a.open or math.isclose(b.close, a.open, abs_tol=1e-6)
    )

    if not body_engulfs:
        return False

    if strict_wick_engulf:
        return b.low <= a.low and b.high >= a.high

    return True


def bearish_engulfing(df: pd.DataFrame, i: int, strict_wick_engulf: bool = False) -> bool:
    """
    Bearish Engulfing:
      Candle i-1 is Bullish (green).
      Candle i is Bearish (red).
      The body of candle i completely engulfs the body of candle i-1.
      Boundary tolerance: b.close <= a.open (allowing tick equality).
    """
    if i < 1 or i >= len(df):
        return False

    a = candle_parts(df.iloc[i - 1])
    b = candle_parts(df.iloc[i])

    if not (a.is_bullish and b.is_bearish):
        return False

    # Body engulfing condition
    body_engulfs = (b.open >= a.close or math.isclose(b.open, a.close, abs_tol=1e-6)) and (
        b.close <= a.open or math.isclose(b.close, a.open, abs_tol=1e-6)
    )

    if not body_engulfs:
        return False

    if strict_wick_engulf:
        return b.high >= a.high and b.low <= a.low

    return True


def piercing_line(df: pd.DataFrame, i: int) -> bool:
    """
    Piercing Line:
      Candle i-1 is a substantial Bearish candle.
      Candle i opens below candle i-1's close/low.
      Candle i closes ABOVE the 50% midpoint of candle i-1's body, but BELOW candle i-1's open.
    """
    if i < 1 or i >= len(df):
        return False

    a = candle_parts(df.iloc[i - 1])
    b = candle_parts(df.iloc[i])

    if not (a.is_bearish and b.is_bullish):
        return False

    midpoint = (a.open + a.close) / 2.0

    return (
        (b.open < a.low or b.open < a.close)
        and (b.close > midpoint or math.isclose(b.close, midpoint, abs_tol=1e-6))
        and b.close < a.open
    )


def dark_cloud_cover(df: pd.DataFrame, i: int) -> bool:
    """
    Dark Cloud Cover:
      Candle i-1 is a substantial Bullish candle.
      Candle i opens above candle i-1's close/high.
      Candle i closes BELOW the 50% midpoint of candle i-1's body, but ABOVE candle i-1's open.
    """
    if i < 1 or i >= len(df):
        return False

    a = candle_parts(df.iloc[i - 1])
    b = candle_parts(df.iloc[i])

    if not (a.is_bullish and b.is_bearish):
        return False

    midpoint = (a.open + a.close) / 2.0

    return (
        (b.open > a.high or b.open > a.close)
        and (b.close < midpoint or math.isclose(b.close, midpoint, abs_tol=1e-6))
        and b.close > a.open
    )


def morning_star(df: pd.DataFrame, i: int) -> bool:
    """
    Morning Star (3-candle bullish reversal):
      1. Candle i-2 is strong Bearish.
      2. Candle i-1 is small-bodied (Doji or Spinning Top).
      3. Candle i is strong Bullish, closing well into Candle i-2's body.
    """
    if i < 2 or i >= len(df):
        return False

    c1 = candle_parts(df.iloc[i - 2])
    c2 = candle_parts(df.iloc[i - 1])
    c3 = candle_parts(df.iloc[i])

    if not (c1.is_bearish and c3.is_bullish):
        return False

    # Middle candle has small body
    if c2.body > c1.body * 0.40:
        return False

    # Third candle closes above middle of first candle
    mid1 = (c1.open + c1.close) / 2.0
    return c3.close > mid1


def evening_star(df: pd.DataFrame, i: int) -> bool:
    """
    Evening Star (3-candle bearish reversal):
      1. Candle i-2 is strong Bullish.
      2. Candle i-1 is small-bodied (Doji or Spinning Top).
      3. Candle i is strong Bearish, closing well into Candle i-2's body.
    """
    if i < 2 or i >= len(df):
        return False

    c1 = candle_parts(df.iloc[i - 2])
    c2 = candle_parts(df.iloc[i - 1])
    c3 = candle_parts(df.iloc[i])

    if not (c1.is_bullish and c3.is_bearish):
        return False

    # Middle candle has small body
    if c2.body > c1.body * 0.40:
        return False

    # Third candle closes below middle of first candle
    mid1 = (c1.open + c1.close) / 2.0
    return c3.close < mid1
