"""
txcore.marketview.router
~~~~~~~~~~~~~~~~~~~~~~~~
FastAPI REST Router for Module 3: MarketView Engine.
Provides unified endpoints for live and historical market candlestick data,
spot quotes, market session timing, and diagnostic latency metrics.
"""

import time
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from prisma.models import User

from txcore.database import db
from txcore.auth.dependencies import require_permission
from txcore.marketview.models import (
    CandleData,
    LiveQuote,
    MarketStatusInfo,
    ProviderTechnicals,
    MarketDataResponse,
)
from txcore.marketview.providers.registry import provider_registry
from txcore.marketview.session import session_manager
from txcore.marketview.overlays import compute_market_technicals

logger = logging.getLogger("auratrade.marketview.router")

marketview_router = APIRouter(prefix="/marketview", tags=["MarketView"])


@marketview_router.get("/data", response_model=MarketDataResponse)
async def get_market_data(
    symbol: str = Query(..., min_length=1, description="Asset ticker symbol (e.g. RELIANCE, AAPL, BTCUSDT)"),
    timeframe: str = Query("5m", description="Candlestick timeframe: 1m, 3m, 5m, 15m, 30m, 1h, 1d"),
    market: Optional[str] = Query(None, description="Optional market code: INDIAN_EQUITY, US_EQUITY, CRYPTO, FOREX, MCX"),
    mode: str = Query("LIVE", description="Retrieval mode: LIVE or HISTORICAL"),
    startDate: Optional[datetime] = Query(None, description="Start datetime for HISTORICAL mode"),
    endDate: Optional[datetime] = Query(None, description="End datetime for HISTORICAL mode"),
    lookback: int = Query(180, ge=1, le=2000, description="Bars count for LIVE mode"),
    indicators: Optional[str] = Query(None, description="Optional comma-separated indicators list e.g. EMA_9,EMA_21,VWAP,RSI,MACD,BB,CANDLES"),
    overlays: Optional[str] = Query(None, description="Optional comma-separated overlays list (alias for indicators)"),
    candles: Optional[str] = Query(None, description="Optional comma-separated candles recognition list"),
    patterns: Optional[str] = Query(None, description="Optional comma-separated patterns recognition list (alias for candles)"),
    current_user: User = Depends(require_permission("MARKETVIEW", "view")),
):
    """
    Retrieves unified market data with dual-mode support (Live vs Historical Date Range).
    Includes chronologically ordered candles, live spot quote, market status banner, technical overlays, and latency diagnostics.
    """
    start_bench = time.perf_counter()
    clean_symbol = symbol.strip().upper()
    clean_tf = timeframe.strip().lower()

    # 1. Resolve market and exchange from Catalog if omitted
    resolved_market = market.upper() if market else "INDIAN_EQUITY"
    resolved_exchange = "NSE"

    catalog_item = await db.marketsymbol.find_unique(where={"symbol": clean_symbol})
    if catalog_item:
        resolved_market = catalog_item.market
        resolved_exchange = catalog_item.exchange

    candle_records: List[CandleData] = []
    used_provider = "DATABASE"

    # 2. Mode Retrieval
    if mode.upper() == "HISTORICAL":
        # Query indexed market_candles from database
        where_clause: Dict[str, Any] = {
            "symbol": clean_symbol,
            "timeframe": clean_tf,
        }
        if startDate or endDate:
            time_filter: Dict[str, Any] = {}
            if startDate:
                time_filter["gte"] = startDate
            if endDate:
                time_filter["lte"] = endDate
            where_clause["timestamp"] = time_filter

        db_bars = await db.marketcandle.find_many(
            where=where_clause,
            take=lookback,
            order={"timestamp": "asc"},
        )

        for b in db_bars:
            candle_records.append(
                CandleData(
                    timestamp=b.timestamp,
                    open=b.open,
                    high=b.high,
                    low=b.low,
                    close=b.close,
                    volume=b.volume,
                )
            )

        # If DB is empty, fetch from provider and return
        if not candle_records:
            candle_records = await provider_registry.fetch_candles_with_fallback(
                symbol=clean_symbol,
                market=resolved_market,
                timeframe=clean_tf,
                lookback=lookback,
                start_time=startDate,
                end_time=endDate,
                exchange=resolved_exchange,
            )
            used_provider = provider_registry.get_provider(resolved_market).name

    else:
        # LIVE Mode: Fetch cached/live bars from provider registry
        candle_records = await provider_registry.fetch_candles_with_fallback(
            symbol=clean_symbol,
            market=resolved_market,
            timeframe=clean_tf,
            lookback=lookback,
            exchange=resolved_exchange,
        )
        used_provider = provider_registry.get_provider(resolved_market).name

    # 3. Fetch Live Spot Quote
    live_quote = await provider_registry.fetch_live_quote_with_fallback(
        symbol=clean_symbol,
        market=resolved_market,
        exchange=resolved_exchange,
    )

    # 3b. Synthesize/update active forming candle with live quote in LIVE mode
    if live_quote and candle_records and mode.upper() == "LIVE":
        last_candle = candle_records[-1]
        last_candle.close = live_quote.lastPrice
        if live_quote.lastPrice > last_candle.high:
            last_candle.high = live_quote.lastPrice
        if live_quote.lastPrice < last_candle.low:
            last_candle.low = live_quote.lastPrice

    # 4. Determine Market Session Status & Banner
    last_price = live_quote.lastPrice if live_quote else (candle_records[-1].close if candle_records else None)
    last_time = live_quote.timestamp if live_quote else (candle_records[-1].timestamp if candle_records else None)

    status_info = session_manager.get_market_status(
        market=resolved_market,
        last_price=last_price,
        last_time=last_time,
        exchange=resolved_exchange,
    )

    # 5. Compute Indicators/Overlays & Candles/Technicals
    technicals_payload = None
    if candle_records:
        technicals_payload = compute_market_technicals(
            candles=candle_records,
            symbol=clean_symbol,
            timeframe=clean_tf,
        )

    elapsed_ms = round((time.perf_counter() - start_bench) * 1000.0, 2)

    return MarketDataResponse(
        symbol=clean_symbol,
        market=resolved_market,
        timeframe=clean_tf,
        candles=candle_records,
        liveQuote=live_quote,
        status=status_info,
        technicals=technicals_payload,
        fetchedAt=datetime.now(timezone.utc),
        provider=used_provider,
        latencyMs=elapsed_ms,
    )


