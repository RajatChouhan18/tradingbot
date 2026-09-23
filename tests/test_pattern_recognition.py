"""
tests.test_pattern_recognition
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for multi-candle patterns with difficult boundary conditions.
"""

from datetime import datetime, timedelta, timezone
import pandas as pd
import pytest

from txcore.analysis.patterns import (
    bullish_engulfing,
    bearish_engulfing,
    piercing_line,
    dark_cloud_cover,
    morning_star,
    evening_star,
)

t0 = datetime(2026, 9, 24, 0, 0, tzinfo=timezone.utc)


def make_df(rows):
    """Helper to convert list of [open, high, low, close] into DataFrame with UTC timestamps."""
    data = []
    for idx, r in enumerate(rows):
        data.append({
            "time": t0 + timedelta(minutes=idx),
            "open": r[0],
            "high": r[1],
            "low": r[2],
            "close": r[3],
            "volume": 100.0,
        })
    return pd.DataFrame(data)


class TestEngulfingPatterns:
    def test_bullish_engulfing_standard(self):
        # Bar 0: Bearish (1.1050 -> 1.1010)
        # Bar 1: Bullish (1.1005 -> 1.1060) completely engulfing
        df = make_df([
            [1.1050, 1.1060, 1.1000, 1.1010],
            [1.1005, 1.1070, 1.1000, 1.1060],
        ])
        assert bullish_engulfing(df, 1) is True
        assert bearish_engulfing(df, 1) is False

    def test_bullish_engulfing_exact_tick_equality(self):
        """Corner case: Bar 1 opens exactly at Bar 0 close and closes exactly at Bar 0 open."""
        df = make_df([
            [1.1050, 1.1060, 1.1000, 1.1010],
            [1.1010, 1.1060, 1.1000, 1.1050],
        ])
        assert bullish_engulfing(df, 1) is True

    def test_bullish_engulfing_partial_reject(self):
        """Bar 1 does NOT reach Bar 0 open -> Not an engulfing."""
        df = make_df([
            [1.1050, 1.1060, 1.1000, 1.1010],
            [1.1010, 1.1060, 1.1000, 1.1040],
        ])
        assert bullish_engulfing(df, 1) is False

    def test_bullish_engulfing_wrong_colors(self):
        """Two green candles -> cannot be a Bullish Engulfing."""
        df = make_df([
            [1.1010, 1.1040, 1.1000, 1.1030],
            [1.1025, 1.1070, 1.1020, 1.1060],
        ])
        assert bullish_engulfing(df, 1) is False

    def test_bearish_engulfing_standard(self):
        # Bar 0: Bullish (1.1010 -> 1.1040)
        # Bar 1: Bearish (1.1045 -> 1.1000) completely engulfing
        df = make_df([
            [1.1010, 1.1050, 1.1000, 1.1040],
            [1.1045, 1.1060, 1.0990, 1.1000],
        ])
        assert bearish_engulfing(df, 1) is True
        assert bullish_engulfing(df, 1) is False

    def test_bearish_engulfing_exact_tick_equality(self):
        df = make_df([
            [1.1010, 1.1050, 1.1000, 1.1040],
            [1.1040, 1.1050, 1.1000, 1.1010],
        ])
        assert bearish_engulfing(df, 1) is True


class TestPiercingAndDarkCloud:
    def test_piercing_line_valid(self):
        # Bar 0: Bearish (1.1050 -> 1.1010). Midpoint = 1.1030
        # Bar 1: Opens below close at 1.1000, closes above midpoint at 1.1035 (< 1.1050)
        df = make_df([
            [1.1050, 1.1060, 1.1000, 1.1010],
            [1.1000, 1.1040, 1.0990, 1.1035],
        ])
        assert piercing_line(df, 1) is True

    def test_piercing_line_below_midpoint_fails(self):
        # Bar 0: Bearish (1.1050 -> 1.1010). Midpoint = 1.1030
        # Bar 1: Closes at 1.1025 (below 50% midpoint) -> Fails
        df = make_df([
            [1.1050, 1.1060, 1.1000, 1.1010],
            [1.1000, 1.1030, 1.0990, 1.1025],
        ])
        assert piercing_line(df, 1) is False

    def test_piercing_line_exceeding_open_fails(self):
        # Closes at 1.1055 (> 1.1050) -> That's an engulfing, not a piercing line
        df = make_df([
            [1.1050, 1.1060, 1.1000, 1.1010],
            [1.1000, 1.1060, 1.0990, 1.1055],
        ])
        assert piercing_line(df, 1) is False

    def test_dark_cloud_cover_valid(self):
        # Bar 0: Bullish (1.1010 -> 1.1050). Midpoint = 1.1030
        # Bar 1: Opens at 1.1055, closes below midpoint at 1.1025 (> 1.1010)
        df = make_df([
            [1.1010, 1.1052, 1.1005, 1.1050],
            [1.1055, 1.1060, 1.1020, 1.1025],
        ])
        assert dark_cloud_cover(df, 1) is True

    def test_dark_cloud_cover_above_midpoint_fails(self):
        # Closes at 1.1035 (above 50% midpoint) -> Fails
        df = make_df([
            [1.1010, 1.1052, 1.1005, 1.1050],
            [1.1055, 1.1060, 1.1030, 1.1035],
        ])
        assert dark_cloud_cover(df, 1) is False


class TestIndexBounds:
    def test_index_zero_does_not_crash(self):
        df = make_df([[1.10, 1.11, 1.09, 1.105]])
        assert bullish_engulfing(df, 0) is False
        assert bearish_engulfing(df, 0) is False
        assert piercing_line(df, 0) is False
        assert dark_cloud_cover(df, 0) is False
        assert morning_star(df, 0) is False

    def test_index_out_of_bounds_does_not_crash(self):
        df = make_df([[1.10, 1.11, 1.09, 1.105], [1.105, 1.12, 1.10, 1.115]])
        assert bullish_engulfing(df, 99) is False
        assert bearish_engulfing(df, 99) is False
