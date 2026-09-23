"""
txcore.models.types
~~~~~~~~~~~~~~~~~~~
Strongly typed domain models, enums, and data structures for the trading engine.
Supports Forex, Indian F&O (Indices and Stocks), and multi-market asset classes.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List


class Direction(str, Enum):
    CALL = "CALL"  # Bullish / Buy Call
    PUT = "PUT"    # Bearish / Buy Put
    NEUTRAL = "NEUTRAL"


class CandleType(str, Enum):
    DOJI = "DOJI"
    DRAGONFLY_DOJI = "DRAGONFLY_DOJI"
    GRAVESTONE_DOJI = "GRAVESTONE_DOJI"
    HAMMER = "HAMMER"
    INVERTED_HAMMER = "INVERTED_HAMMER"
    SHOOTING_STAR = "SHOOTING_STAR"
    SPINNING_TOP = "SPINNING_TOP"
    MARUBOZU_BULLISH = "MARUBOZU_BULLISH"
    MARUBOZU_BEARISH = "MARUBOZU_BEARISH"
    WEAK_BULLISH = "WEAK_BULLISH"
    WEAK_BEARISH = "WEAK_BEARISH"
    STANDARD_BULLISH = "STANDARD_BULLISH"
    STANDARD_BEARISH = "STANDARD_BEARISH"


class PatternType(str, Enum):
    BULLISH_ENGULFING = "Bullish Engulfing"
    BEARISH_ENGULFING = "Bearish Engulfing"
    PIERCING_LINE = "Piercing Line"
    DARK_CLOUD_COVER = "Dark Cloud Cover"
    MORNING_STAR = "Morning Star"
    EVENING_STAR = "Evening Star"
    TWEEZER_BOTTOM = "Tweezer Bottom"
    TWEEZER_TOP = "Tweezer Top"
    CUSTOM = "Custom Pattern"


class SignalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    BLOCKED = "BLOCKED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class Candle:
    """Represents a single completed or forming OHLCV bar."""
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0

    @property
    def body(self) -> float:
        return abs(self.close - self.open)

    @property
    def range(self) -> float:
        return max(0.0, self.high - self.low)

    @property
    def upper_wick(self) -> float:
        return max(0.0, self.high - max(self.open, self.close))

    @property
    def lower_wick(self) -> float:
        return max(0.0, min(self.open, self.close) - self.low)

    @property
    def is_bullish(self) -> bool:
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        return self.close < self.open

    @property
    def is_flat(self) -> bool:
        return self.close == self.open


@dataclass
class SetupResult:
    """Represents an identified pattern setup awaiting confirmation/entry."""
    direction: Direction
    pattern: PatternType
    pattern_index: int
    entry_index: int
    level: float
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Signal:
    """Represents an actionable trading alert with complete lifecycle state."""
    pair: str
    direction: Direction
    pattern: str
    level: float
    price: float
    candle_time: datetime
    reason: str
    status: SignalStatus = SignalStatus.APPROVED
    provider: str = "TRADINGVIEW"
    news_status: str = "CLEAR"
    timeframe: str = "1-Minute"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_alert_message(self, version_tag: str = "V3 - TRADINGVIEW") -> str:
        """Renders standard emoji-formatted alert text."""
        return (
            f"🚨 PDF PRICE ACTION SIGNAL ({version_tag}) 🚨\n\n"
            f"💱 Pair: {self.pair}\n"
            f"⏱ Timeframe: {self.timeframe}\n"
            f"📊 Signal: {self.direction.value}\n"
            f"🕯 Pattern: {self.pattern}\n"
            f"💰 Price: {self.price:.5f}\n"
            f"📍 Key Level: {self.level:.5f}\n\n"
            f"📌 PDF Rule:\n{self.reason}\n\n"
            f"📡 Provider: {self.provider}\n"
            f"📰 News filter: {self.news_status}\n"
            f"⚠️ Demo/backtest before live money."
        )
