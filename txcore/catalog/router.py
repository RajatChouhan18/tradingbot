"""
txcore.catalog.router
~~~~~~~~~~~~~~~~~~~~~
FastAPI REST router for Module 2: Market Catalog & Asset Directory.
Endpoints:
- GET /catalog/groups: List market groups with symbol counts.
- GET /catalog/symbols: Filter & list symbols from catalog.
- GET /catalog/search: Real-time TradingView live search.
- POST /catalog/verify: Verify single ticker/company on TradingView.
- POST /catalog/add: Add verified asset to database with audit tracking.
- PATCH /catalog/symbols/{symbol}/toggle: Toggle active/inactive.
- DELETE /catalog/symbols/{symbol}: Permanently delete symbol.
"""

import logging
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from prisma.models import User

from txcore.database import db
from txcore.auth.dependencies import get_current_user, get_current_user_optional, require_permission
from txcore.catalog.models import (
    MarketGroupResponse,
    MarketSymbolResponse,
    TradingViewSearchResult,
    AssetVerificationRequest,
    AssetVerificationResponse,
    AddAssetRequest,
    MarketCandleResponse,
)
from txcore.catalog.verifier import search_tradingview, verify_asset
from txcore.catalog.historical import query_market_candles, seed_benchmark_historical_candles

logger = logging.getLogger("auratrade.catalog.router")

catalog_router = APIRouter(prefix="/catalog", tags=["Market Catalog"])


