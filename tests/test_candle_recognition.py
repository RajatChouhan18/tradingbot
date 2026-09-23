"""
tests.test_candle_recognition
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for single candle anatomy, geometry, and corner-case handling.
"""

import math
from datetime import datetime, timezone
import pandas as pd
import pytest

from txcore.models.types import Candle, CandleType
from txcore.analysis.candle import (
    candle_parts,
    is_doji,
    is_dragonfly_doji,
    is_gravestone_doji,
    is_hammer,
    is_inverted_hammer,
    is_shooting_star,
    is_spinning_top,
    is_marubozu,
    weak_bullish,
    weak_bearish,
    classify_candle,
)

t0 = datetime(2026, 9, 24, 0, 0, tzinfo=timezone.utc)


class TestCandleAnatomy:
    def test_candle_parts_standard(self):
        c = candle_parts({"time": t0, "open": 1.1000, "high": 1.1050, "low": 1.0980, "close": 1.1040})
        assert math.isclose(c.body, 0.0040)
        assert math.isclose(c.range, 0.0070)
        assert math.isclose(c.upper_wick, 0.0010)
        assert math.isclose(c.lower_wick, 0.0020)
        assert c.is_bullish is True
        assert c.is_bearish is False

    def test_candle_parts_defensive_clamp(self):
        """Corner case: Input has illogical high lower than close, or low higher than open."""
        c = candle_parts({"time": t0, "open": 1.1000, "high": 1.0900, "low": 1.1100, "close": 1.1050})
        assert c.high >= max(c.open, c.close)
        assert c.low <= min(c.open, c.close)

    def test_zero_range_candle(self):
        """Corner case: Flat bar with zero range (no ticks/volume). Must not divide by zero."""
        c = candle_parts({"time": t0, "open": 1.1000, "high": 1.1000, "low": 1.1000, "close": 1.1000})
        assert c.range == 0.0
        assert c.body == 0.0
        assert is_doji(c) is False
        assert is_hammer(c) is False
        assert is_spinning_top(c) is False
        assert is_marubozu(c) is False


class TestDojiRecognition:
    def test_perfect_doji(self):
        c = Candle(time=t0, open=1.1000, high=1.1050, low=1.0950, close=1.1000)
        assert is_doji(c) is True

    def test_doji_boundary_values(self):
        """Range = 0.0100. 10% threshold = 0.0010."""
        # 9% body -> True
        c_in = Candle(time=t0, open=1.1000, high=1.1050, low=1.0950, close=1.1009)
        assert is_doji(c_in) is True

        # Exactly 10% body -> True
        c_exact = Candle(time=t0, open=1.1000, high=1.1050, low=1.0950, close=1.1010)
        assert is_doji(c_exact) is True

        # 11% body -> False
        c_out = Candle(time=t0, open=1.1000, high=1.1050, low=1.0950, close=1.1012)
        assert is_doji(c_out) is False

    def test_dragonfly_doji(self):
        # Long lower wick (0.0080 of 0.0100 range), no upper wick
        c = Candle(time=t0, open=1.1098, high=1.1100, low=1.1000, close=1.1100)
        assert is_dragonfly_doji(c) is True
        assert is_gravestone_doji(c) is False

    def test_gravestone_doji(self):
        # Long upper wick (0.0080 of 0.0100 range), no lower wick
        c = Candle(time=t0, open=1.1002, high=1.1100, low=1.1000, close=1.1000)
        assert is_gravestone_doji(c) is True
        assert is_dragonfly_doji(c) is False


class TestHammerAndStarRecognition:
    def test_classic_hammer(self):
        # Body = 0.0020 (1.1040 to 1.1060). Lower wick = 0.0050 (>= 2x body), upper wick = 0.0003 (<= 0.3x body)
        c = Candle(time=t0, open=1.1040, high=1.1063, low=1.0990, close=1.1060)
        assert is_hammer(c) is True

    def test_hammer_invalid_if_large_upper_wick(self):
        # Lower wick is long, but upper wick is also too long (not a hammer)
        c = Candle(time=t0, open=1.1040, high=1.1090, low=1.0990, close=1.1060)
        assert is_hammer(c) is False

    def test_inverted_hammer(self):
        # Body = 0.0020. Upper wick = 0.0050 (>= 2x body), lower wick = 0.0002
        c = Candle(time=t0, open=1.1005, high=1.1075, low=1.1000, close=1.1025)
        assert is_inverted_hammer(c) is True

    def test_shooting_star(self):
        # Bearish body = 0.0020. Upper wick = 0.0050, lower wick = 0.0001
        c = Candle(time=t0, open=1.1025, high=1.1075, low=1.1000, close=1.1005)
        assert is_shooting_star(c) is True


class TestMarubozuAndWeakCandles:
    def test_marubozu_bullish(self):
        # Range = 0.0100, Body = 0.0096 (>= 90% range), wicks = 0.0002 each
        c = Candle(time=t0, open=1.1002, high=1.1100, low=1.1000, close=1.1098)
        assert is_marubozu(c) is True
        assert c.is_bullish is True

    def test_weak_bullish(self):
        """Body <= 1.5x max(wicks). Close > Open."""
        # Body = 0.0010, upper wick = 0.0020. 0.0010 <= 0.0020 * 1.5 -> True
        c = Candle(time=t0, open=1.1000, high=1.1030, low=1.0995, close=1.1010)
        assert weak_bullish(c) is True

    def test_weak_bearish(self):
        """Body <= 1.5x max(wicks). Close < Open."""
        # Body = 0.0010, lower wick = 0.0020. Close < Open -> True
        c = Candle(time=t0, open=1.1010, high=1.1015, low=1.0980, close=1.1000)
        assert weak_bearish(c) is True

    def test_classifier_fallback(self):
        c = Candle(time=t0, open=1.1000, high=1.1060, low=1.0990, close=1.1050)
        ctype = classify_candle(c)
        assert ctype in (CandleType.STANDARD_BULLISH, CandleType.MARUBOZU_BULLISH, CandleType.WEAK_BULLISH)
