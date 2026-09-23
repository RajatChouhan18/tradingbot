"""
tests.test_strategy_engine
~~~~~~~~~~~~~~~~~~~~~~~~~~
End-to-end unit tests for PDFPriceActionStrategy state machine, retracement verification,
and entry readiness timing.
"""

from datetime import datetime, timedelta, timezone
import pandas as pd
import pytest

from txcore.models.types import Direction, PatternType, SignalStatus
from txcore.strategies.pdf_price_action import PDFPriceActionStrategy

t0 = datetime(2026, 9, 24, 0, 0, tzinfo=timezone.utc)


def build_ohlc_df(bars):
    data = []
    for idx, (o, h, l, c) in enumerate(bars):
        data.append({
            "time": t0 + timedelta(minutes=idx),
            "open": float(o),
            "high": float(h),
            "low": float(l),
            "close": float(c),
            "volume": 100.0,
        })
    return pd.DataFrame(data)


class TestPDFPriceActionStrategy:
    def setup_method(self):
        self.strategy = PDFPriceActionStrategy(scan_bars=8, lookback_sr=20)

    def test_bullish_engulfing_with_support_retracement_signal(self):
        """
        Creates a realistic 10-bar sequence:
          Bars 0-5: General background price action establishing support at 1.0850.
          Bar 6: Bearish candle (1.0870 -> 1.0852).
          Bar 7: Bullish Engulfing (1.0850 -> 1.0880).
          Bar 8: Retracement candle (weak bearish, touches support at 1.0850 and closes at 1.0860).
          Bar 9: Entry candle just completed (len = 10, entry_index = 9).
        """
        bars = [
            (1.0890, 1.0900, 1.0880, 1.0885),
            (1.0885, 1.0890, 1.0870, 1.0875),
            (1.0875, 1.0880, 1.0860, 1.0865),
            (1.0865, 1.0870, 1.0850, 1.0855),  # Established support at 1.0850
            (1.0855, 1.0875, 1.0852, 1.0870),
            (1.0870, 1.0880, 1.0865, 1.0875),
            (1.0875, 1.0880, 1.0852, 1.0855),  # Bar 6: Bearish
            (1.0850, 1.0885, 1.0848, 1.0880),  # Bar 7: Bullish Engulfing (index 7)
            (1.0880, 1.0882, 1.0848, 1.0865),  # Bar 8: Retracement touches support & rejects (weak bearish)
        ]
        df = build_ohlc_df(bars)

        # Retracement candle is Bar 8 (index 8). Entry candle is Bar 9.
        # len(df) is 9. Entry index is i + 2 = 7 + 2 = 9.
        # When len(df) == 9, entry is ready!
        signal = self.strategy.evaluate(df, symbol="EUR/USD")

        assert signal is not None
        assert signal.pair == "EUR/USD"
        assert signal.direction == Direction.CALL
        assert signal.pattern == PatternType.BULLISH_ENGULFING.value
        assert signal.status == SignalStatus.APPROVED
        assert signal.price == float(df.iloc[-1]["close"])

    def test_stale_setup_is_rejected(self):
        """
        Corner case: The setup completed 4 minutes ago.
        validate_entry must return False to avoid firing late signals.
        """
        bars = [
            (1.0890, 1.0900, 1.0880, 1.0885),
            (1.0885, 1.0890, 1.0870, 1.0875),
            (1.0875, 1.0880, 1.0860, 1.0865),
            (1.0865, 1.0870, 1.0850, 1.0855),
            (1.0855, 1.0875, 1.0852, 1.0870),
            (1.0870, 1.0880, 1.0865, 1.0875),
            (1.0875, 1.0880, 1.0852, 1.0855),  # Bar 6: Bearish
            (1.0850, 1.0885, 1.0848, 1.0880),  # Bar 7: Bullish Engulfing
            (1.0880, 1.0882, 1.0848, 1.0865),  # Bar 8: Retracement
            # Stale extra bars:
            (1.0865, 1.0890, 1.0860, 1.0885),  # Bar 9
            (1.0885, 1.0895, 1.0880, 1.0890),  # Bar 10
            (1.0890, 1.0905, 1.0885, 1.0900),  # Bar 11
        ]
        df = build_ohlc_df(bars)
        signal = self.strategy.evaluate(df, symbol="EUR/USD")
        assert signal is None

    def test_short_dataframe_returns_none(self):
        """Corner case: Dataframe has fewer than 5 bars."""
        bars = [(1.10, 1.11, 1.09, 1.105), (1.105, 1.11, 1.10, 1.108)]
        df = build_ohlc_df(bars)
        assert self.strategy.evaluate(df, symbol="EUR/USD") is None

    def test_bearish_engulfing_with_resistance_signal(self):
        bars = [
            (1.0800, 1.0830, 1.0790, 1.0820),
            (1.0820, 1.0850, 1.0815, 1.0845),
            (1.0845, 1.0870, 1.0840, 1.0865),
            (1.0865, 1.0890, 1.0860, 1.0885),  # Resistance at 1.0890
            (1.0885, 1.0888, 1.0860, 1.0865),
            (1.0865, 1.0880, 1.0860, 1.0875),
            (1.0875, 1.0888, 1.0870, 1.0885),  # Bar 6: Bullish
            (1.0890, 1.0895, 1.0855, 1.0860),  # Bar 7: Bearish Engulfing (index 7, Resistance = 1.0895)
            (1.0860, 1.0896, 1.0858, 1.0870),  # Bar 8: Retracement touches resistance (1.0896 >= 1.0895) & rejects (weak bullish)
        ]
        df = build_ohlc_df(bars)
        signal = self.strategy.evaluate(df, symbol="USD/JPY")

        assert signal is not None
        assert signal.direction == Direction.PUT
        assert signal.pattern == PatternType.BEARISH_ENGULFING.value
