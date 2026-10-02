"""
txcore.strategies.pdf_price_action
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Pure Price Action Strategy implementation based on 'BO Price Action Book by Ishaq's Binary Academy'.
Contains the complete 4-pattern state machine, dynamic S/R detection, retracement verification,
and strict entry-timing validation.
"""

from typing import Optional
import pandas as pd
from txcore.models.types import Signal, SetupResult, Direction, PatternType, SignalStatus
from txcore.strategies.base import BaseStrategy
from txcore.analysis.candle import weak_bullish, weak_bearish
from txcore.analysis.patterns import (
    bullish_engulfing,
    bearish_engulfing,
    piercing_line,
    dark_cloud_cover,
)
from txcore.analysis.levels import (
    key_levels,
    prior_downtrend,
    prior_uptrend,
    rejects_support,
    rejects_resistance,
)


class PDFPriceActionStrategy(BaseStrategy):
    """
    Implements Ishaq's 4 core Price Action setups:
      1. Bullish Engulfing with Support Retracement
      2. Bearish Engulfing with Resistance Retracement
      3. Piercing Line with Prior Downtrend & 50% Body Retracement
      4. Dark Cloud Cover with Prior Uptrend & 50% Body Retracement
    """

    def __init__(self, scan_bars: int = 8, lookback_sr: int = 20):
        self.scan_bars = scan_bars
        self.lookback_sr = lookback_sr

    def find_setup(self, df: pd.DataFrame) -> Optional[SetupResult]:
        """
        Scans recent completed candles for a valid pattern + retracement setup.
        """
        n = len(df)
        if n < 5:
            return None

        for i in range(max(1, n - self.scan_bars), n - 1):
            # 1. Bullish Engulfing
            if bullish_engulfing(df, i):
                support, _ = key_levels(df, i, lookback=self.lookback_sr)
                retracement = df.iloc[i + 1]

                if weak_bearish(retracement) and rejects_support(retracement, support):
                    return SetupResult(
                        direction=Direction.CALL,
                        pattern=PatternType.BULLISH_ENGULFING,
                        pattern_index=i,
                        entry_index=i + 2,
                        level=support,
                        reason="Retracement touched support, rejected and formed weak bearish candle.",
                    )

                if float(retracement["close"]) < support:
                    second = df.iloc[i + 2] if i + 2 < n else None
                    if second is not None and rejects_support(second, support):
                        return SetupResult(
                            direction=Direction.CALL,
                            pattern=PatternType.BULLISH_ENGULFING,
                            pattern_index=i,
                            entry_index=i + 3,
                            level=support,
                            reason="Second retracement touched support and rejected.",
                        )

            # 2. Bearish Engulfing
            if bearish_engulfing(df, i):
                _, resistance = key_levels(df, i, lookback=self.lookback_sr)
                retracement = df.iloc[i + 1]

                if weak_bullish(retracement) and rejects_resistance(retracement, resistance):
                    return SetupResult(
                        direction=Direction.PUT,
                        pattern=PatternType.BEARISH_ENGULFING,
                        pattern_index=i,
                        entry_index=i + 2,
                        level=resistance,
                        reason="Retracement touched resistance, rejected and formed weak bullish candle.",
                    )

                if float(retracement["close"]) > resistance:
                    second = df.iloc[i + 2] if i + 2 < n else None
                    if second is not None and rejects_resistance(second, resistance):
                        return SetupResult(
                            direction=Direction.PUT,
                            pattern=PatternType.BEARISH_ENGULFING,
                            pattern_index=i,
                            entry_index=i + 3,
                            level=resistance,
                            reason="Second retracement touched resistance and rejected.",
                        )

            # 3. Piercing Line
            if piercing_line(df, i) and prior_downtrend(df, i):
                a_open = float(df.iloc[i - 1]["open"])
                a_close = float(df.iloc[i - 1]["close"])
                pattern_50 = (a_open + a_close) / 2.0
                support, _ = key_levels(df, i, lookback=self.lookback_sr)
                retracement = df.iloc[i + 1]

                if float(retracement["close"]) > pattern_50:
                    if rejects_support(retracement, support):
                        return SetupResult(
                            direction=Direction.CALL,
                            pattern=PatternType.PIERCING_LINE,
                            pattern_index=i,
                            entry_index=i + 2,
                            level=support,
                            reason="Retracement closed above 50% level and rejected support.",
                        )

                if float(retracement["close"]) < support:
                    second = df.iloc[i + 2] if i + 2 < n else None
                    if second is not None and rejects_support(second, support):
                        return SetupResult(
                            direction=Direction.CALL,
                            pattern=PatternType.PIERCING_LINE,
                            pattern_index=i,
                            entry_index=i + 3,
                            level=support,
                            reason="Second candle touched key level and rejected.",
                        )

            # 4. Dark Cloud Cover
            if dark_cloud_cover(df, i) and prior_uptrend(df, i):
                _, resistance = key_levels(df, i, lookback=self.lookback_sr)
                retracement = df.iloc[i + 1]

                if rejects_resistance(retracement, resistance):
                    return SetupResult(
                        direction=Direction.PUT,
                        pattern=PatternType.DARK_CLOUD_COVER,
                        pattern_index=i,
                        entry_index=i + 2,
                        level=resistance,
                        reason="Retracement touched resistance and rejected.",
                    )

                if weak_bullish(retracement):
                    return SetupResult(
                        direction=Direction.PUT,
                        pattern=PatternType.DARK_CLOUD_COVER,
                        pattern_index=i,
                        entry_index=i + 2,
                        level=resistance,
                        reason="No rejection; retracement closed as weak bullish candle.",
                    )

        return None

    def validate_entry(self, df: pd.DataFrame, setup: SetupResult) -> bool:
        """
        Confirms entry readiness.
        Entry is valid if the confirmation bar has just closed.
        Specifically, entry_index must be equal to len(df) or len(df) - 1.
        """
        n = len(df)
        return setup.entry_index == n or setup.entry_index == n - 1

    def evaluate(self, df: pd.DataFrame, symbol: str) -> Optional[Signal]:
        """
        Evaluates completed bars, verifies retracement rejection, and returns an approved Signal.
        """
        setup = self.find_setup(df)
        if not setup:
            return None

        if not self.validate_entry(df, setup):
            return None

        pattern_row = df.iloc[setup.pattern_index]
        entry_row = df.iloc[-1]

        return Signal(
            pair=symbol,
            direction=setup.direction,
            pattern=setup.pattern.value if hasattr(setup.pattern, "value") else str(setup.pattern),
            level=setup.level,
            price=float(entry_row["close"]),
            candle_time=pattern_row["time"],
            reason=setup.reason,
            status=SignalStatus.APPROVED,
        )
