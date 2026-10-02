"""
tests.test_feature_2_1_schema
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Automated verification suite for Feature 2.1:
- Unified Prisma Schema for MarketGroup, MarketSymbol, and MarketCandle.
- Mandatory institutional audit metadata (createdAt, updatedAt, createdBy, updatedBy).
- Composite unique constraint [symbol, timeframe, timestamp] on MarketCandle.
- High-speed descending timestamp indexing.
- Symbol deletion and active/inactive lifecycle.
- Strict decimal precision validation (4 for stocks, 6 for crypto/forex).
"""

import sys
import os
import pytest
from datetime import datetime, timezone, timedelta

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from txcore.database import db, connect_db, disconnect_db


@pytest.mark.anyio
async def test_feature_2_1_market_catalog_and_candle_schema():
    await connect_db()
    try:
        # Pre-cleanup in case of prior aborted run
        await db.marketcandle.delete_many(where={"symbol": "TEST_INFY"})
        await db.marketsymbol.delete_many(where={"symbol": {"in": ["TEST_INFY", "TEST_BTCUSDT"]}})
        await db.marketgroup.delete_many(where={"groupId": "TEST_NSE"})

        # 1. Verify MarketGroup CRUD & Audit Columns
        group = await db.marketgroup.create(
            data={
                "groupId": "TEST_NSE",
                "name": "National Stock Exchange Test",
                "market": "INDIAN_EQUITY",
                "description": "Indian Equities and Indices Benchmark Group",
                "createdBy": "ADMIN_SYSTEM",
                "updatedBy": "ADMIN_SYSTEM",
            }
        )
        assert group.id is not None
        assert group.groupId == "TEST_NSE"
        assert group.createdBy == "ADMIN_SYSTEM"
        assert group.updatedBy == "ADMIN_SYSTEM"
        assert group.createdAt is not None
        assert group.updatedAt is not None

        # 2. Verify MarketSymbol CRUD, Relation, and Audit Columns
        symbol_stock = await db.marketsymbol.create(
            data={
                "symbol": "TEST_INFY",
                "shortName": "Infosys Test",
                "fullName": "Infosys Technologies Ltd",
                "market": "INDIAN_EQUITY",
                "exchange": "NSE",
                "assetType": "STOCK",
                "sector": "Information Technology",
                "indexGroup": "NIFTY50",
                "decimalPlaces": 4,
                "groupId": group.groupId,
                "lotSize": 1,
                "tickSize": 0.05,
                "tvSymbol": "NSE:INFY",
                "isPreseeded": True,
                "isActive": True,
                "createdBy": "SYSTEM_SEEDER",
                "updatedBy": "SYSTEM_SEEDER",
            }
        )
        assert symbol_stock.id is not None
        assert symbol_stock.symbol == "TEST_INFY"
        assert symbol_stock.decimalPlaces == 4
        assert symbol_stock.isPreseeded is True
        assert symbol_stock.isActive is True
        assert symbol_stock.createdBy == "SYSTEM_SEEDER"

        # Verify Crypto Symbol with 6 decimal places
        symbol_crypto = await db.marketsymbol.create(
            data={
                "symbol": "TEST_BTCUSDT",
                "shortName": "Bitcoin Test",
                "fullName": "Bitcoin / Tether USD",
                "market": "CRYPTO",
                "exchange": "BINANCE",
                "assetType": "CRYPTO",
                "decimalPlaces": 6,
                "lotSize": 1,
                "tickSize": 0.01,
                "tvSymbol": "BINANCE:BTCUSDT",
                "isPreseeded": True,
                "isActive": True,
                "createdBy": "SYSTEM_SEEDER",
                "updatedBy": "SYSTEM_SEEDER",
            }
        )
        assert symbol_crypto.decimalPlaces == 6

        # 3. Verify Symbol Activation / Deactivation & Deletion
        # Toggle inactive
        updated_symbol = await db.marketsymbol.update(
            where={"symbol": "TEST_INFY"},
            data={"isActive": False, "updatedBy": "SUPERADMIN"},
        )
        assert updated_symbol.isActive is False
        assert updated_symbol.updatedBy == "SUPERADMIN"

        # Toggle active again
        reactivated_symbol = await db.marketsymbol.update(
            where={"symbol": "TEST_INFY"},
            data={"isActive": True, "updatedBy": "SUPERADMIN"},
        )
        assert reactivated_symbol.isActive is True

        # 4. Verify Unified MarketCandle Storage & High-Speed Retrieval
        now = datetime.now(timezone.utc)
        candle_time_1 = now - timedelta(minutes=5)
        candle_time_2 = now

        candle1 = await db.marketcandle.create(
            data={
                "symbol": "TEST_INFY",
                "timeframe": "5m",
                "timestamp": candle_time_1,
                "open": 1500.00,
                "high": 1505.50,
                "low": 1498.25,
                "close": 1504.00,
                "volume": 25000.0,
                "createdBy": "TV_SYNC",
                "updatedBy": "TV_SYNC",
            }
        )
        assert candle1.id is not None
        assert candle1.close == 1504.00
        assert candle1.createdBy == "TV_SYNC"

        candle2 = await db.marketcandle.create(
            data={
                "symbol": "TEST_INFY",
                "timeframe": "5m",
                "timestamp": candle_time_2,
                "open": 1504.00,
                "high": 1510.00,
                "low": 1502.00,
                "close": 1508.50,
                "volume": 32000.0,
                "createdBy": "TV_SYNC",
                "updatedBy": "TV_SYNC",
            }
        )
        assert candle2.id is not None

        # 5. Verify Unique Constraint [symbol, timeframe, timestamp]
        with pytest.raises(Exception):
            await db.marketcandle.create(
                data={
                    "symbol": "TEST_INFY",
                    "timeframe": "5m",
                    "timestamp": candle_time_1,  # Duplicate timestamp
                    "open": 1501.0,
                    "high": 1506.0,
                    "low": 1499.0,
                    "close": 1505.0,
                    "volume": 1000.0,
                }
            )

        # 6. Verify Descending Timestamp Querying (High-speed range scan)
        candles = await db.marketcandle.find_many(
            where={"symbol": "TEST_INFY", "timeframe": "5m"},
            order={"timestamp": "desc"},
        )
        assert len(candles) == 2
        assert candles[0].timestamp >= candles[1].timestamp
        assert candles[0].close == 1508.50
        assert candles[1].close == 1504.00

        # 7. Verify Full Deletion Capability (User Directive)
        # Delete symbol
        deleted_symbol = await db.marketsymbol.delete(where={"symbol": "TEST_INFY"})
        assert deleted_symbol.symbol == "TEST_INFY"
        check_symbol = await db.marketsymbol.find_unique(where={"symbol": "TEST_INFY"})
        assert check_symbol is None

        # Clean up crypto symbol, candles, and group
        await db.marketcandle.delete_many(where={"symbol": "TEST_INFY"})
        await db.marketsymbol.delete(where={"symbol": "TEST_BTCUSDT"})
        await db.marketgroup.delete(where={"groupId": "TEST_NSE"})

    finally:
        await disconnect_db()
