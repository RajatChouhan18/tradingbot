"""
txcore.catalog.models
~~~~~~~~~~~~~~~~~~~~~
Pydantic data models and schemas for Module 2: Market Catalog & Asset Directory.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class MarketGroupResponse(BaseModel):
    id: str
    groupId: str
    name: str
    market: str
    description: Optional[str] = ""
    symbolCount: Optional[int] = 0
    createdAt: datetime
    updatedAt: datetime
    createdBy: Optional[str] = "SYSTEM"
    updatedBy: Optional[str] = "SYSTEM"


class MarketSymbolResponse(BaseModel):
    id: str
    symbol: str
    shortName: str
    fullName: str
    market: str
    exchange: str
    assetType: str
    sector: Optional[str] = None
    indexGroup: Optional[str] = None
    decimalPlaces: int
    groupId: Optional[str] = None
    lotSize: int
    tickSize: float
    tvSymbol: Optional[str] = None
    isPreseeded: bool
    isActive: bool
    isDeleted: bool = False
    deletedAt: Optional[datetime] = None
    createdAt: datetime
    updatedAt: datetime
    createdBy: Optional[str] = "SYSTEM"
    updatedBy: Optional[str] = "SYSTEM"


class TradingViewSearchResult(BaseModel):
    symbol: str
    name: str
    exchange: str
    assetType: str
    market: str
    tvSymbol: str
    decimalPlaces: int
    country: Optional[str] = ""
    currency: Optional[str] = ""


class AssetVerificationRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Company name or ticker to search and verify")
    market: Optional[str] = Field("INDIAN_EQUITY", description="Target market code: INDIAN_EQUITY, US_EQUITY, CRYPTO, FOREX, MCX")
    exchange: Optional[str] = Field(None, description="Optional target exchange filter e.g. NSE, BSE, NASDAQ, BINANCE")


class AssetVerificationResponse(BaseModel):
    verified: bool
    asset: Optional[TradingViewSearchResult] = None
    error: Optional[str] = None


class AddAssetRequest(BaseModel):
    symbol: str = Field(..., min_length=1)
    shortName: str = Field(..., min_length=1)
    fullName: str = Field(..., min_length=1)
    market: str = Field(..., min_length=1)
    exchange: str = Field(..., min_length=1)
    assetType: str = Field("STOCK")
    sector: Optional[str] = None
    indexGroup: Optional[str] = None
    decimalPlaces: Optional[int] = None # If None, auto-determined: 4 for stocks, 6 for crypto/forex
    groupId: Optional[str] = None
    lotSize: Optional[int] = 1
    tickSize: Optional[float] = 0.05
    tvSymbol: Optional[str] = None


class MarketCandleResponse(BaseModel):
    id: str
    symbol: str
    timeframe: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    createdAt: datetime
    updatedAt: datetime
    createdBy: Optional[str] = "SYSTEM"
    updatedBy: Optional[str] = "SYSTEM"

