"""
Test: PostgreSQL Connection Lifecycle and Health Check Verification
Verifies connect_db, health check query latency, and graceful disconnection.
"""

import sys
import os
import pytest
import asyncio

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from txcore.database import connect_db, disconnect_db, check_db_health, db


@pytest.mark.anyio
async def test_database_connection_and_health():
    # 1. Connect
    client = await connect_db()
    assert client.is_connected() is True

    # 2. Check health
    health = await check_db_health()
    print("\nDatabase Health Report:", health)
    assert health["status"] == "HEALTHY"
    assert health["database"] == "txbot"
    assert health["user"] == "postgres"
    assert health["latency_ms"] >= 0

    # 3. Disconnect
    await disconnect_db()
    assert db.is_connected() is False


if __name__ == "__main__":
    asyncio.run(test_database_connection_and_health())
    print("ALL TESTS PASSED SUCCESSFULLY!")
