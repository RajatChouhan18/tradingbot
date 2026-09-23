"""
tests.test_levels_and_rejections
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for dynamic Support & Resistance, trend determination, and level rejections.
"""

from datetime import datetime, timedelta, timezone
import pandas as pd
import pytest

from txcore.models.types import Candle
from txcore.analysis.levels import (
    key_levels,
    prior_downtrend,
    prior_uptrend,
    rejects_support,
    rejects_resistance,
)

t0 = datetime(2026, 9, 24, 0, 0, tzinfo=timezone.utc)


def make_df(rows):
    data = []
    for idx, r in enumerate(rows):
        data.append({
            "time": t0 + timedelta(minutes=idx),
            "open": r[0],
            "high": r[1],
            "low": r[2],
            "close": r[3],
        })
    return pd.DataFrame(data)


class TestKeyLevels:
    def test_key_levels_standard(self):
        df = make_df([
            [1.100, 1.108, 1.095, 1.102],
            [1.102, 1.112, 1.101, 1.110],  # High = 1.112
            [1.110, 1.111, 1.090, 1.092],  # Low = 1.090
            [1.092, 1.099, 1.091, 1.098],
        ])
        support, resistance = key_levels(df, 3, lookback=10)
        assert support == 1.090
        assert resistance == 1.112

    def test_key_levels_flat_window(self):
        """Corner case: All bars in lookback are identical flat price."""
        df = make_df([
            [1.100, 1.100, 1.100, 1.100],
            [1.100, 1.100, 1.100, 1.100],
        ])
        support, resistance = key_levels(df, 1, lookback=10)
        assert support == 1.100
        assert resistance == 1.100


class TestTrendDetection:
    def test_prior_downtrend_valid(self):
        # 5 consecutive bars moving down
        df = make_df([
            [1.110, 1.112, 1.105, 1.106],
            [1.106, 1.107, 1.102, 1.103],
            [1.103, 1.104, 1.099, 1.100],
            [1.100, 1.101, 1.095, 1.096],
            [1.096, 1.097, 1.090, 1.091],
        ])
        assert prior_downtrend(df, end_index=5, bars=5) is True
        assert prior_uptrend(df, end_index=5, bars=5) is False

    def test_prior_downtrend_too_few_bars(self):
        df = make_df([
            [1.110, 1.112, 1.105, 1.106],
            [1.106, 1.107, 1.102, 1.103],
        ])
        assert prior_downtrend(df, end_index=2, bars=5) is False

    def test_prior_uptrend_valid(self):
        # 5 consecutive bars moving up
        df = make_df([
            [1.090, 1.094, 1.089, 1.093],
            [1.093, 1.098, 1.092, 1.097],
            [1.097, 1.102, 1.096, 1.101],
            [1.101, 1.105, 1.100, 1.104],
            [1.104, 1.110, 1.103, 1.109],
        ])
        assert prior_uptrend(df, end_index=5, bars=5) is True
        assert prior_downtrend(df, end_index=5, bars=5) is False


class TestRejections:
    def test_rejects_support_valid(self):
        # Support at 1.0850.
        # Candle low dips to 1.0842 (pierces), but closes at 1.0858 (above).
        c = Candle(time=t0, open=1.0860, high=1.0865, low=1.0842, close=1.0858)
        assert rejects_support(c, support=1.0850) is True

    def test_rejects_support_breakdown_fails(self):
        # Candle breaks support and closes below 1.0850 at 1.0840 -> Not a rejection
        c = Candle(time=t0, open=1.0860, high=1.0865, low=1.0835, close=1.0840)
        assert rejects_support(c, support=1.0850) is False

    def test_rejects_support_no_touch_fails(self):
        # Candle low is 1.0860, never touches support at 1.0850
        c = Candle(time=t0, open=1.0870, high=1.0880, low=1.0860, close=1.0875)
        assert rejects_support(c, support=1.0850) is False

    def test_rejects_resistance_valid(self):
        # Resistance at 1.1050.
        # Candle high reaches 1.1062, but closes at 1.1042 (below).
        c = Candle(time=t0, open=1.1035, high=1.1062, low=1.1030, close=1.1042)
        assert rejects_resistance(c, resistance=1.1050) is True

    def test_rejects_resistance_breakout_fails(self):
        # Candle breaks resistance and closes above at 1.1065 -> Not a rejection
        c = Candle(time=t0, open=1.1035, high=1.1070, low=1.1030, close=1.1065)
        assert rejects_resistance(c, resistance=1.1050) is False