# =========================================================================
# 1. Market Groups
# =========================================================================
@catalog_router.get("/groups", response_model=List[MarketGroupResponse])
async def get_market_groups(
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Lists all market groups along with active symbol counts."""
    groups = await db.marketgroup.find_many(
        include={"symbols": True},
        order={"name": "asc"},
    )
    results = []
    for g in groups:
        results.append(
            MarketGroupResponse(
                id=g.id,
                groupId=g.groupId,
                name=g.name,
                market=g.market,
                description=g.description or "",
                symbolCount=len(g.symbols) if g.symbols else 0,
                createdAt=g.createdAt,
                updatedAt=g.updatedAt,
                createdBy=g.createdBy,
                updatedBy=g.updatedBy,
            )
        )
    return results


# =========================================================================
# 2. Market Symbols Directory
# =========================================================================
@catalog_router.get("/symbols", response_model=List[MarketSymbolResponse])
async def get_market_symbols(
    group: Optional[str] = Query(None, description="Filter by market group ID e.g. NSE, US_EQUITY, CRYPTO"),
    market: Optional[str] = Query(None, description="Filter by market code e.g. INDIAN_EQUITY, US_EQUITY"),
    assetType: Optional[str] = Query(None, description="Filter by asset type: STOCK, INDEX, CRYPTO, FOREX, COMMODITY"),
    search: Optional[str] = Query(None, description="Fuzzy search symbol, shortName or fullName"),
    activeOnly: Optional[bool] = Query(False, description="Filter only active symbols"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Lists symbols from catalog with filtering, sorting, and pagination."""
    where_clause: dict = {"isDeleted": False}
    if group:
        where_clause["groupId"] = group
    if market:
        where_clause["market"] = market
    if assetType and assetType != "ALL":
        where_clause["assetType"] = assetType
    if activeOnly:
        where_clause["isActive"] = True

    if search:
        q = search.strip()
        where_clause["OR"] = [
            {"symbol": {"contains": q, "mode": "insensitive"}},
            {"shortName": {"contains": q, "mode": "insensitive"}},
            {"fullName": {"contains": q, "mode": "insensitive"}},
        ]

    symbols = await db.marketsymbol.find_many(
        where=where_clause,
        take=limit,
        skip=offset,
        order={"symbol": "asc"},
    )

    return [
        MarketSymbolResponse(
            id=s.id,
            symbol=s.symbol,
            shortName=s.shortName,
            fullName=s.fullName,
            market=s.market,
            exchange=s.exchange,
            assetType=s.assetType,
            sector=s.sector,
            indexGroup=s.indexGroup,
            decimalPlaces=s.decimalPlaces,
            groupId=s.groupId,
            lotSize=s.lotSize,
            tickSize=s.tickSize,
            tvSymbol=s.tvSymbol,
            isPreseeded=s.isPreseeded,
            isActive=s.isActive,
            isDeleted=s.isDeleted,
            deletedAt=s.deletedAt,
            createdAt=s.createdAt,
            updatedAt=s.updatedAt,
            createdBy=s.createdBy,
            updatedBy=s.updatedBy,
        )
        for s in symbols
    ]


# =========================================================================
# 3. Live TradingView Search & Verification
# =========================================================================
@catalog_router.get("/search", response_model=List[TradingViewSearchResult])
async def search_live_assets(
    query: str = Query(..., min_length=1, description="Company name or ticker to search"),
    market: Optional[str] = Query(None, description="Optional target market filter"),
    exchange: Optional[str] = Query(None, description="Optional target exchange filter"),
    limit: int = Query(15, ge=1, le=50),
    current_user: User = Depends(require_permission("CATALOG", "view")),
):
    """Executes live TradingView Symbol Search across global exchanges."""
    return await search_tradingview(query=query, market=market, exchange=exchange, limit=limit)


@catalog_router.post("/verify", response_model=AssetVerificationResponse)
async def verify_live_asset(
    body: AssetVerificationRequest,
    current_user: User = Depends(require_permission("CATALOG", "view")),
):
    """Verifies existence of an asset on TradingView for the specified market."""
    return await verify_asset(query=body.query, market=body.market, exchange=body.exchange)


# =========================================================================
# 4. Add Asset to Catalog
# =========================================================================
@catalog_router.post("/add", response_model=MarketSymbolResponse)
async def add_asset_to_catalog(
    body: AddAssetRequest,
    current_user: User = Depends(require_permission("CATALOG", "edit")),
):
    """Adds a verified asset to the catalog or reactivates a soft-deleted asset with strict precision and audit tracking."""
    clean_symbol = body.symbol.strip().upper()

    # 1. Strict Precision Invariant
    # Default 4 for stocks/indices, 6 for crypto/forex/commodities
    if body.decimalPlaces is not None:
        precision = body.decimalPlaces
    else:
        if body.assetType.upper() in ["STOCK", "INDEX"]:
            precision = 4
        else:
            precision = 6

    # 2. Map or fallback group
    target_group_id = body.groupId
    if not target_group_id:
        if body.market == "INDIAN_EQUITY":
            target_group_id = "NSE"
        elif body.market == "US_EQUITY":
            target_group_id = "US_EQUITY"
        elif body.market == "CRYPTO":
            target_group_id = "CRYPTO"
        elif body.market == "FOREX":
            target_group_id = "FOREX"
        elif body.market == "MCX":
            target_group_id = "MCX"

    # 3. Check if symbol already exists
    existing = await db.marketsymbol.find_unique(where={"symbol": clean_symbol})
    if existing:
        if not existing.isDeleted:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Symbol '{clean_symbol}' already exists in the catalog.",
            )
        # Reactivate soft-deleted asset
        updated = await db.marketsymbol.update(
            where={"symbol": clean_symbol},
            data={
                "shortName": body.shortName.strip(),
                "fullName": body.fullName.strip(),
                "market": body.market.strip().upper(),
                "exchange": body.exchange.strip().upper(),
                "assetType": body.assetType.strip().upper(),
                "sector": body.sector,
                "indexGroup": body.indexGroup,
                "decimalPlaces": precision,
                "groupId": target_group_id,
                "lotSize": body.lotSize or 1,
                "tickSize": body.tickSize or (0.05 if precision == 4 else 0.0001),
                "tvSymbol": body.tvSymbol or f"{body.exchange.upper()}:{clean_symbol}",
                "isActive": True,
                "isDeleted": False,
                "deletedAt": None,
                "updatedBy": current_user.email,
            },
        )
        logger.info(f"User {current_user.email} re-added and reactivated soft-deleted asset: {clean_symbol}")
        return MarketSymbolResponse(
            id=updated.id,
            symbol=updated.symbol,
            shortName=updated.shortName,
            fullName=updated.fullName,
            market=updated.market,
            exchange=updated.exchange,
            assetType=updated.assetType,
            sector=updated.sector,
            indexGroup=updated.indexGroup,
            decimalPlaces=updated.decimalPlaces,
            groupId=updated.groupId,
            lotSize=updated.lotSize,
            tickSize=updated.tickSize,
            tvSymbol=updated.tvSymbol,
            isPreseeded=updated.isPreseeded,
            isActive=updated.isActive,
            isDeleted=updated.isDeleted,
            deletedAt=updated.deletedAt,
            createdAt=updated.createdAt,
            updatedAt=updated.updatedAt,
            createdBy=updated.createdBy,
            updatedBy=updated.updatedBy,
        )

    # 4. Create new asset in Database
    created = await db.marketsymbol.create(
        data={
            "symbol": clean_symbol,
            "shortName": body.shortName.strip(),
            "fullName": body.fullName.strip(),
            "market": body.market.strip().upper(),
            "exchange": body.exchange.strip().upper(),
            "assetType": body.assetType.strip().upper(),
            "sector": body.sector,
            "indexGroup": body.indexGroup,
            "decimalPlaces": precision,
            "groupId": target_group_id,
            "lotSize": body.lotSize or 1,
            "tickSize": body.tickSize or (0.05 if precision == 4 else 0.0001),
            "tvSymbol": body.tvSymbol or f"{body.exchange.upper()}:{clean_symbol}",
            "isPreseeded": False,
            "isActive": True,
            "isDeleted": False,
            "deletedAt": None,
            "createdBy": current_user.email,
            "updatedBy": current_user.email,
        }
    )

    logger.info(f"User {current_user.email} added new asset to catalog: {clean_symbol}")

    return MarketSymbolResponse(
        id=created.id,
        symbol=created.symbol,
        shortName=created.shortName,
        fullName=created.fullName,
        market=created.market,
        exchange=created.exchange,
        assetType=created.assetType,
        sector=created.sector,
        indexGroup=created.indexGroup,
        decimalPlaces=created.decimalPlaces,
        groupId=created.groupId,
        lotSize=created.lotSize,
        tickSize=created.tickSize,
        tvSymbol=created.tvSymbol,
        isPreseeded=created.isPreseeded,
        isActive=created.isActive,
        isDeleted=created.isDeleted,
        deletedAt=created.deletedAt,
        createdAt=created.createdAt,
        updatedAt=created.updatedAt,
        createdBy=created.createdBy,
        updatedBy=created.updatedBy,
    )