@marketview_router.get("/status", response_model=MarketStatusInfo)
async def get_market_status_endpoint(
    market: str = Query(..., description="Target market code: INDIAN_EQUITY, US_EQUITY, CRYPTO, FOREX, MCX"),
    symbol: Optional[str] = Query(None, description="Optional symbol to attach last traded price"),
    current_user: User = Depends(require_permission("MARKETVIEW", "view")),
):
    """Returns current market session status and institutional banner text."""
    clean_market = market.strip().upper()
    last_price = None
    last_time = None

    if symbol:
        quote = await provider_registry.fetch_live_quote_with_fallback(symbol=symbol.strip().upper(), market=clean_market)
        if quote:
            last_price = quote.lastPrice
            last_time = quote.timestamp

    return session_manager.get_market_status(
        market=clean_market,
        last_price=last_price,
        last_time=last_time,
    )


@marketview_router.get("/quote", response_model=Optional[LiveQuote])
async def get_live_quote_endpoint(
    symbol: str = Query(..., min_length=1, description="Asset ticker symbol"),
    market: Optional[str] = Query(None, description="Optional market code"),
    current_user: User = Depends(require_permission("MARKETVIEW", "view")),
):
    """Returns real-time spot quote for a single asset."""
    clean_symbol = symbol.strip().upper()
    resolved_market = market.upper() if market else "INDIAN_EQUITY"

    catalog_item = await db.marketsymbol.find_unique(where={"symbol": clean_symbol})
    if catalog_item:
        resolved_market = catalog_item.market

    return await provider_registry.fetch_live_quote_with_fallback(
        symbol=clean_symbol,
        market=resolved_market,
    )
