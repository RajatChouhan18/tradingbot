"""
txcore.models.types
~~~~~~~~~~~~~~~~~~~
Strongly typed domain models, enums, and data structures for the trading engine.
Supports Forex, Indian F&O (Indices and Stocks), and multi-market asset classes.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
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


import uuid


def generate_signal_id(pair: str = "", timestamp: Optional[datetime] = None) -> str:
    """
    Generates a unique, collision-resistant identifier for every signal.
    Format: SIG-{PAIR}-{YYYYMMDD-HHMMSS}-{RANDOM_HEX_6}
    Example: SIG-EURUSD-20260924-011500-A9F3D2
    """
    ts_str = (timestamp or datetime.now(timezone.utc)).strftime("%Y%m%d-%H%M%S")
    clean_pair = pair.replace("/", "").replace("_", "").replace(":", "").upper() if pair else "GEN"
    suffix = uuid.uuid4().hex[:6].upper()
    return f"SIG-{clean_pair}-{ts_str}-{suffix}"


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
    signal_id: str = ""
    status: SignalStatus = SignalStatus.APPROVED
    provider: str = "TRADINGVIEW"
    news_status: str = "CLEAR"
    timeframe: str = "1-Minute"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.signal_id:
            self.signal_id = generate_signal_id(self.pair, self.candle_time)

    def to_alert_message(self, version_tag: str = "V3 - TRADINGVIEW") -> str:
        """Renders standard emoji-formatted alert text with unique signal ID."""
        return (
            f"🚨 PDF PRICE ACTION SIGNAL ({version_tag}) 🚨\n"
            f"🆔 ID: {self.signal_id}\n\n"
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


class MarketStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PRE_OPEN = "PRE_OPEN"
    POST_CLOSE = "POST_CLOSE"
    WEEKEND = "WEEKEND"
    HOLIDAY = "HOLIDAY"


class VixRegime(str, Enum):
    LOW = "LOW"             # VIX < 13: Low volatility, tight ranges, option buying risky
    NORMAL = "NORMAL"       # 13 <= VIX < 18: Healthy trending momentum, ideal for breakout buying
    ELEVATED = "ELEVATED"   # 18 <= VIX < 24: High volatility, wide stops, explosive moves
    EXTREME = "EXTREME"     # VIX >= 24: Panic / High fear regime, huge option premiums


@dataclass
class IndexQuote:
    """Represents a live or cached snapshot of a market index."""
    name: str
    symbol: str
    last_price: float
    change: float
    percent_change: float
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    previous_close: float = 0.0
    year_high: float = 0.0
    year_low: float = 0.0
    pe: float = 0.0
    pb: float = 0.0
    dy: float = 0.0
    advances: int = 0
    declines: int = 0
    unchanged: int = 0
    exchange: str = "NSE"
    timestamp: Optional[datetime] = None

    @property
    def is_positive(self) -> bool:
        return self.change > 0

    @property
    def is_negative(self) -> bool:
        return self.change < 0

    def to_summary_line(self) -> str:
        arrow = "🟢 ▲" if self.change >= 0 else "🔴 ▼"
        return f"{self.name:25} | {self.last_price:10.2f} | {arrow} {self.change:+8.2f} ({self.percent_change:+6.2f}%)"


@dataclass
class StockQuote:
    """Represents a real-time quote for an equity stock."""
    symbol: str
    company_name: str
    last_price: float
    change: float
    percent_change: float
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: float = 0.0
    high_52w: float = 0.0
    low_52w: float = 0.0
    exchange: str = "NSE"
    sector: str = ""
    timestamp: Optional[datetime] = None

    def to_summary_line(self) -> str:
        arrow = "🟢 ▲" if self.change >= 0 else "🔴 ▼"
        return f"{self.symbol:12} | {self.last_price:9.2f} | {arrow} {self.change:+7.2f} ({self.percent_change:+5.2f}%) | Vol: {self.volume:,.0f}"


@dataclass
class MarketBreadth:
    """Market breadth statistics (advances vs declines) for an index or universe."""
    advances: int
    declines: int
    unchanged: int
    index_name: str = "NIFTY 50"
    timestamp: Optional[datetime] = None

    @property
    def total(self) -> int:
        return self.advances + self.declines + self.unchanged

    @property
    def advance_decline_ratio(self) -> float:
        if self.declines == 0:
            return float(self.advances) if self.advances > 0 else 1.0
        return round(self.advances / self.declines, 2)

    @property
    def sentiment(self) -> str:
        ratio = self.advance_decline_ratio
        if ratio >= 2.0:
            return "STRONGLY_BULLISH"
        elif ratio > 1.1:
            return "MODERATELY_BULLISH"
        elif 0.9 <= ratio <= 1.1:
            return "NEUTRAL"
        elif 0.5 <= ratio < 0.9:
            return "MODERATELY_BEARISH"
        else:
            return "STRONGLY_BEARISH"

    def to_string(self) -> str:
        return (
            f"Market Breadth [{self.index_name}]: "
            f"Advances: {self.advances} | Declines: {self.declines} | Unchanged: {self.unchanged} "
            f"(ADR: {self.advance_decline_ratio:.2f} -> {self.sentiment})"
        )


@dataclass
class MarketSessionInfo:
    """Real-time trading status and timing for markets."""
    status: MarketStatus
    is_trading_active: bool
    current_time_ist: str
    session_name: str
    time_to_open_minutes: Optional[int] = None
    time_to_close_minutes: Optional[int] = None
    message: str = ""

    def to_alert_line(self) -> str:
        state_icon = "🟢 ACTIVE" if self.is_trading_active else "🔴 CLOSED"
        return f"Market State: {self.status.value} ({state_icon}) - {self.session_name} [{self.current_time_ist} IST]"


@dataclass
class VixAnalysis:
    """Analysis of VIX volatility regime and trading implications."""
    current_vix: float
    regime: VixRegime
    change: float = 0.0
    percent_change: float = 0.0
    implication: str = ""
    recommendation: str = ""

    def to_summary_string(self) -> str:
        return (
            f"VIX: {self.current_vix:.2f} ({self.change:+.2f}) | "
            f"Regime: {self.regime.value} | {self.recommendation}"
        )


@dataclass
class OptionChainSummary:
    """Summary metrics of an Index / Stock Option Chain."""
    underlying: str
    spot_price: float
    total_call_oi: int
    total_put_oi: int
    pcr: float
    pcr_sentiment: str
    max_pain_strike: Optional[float] = None
    top_call_oi_strike: Optional[float] = None
    top_put_oi_strike: Optional[float] = None
    timestamp: Optional[datetime] = None


# Backward-compatible aliases for renamed classes
IndianMarketStatus = MarketStatus
IndianIndexQuote = IndexQuote
IndianStockQuote = StockQuote
