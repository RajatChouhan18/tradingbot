"""
txcore.marketview.models
~~~~~~~~~~~~~~~~~~~~~~~~
Pydantic data models for Module 3: MarketView (Data Provider Layer & Real-Time Engine).
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class CandleData(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


class LiveQuote(BaseModel):
    symbol: str
    market: str
    exchange: Optional[str] = None
    lastPrice: float
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    prevClose: Optional[float] = None
    change: Optional[float] = None
    changePct: Optional[float] = None
    volume: Optional[float] = 0.0
    timestamp: datetime
    provider: str


class MarketStatusInfo(BaseModel):
    market: str
    exchange: Optional[str] = None
    isOpen: bool
    sessionName: str
    lastTradedPrice: Optional[float] = None
    lastTradedTime: Optional[datetime] = None
    nextOpenTime: Optional[datetime] = None
    message: str


class PatternMarker(BaseModel):
    index: int
    timestamp: datetime
    pattern: str
    sentiment: str  # BULLISH, BEARISH, NEUTRAL
    description: str


class ProviderTechnicals(BaseModel):
    symbol: str
    timeframe: str
    timestamp: datetime
    overlays: Dict[str, List[Optional[float]]] = Field(default_factory=dict)
    patterns: List[PatternMarker] = Field(default_factory=list)
    vixRegime: Optional[str] = None


class MarketDataResponse(BaseModel):
    symbol: str
    market: str
    timeframe: str
    candles: List[CandleData]
    liveQuote: Optional[LiveQuote] = None
    status: Optional[MarketStatusInfo] = None
    technicals: Optional[ProviderTechnicals] = None
    fetchedAt: datetime
    provider: str
    latencyMs: float