# =========================================================================
# 5. Toggle & Delete Lifecycle
# =========================================================================
@catalog_router.patch("/symbols/{symbol}/toggle", response_model=MarketSymbolResponse)
async def toggle_symbol_status(
    symbol: str,
    isActive: bool = Query(..., description="Target active status"),
    current_user: User = Depends(require_permission("CATALOG", "edit")),
):
    """Toggles active/inactive status for any catalog symbol."""
    clean_symbol = symbol.strip().upper()
    existing = await db.marketsymbol.find_unique(where={"symbol": clean_symbol})
    if not existing or existing.isDeleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Symbol '{clean_symbol}' not found in catalog.",
        )

    updated = await db.marketsymbol.update(
        where={"symbol": clean_symbol},
        data={
            "isActive": isActive,
            "updatedBy": current_user.email,
        },
    )

    return MarketSymbolResponse(
        id=updated.id,
        symbol=updated.symbol,
        shortName=updated.shortName,
        fullName=updated.fullName,
        market=updated.market,
        exchange=updated.exchange,
        assetType=updated.assetType,
        sector=updated.sector,
        indexGroup=updated.indexGroup,
        decimalPlaces=updated.decimalPlaces,
        groupId=updated.groupId,
        lotSize=updated.lotSize,
        tickSize=updated.tickSize,
        tvSymbol=updated.tvSymbol,
        isPreseeded=updated.isPreseeded,
        isActive=updated.isActive,
        isDeleted=updated.isDeleted,
        deletedAt=updated.deletedAt,
        createdAt=updated.createdAt,
        updatedAt=updated.updatedAt,
        createdBy=updated.createdBy,
        updatedBy=updated.updatedBy,
    )


@catalog_router.delete("/symbols/{symbol}")
async def delete_symbol(
    symbol: str,
    current_user: User = Depends(require_permission("CATALOG", "delete")),
):
    """Soft-deletes any symbol from the catalog without deleting historical candles or audit data."""
    clean_symbol = symbol.strip().upper()
    existing = await db.marketsymbol.find_unique(where={"symbol": clean_symbol})
    if not existing or existing.isDeleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Symbol '{clean_symbol}' not found in catalog.",
        )

    await db.marketsymbol.update(
        where={"symbol": clean_symbol},
        data={
            "isDeleted": True,
            "isActive": False,
            "deletedAt": datetime.now(timezone.utc),
            "updatedBy": current_user.email,
        },
    )
    logger.info(f"User {current_user.email} soft-deleted symbol from catalog: {clean_symbol}")

    return {"deleted": True, "symbol": clean_symbol}


# =========================================================================
# 6. Unified Candlestick Data Retrieval & Pre-Seeding
# =========================================================================
@catalog_router.get("/candles", response_model=List[MarketCandleResponse])
async def get_market_candles(
    symbol: str = Query(..., description="Target ticker symbol"),
    timeframe: str = Query("5m", description="Candle timeframe: 1m, 5m, 15m, 1h, 1d"),
    limit: int = Query(180, ge=1, le=2000, description="Number of bars to return"),
    current_user: User = Depends(require_permission("CATALOG", "view")),
):
    """Retrieves chronologically ordered OHLCV candles from the unified market_candles table."""
    candles = await query_market_candles(
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
        ascending=True,
    )
    return [
        MarketCandleResponse(
            id=c.id,
            symbol=c.symbol,
            timeframe=c.timeframe,
            timestamp=c.timestamp,
            open=c.open,
            high=c.high,
            low=c.low,
            close=c.close,
            volume=c.volume,
            createdAt=c.createdAt,
            updatedAt=c.updatedAt,
            createdBy=c.createdBy,
            updatedBy=c.updatedBy,
        )
        for c in candles
    ]


@catalog_router.post("/candles/seed")
async def trigger_candle_seeding(
    n_bars: int = Query(500, ge=50, le=5000, description="Bars per timeframe to fetch and cache"),
    current_user: User = Depends(require_permission("CATALOG", "edit")),
):
    """Triggers background pre-seeding of benchmark historical candles into market_candles."""
    result = await seed_benchmark_historical_candles(n_bars=n_bars)
    return {"status": "SUCCESS", "result": result}

