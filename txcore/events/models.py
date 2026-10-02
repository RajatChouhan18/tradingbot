"""
AuraTrade Event Trigger Data Models (txcore.events.models)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Pydantic schemas and enums for standalone event watchers, rule thresholds,
multi-channel messaging targets, and execution audit telemetry.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class TriggerType(str, Enum):
    CANDLE_PATTERN = "CANDLE_PATTERN"
    PRICE_SPIKE = "PRICE_SPIKE"
    VOLUME_SPIKE = "VOLUME_SPIKE"
    SR_BREAK = "SR_BREAK"
    INDICATOR_CROSS = "INDICATOR_CROSS"


class TriggerStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    DISABLED = "DISABLED"


class ChannelType(str, Enum):
    TELEGRAM = "TELEGRAM"
    WHATSAPP = "WHATSAPP"
    WEBHOOK = "WEBHOOK"
    EMAIL = "EMAIL"


# =========================================================================
# Rule Configuration Schemas
# =========================================================================
class PriceSpikeConfig(BaseModel):
    spike_pct: float = Field(default=1.5, ge=0.01, description="Percentage price movement required to trigger")
    lookback_bars: int = Field(default=3, ge=1, le=50, description="Number of bars over which spike occurs")
    direction: str = Field(default="ANY", description="BULLISH (Up), BEARISH (Down), or ANY")


class VolumeSpikeConfig(BaseModel):
    volume_multiplier: float = Field(default=2.0, ge=1.1, description="Multiple of 20-period volume SMA required")
    sma_period: int = Field(default=20, ge=5, le=100)


class SRBreakConfig(BaseModel):
    level: float = Field(..., description="Support or Resistance price level")
    level_type: str = Field(default="RESISTANCE", description="SUPPORT or RESISTANCE")
    break_type: str = Field(default="BREAKOUT", description="BREAKOUT (above) or BREAKDOWN (below)")
    buffer_pct: float = Field(default=0.0, ge=0.0, description="Tolerance buffer % beyond the level")


class IndicatorCrossConfig(BaseModel):
    indicator: str = Field(default="RSI", description="RSI, EMA_CROSS, VWAP_CROSS, MACD_CROSS")
    # RSI thresholds
    rsi_operator: Optional[str] = Field(default="GREATER_THAN", description="GREATER_THAN (Overbought) or LESS_THAN (Oversold)")
    rsi_threshold: Optional[float] = Field(default=70.0, ge=0.0, le=100.0)
    # EMA Cross parameters
    ema_fast: Optional[int] = Field(default=9, ge=1)
    ema_slow: Optional[int] = Field(default=21, ge=2)
    cross_direction: Optional[str] = Field(default="GOLDEN", description="GOLDEN (Fast crosses above Slow) or DEATH (Fast crosses below Slow)")


class CandlePatternConfig(BaseModel):
    patterns: List[str] = Field(default=["ENGULFING_BULLISH", "HAMMER"], description="List of detectable candlestick pattern IDs")
    sentiment: Optional[str] = Field(default="ANY", description="BULLISH, BEARISH, NEUTRAL, or ANY")


# =========================================================================
# Request & Response Schemas
# =========================================================================
class CreateEventTriggerRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Descriptive identifier for the event watcher")
    symbol: str = Field(..., min_length=1, max_length=30, description="Market symbol / ticker (e.g. RELIANCE, BTCUSDT)")
    market: str = Field(default="INDIAN_EQUITY", description="Market code: INDIAN_EQUITY, US_EQUITY, CRYPTO, FOREX, MCX")
    timeframe: str = Field(default="5m", description="Base timeframe: 1m, 3m, 5m, 15m, 30m, 1h, 1d")
    trigger_type: TriggerType = Field(..., description="Type of signal condition to monitor")
    threshold_config: Optional[Dict[str, Any]] = Field(default=None, description="JSON rule parameters for the chosen trigger type")
    conditions: Optional[Dict[str, Any]] = Field(default=None, description="Alias for threshold_config")
    channels: List[ChannelType] = Field(default=[ChannelType.TELEGRAM], description="Channels to notify on trigger")
    channel_targets: Optional[Dict[str, Any]] = Field(default=None, description="Custom chat IDs or webhook URLs")
    status: TriggerStatus = Field(default=TriggerStatus.ACTIVE)
    notes: Optional[str] = None
    is_standalone: Optional[bool] = True


class UpdateEventTriggerRequest(BaseModel):
    name: Optional[str] = None
    symbol: Optional[str] = None
    market: Optional[str] = None
    timeframe: Optional[str] = None
    trigger_type: Optional[TriggerType] = None
    threshold_config: Optional[Dict[str, Any]] = None
    conditions: Optional[Dict[str, Any]] = None
    channels: Optional[List[ChannelType]] = None
    channel_targets: Optional[Dict[str, Any]] = None
    status: Optional[TriggerStatus] = None
    notes: Optional[str] = None



class ChannelDispatchDetail(BaseModel):
    channel: str
    target: str
    status: str  # SENT, FAILED, SKIPPED
    latency_ms: int = 0
    error: Optional[str] = None


class TriggerExecutionLogResponse(BaseModel):
    id: str
    trigger_id: str
    symbol: str
    market: str
    timeframe: str
    trigger_type: str
    trigger_price: float
    conditions_met: Dict[str, Any]
    candle_timestamp: datetime
    channels_notified: List[Dict[str, Any]]
    dispatch_success: bool
    latency_ms: int
    error_message: Optional[str] = None
    created_at: datetime


class EventTriggerResponse(BaseModel):
    id: str
    name: str
    symbol: str
    market: str
    timeframe: str
    trigger_type: str
    threshold_config: Dict[str, Any]
    channels: List[str]
    channel_targets: Optional[Dict[str, Any]] = None
    status: str
    last_triggered_at: Optional[datetime] = None
    trigger_count: int
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = "SYSTEM"
    updated_by: Optional[str] = "SYSTEM"


class TestTriggerRequest(BaseModel):
    trigger_id: Optional[str] = None
    symbol: Optional[str] = None
    market: Optional[str] = None
    timeframe: Optional[str] = None
    trigger_type: Optional[TriggerType] = None
    threshold_config: Optional[Dict[str, Any]] = None


class TestTriggerResponse(BaseModel):
    matched: bool
    symbol: str
    market: str
    timeframe: str
    last_candle: Dict[str, Any]
    trigger_type: str
    evaluated_values: Dict[str, Any]
    evaluation_message: str
    latency_ms: float
