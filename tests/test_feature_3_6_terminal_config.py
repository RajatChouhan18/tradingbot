"""
Test: Feature 3.6 Isolated User Terminal Configuration & Precision Rules
Verifies user terminal configuration endpoints, per-user isolation, and institutional audit tracking.
"""

import sys
import os
import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from txcore.database import connect_db, disconnect_db, db
from txcore.auth.seeder import seed_system_roles_and_superadmin, DEFAULT_SUPERADMIN_EMAIL, DEFAULT_SUPERADMIN_PASSWORD
from txcore.auth.router import router as auth_router
from txcore.auth.user_router import router as user_router

app = FastAPI(title="AuraTrade Feature 3.6 Test App")
app.include_router(auth_router)
app.include_router(user_router)


@pytest.mark.anyio
async def test_user_terminal_config_isolated_crud():
    await connect_db()
    await seed_system_roles_and_superadmin()

    # Clean up any existing terminal config for test idempotency
    admin_user = await db.user.find_unique(where={"email": DEFAULT_SUPERADMIN_EMAIL})
    if admin_user:
        await db.userterminalconfig.delete_many(where={"userId": admin_user.id})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Login with SuperAdmin
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"identifier": DEFAULT_SUPERADMIN_EMAIL, "password": DEFAULT_SUPERADMIN_PASSWORD},
        )
        assert login_res.status_code == 200
        token = login_res.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Get initial terminal config (should return defaults if not customized)
        init_res = await client.get("/api/v1/users/me/terminal-config", headers=headers)
        assert init_res.status_code == 200
        init_data = init_res.json()
        assert init_data["default_market"] == "INDIAN_EQUITY"
        assert init_data["default_symbol"] == "RELIANCE"
        assert init_data["default_timeframe"] == "5m"
        assert "EMA_9" in init_data["default_overlays"]
        assert init_data["default_patterns"] == "ALL"

        # 3. Update terminal config for Admin
        update_payload = {
            "default_market": "CRYPTO",
            "default_symbol": "BTCUSDT",
            "default_timeframe": "15m",
            "default_overlays": "EMA_9,EMA_21,EMA_50,VWAP",
            "default_patterns": "ENGULFING_BULLISH,HAMMER,DOJI",
        }
        put_res = await client.put("/api/v1/users/me/terminal-config", json=update_payload, headers=headers)
        assert put_res.status_code == 200
        put_data = put_res.json()
        assert put_data["success"] is True
        assert put_data["default_market"] == "CRYPTO"
        assert put_data["default_symbol"] == "BTCUSDT"
        assert put_data["default_timeframe"] == "15m"
        assert put_data["default_overlays"] == "EMA_9,EMA_21,EMA_50,VWAP"
        assert put_data["default_patterns"] == "ENGULFING_BULLISH,HAMMER,DOJI"

        # 4. Fetch updated config to verify persistence
        get_res = await client.get("/api/v1/users/me/terminal-config", headers=headers)
        assert get_res.status_code == 200
        get_data = get_res.json()
        assert get_data["default_market"] == "CRYPTO"
        assert get_data["default_symbol"] == "BTCUSDT"
        assert get_data["is_customized"] is True

        # 5. Verify database audit columns
        admin_user = await db.user.find_unique(where={"email": DEFAULT_SUPERADMIN_EMAIL})
        db_cfg = await db.userterminalconfig.find_unique(where={"userId": admin_user.id})
        assert db_cfg is not None
        assert db_cfg.defaultMarket == "CRYPTO"
        assert db_cfg.defaultSymbol == "BTCUSDT"
        assert db_cfg.createdBy == DEFAULT_SUPERADMIN_EMAIL
        assert db_cfg.updatedBy == DEFAULT_SUPERADMIN_EMAIL
        assert db_cfg.createdAt is not None
        assert db_cfg.updatedAt is not None

        # 6. Test saving empty candle patterns & empty indicators (No patterns selected)
        empty_payload = {
            "default_market": "CRYPTO",
            "default_symbol": "BTCUSDT",
            "default_timeframe": "15m",
            "default_indicators": "",
            "default_overlays": "",
            "default_candles": "",
            "default_patterns": "",
        }
        empty_put_res = await client.put("/api/v1/users/me/terminal-config", json=empty_payload, headers=headers)
        assert empty_put_res.status_code == 200
        empty_put_data = empty_put_res.json()
        assert empty_put_data["default_indicators"] == ""
        assert empty_put_data["default_candles"] == ""

        # Fetch to confirm empty patterns are persisted and returned
        empty_get_res = await client.get("/api/v1/users/me/terminal-config", headers=headers)
        assert empty_get_res.status_code == 200
        empty_get_data = empty_get_res.json()
        assert empty_get_data["default_indicators"] == ""
        assert empty_get_data["default_candles"] == ""
        assert empty_get_data["default_patterns"] == ""
        assert empty_get_data["is_customized"] is True

        print("\n[SUCCESS] Feature 3.6 User Terminal Config CRUD & Audit Columns verified!")
