"""
tests.test_feature_2_2_seeder
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Automated verification suite for Feature 2.2:
- Benchmark Pre-Seeding across Indian Equities, US Equities, Crypto, Forex, and MCX Commodities.
- Strict decimal precision (4 for stocks/indices, 6 for crypto/forex/commodities).
- Seeder idempotency (multiple runs without duplicates or errors).
- Institutional audit tracking (createdBy = "SYSTEM_SEEDER").
"""

import sys
import os
import pytest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from txcore.database import db, connect_db, disconnect_db
from txcore.catalog.seeder import seed_benchmarks, BENCHMARK_GROUPS, BENCHMARK_SYMBOLS


@pytest.mark.anyio
async def test_feature_2_2_benchmark_seeder():
    await connect_db()
    try:
        # 1. Run Seeder Initial Execution
        result1 = await seed_benchmarks()
        assert result1["total_groups"] >= len(BENCHMARK_GROUPS)
        assert result1["total_symbols"] >= len(BENCHMARK_SYMBOLS)

        # 2. Verify Market Groups Exist
        for g in BENCHMARK_GROUPS:
            db_group = await db.marketgroup.find_unique(where={"groupId": g["groupId"]})
            assert db_group is not None
            assert db_group.name == g["name"]
            assert db_group.market == g["market"]
            assert db_group.createdBy == "SYSTEM_SEEDER"
            assert db_group.createdAt is not None
            assert db_group.updatedAt is not None

        # 3. Verify All Benchmark Symbols Exist with Proper Attributes
        for s in BENCHMARK_SYMBOLS:
            db_sym = await db.marketsymbol.find_unique(where={"symbol": s["symbol"]})
            assert db_sym is not None, f"Symbol {s['symbol']} was not seeded!"
            assert db_sym.market == s["market"]
            assert db_sym.exchange == s["exchange"]
            assert db_sym.assetType == s["assetType"]
            assert db_sym.decimalPlaces == s["decimalPlaces"]
            assert db_sym.isPreseeded is True
            assert db_sym.isActive is True
            assert db_sym.createdBy == "SYSTEM_SEEDER"

            # Strict Precision Invariants
            if s["assetType"] in ["STOCK", "INDEX"]:
                assert db_sym.decimalPlaces == 4, f"Stock/Index {s['symbol']} must have 4 decimal places!"
            elif s["assetType"] in ["CRYPTO", "FOREX", "COMMODITY"]:
                assert db_sym.decimalPlaces == 6, f"Asset {s['symbol']} must have 6 decimal places!"

        # 4. Verify Idempotency on Second Run
        result2 = await seed_benchmarks()
        assert result2["groups_seeded"] == 0  # No new groups created
        assert result2["symbols_seeded"] == 0  # No new symbols created
        assert result2["total_symbols"] == result1["total_symbols"]

    finally:
        await disconnect_db()
