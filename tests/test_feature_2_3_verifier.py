"""
tests.test_feature_2_3_verifier
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Automated verification suite for Feature 2.3:
- Real-time TradingView live search for equities, crypto, forex.
- Strict decimal precision auto-detection (4 for stocks, 6 for crypto/forex).
- Negative verification test with user-friendly explicit error response.
- REST API verification for /catalog/groups, /catalog/symbols, /catalog/search, /catalog/add, /catalog/toggle, /catalog/delete.
- Mandatory audit tracking on additions and updates.
"""

import sys
import os
import pytest
import httpx

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from txcore.database import db, connect_db, disconnect_db
from txcore.catalog.verifier import search_tradingview, verify_asset
from txcore.service import app


@pytest.mark.anyio
async def test_feature_2_3_live_search_and_verifier():
    # 1. Test Live Search for Indian Equity
    in_results = await search_tradingview(query="RELIANCE", market="INDIAN_EQUITY", limit=5)
    assert len(in_results) > 0
    top_in = in_results[0]
    assert top_in.exchange in ["NSE", "BSE"]
    assert top_in.decimalPlaces == 4
    assert "RELIANCE" in top_in.symbol

    # 2. Test Live Search for US Equity
    us_results = await search_tradingview(query="AAPL", market="US_EQUITY", limit=5)
    assert len(us_results) > 0
    top_us = us_results[0]
    assert top_us.exchange in ["NASDAQ", "NYSE"]
    assert top_us.decimalPlaces == 4
    assert "AAPL" in top_us.symbol

    # 3. Test Live Search for Crypto (Must be 6 decimals)
    crypto_results = await search_tradingview(query="BTCUSDT", market="CRYPTO", limit=5)
    assert len(crypto_results) > 0
    top_crypto = crypto_results[0]
    assert top_crypto.decimalPlaces == 6
    assert "BTCUSDT" in top_crypto.symbol

    # 4. Test Verification Engine Success
    ver_success = await verify_asset(query="AAPL", market="US_EQUITY")
    assert ver_success.verified is True
    assert ver_success.asset is not None
    assert ver_success.asset.symbol == "AAPL"
    assert ver_success.asset.decimalPlaces == 4

    # 5. Test Verification Engine Negative Test (Non-existent asset)
    ver_fail = await verify_asset(query="XYZ999NONEXISTENT", market="INDIAN_EQUITY")
    assert ver_fail.verified is False
    assert ver_fail.asset is None
    assert "could not be found or verified on TradingView" in ver_fail.error
    assert "XYZ999NONEXISTENT" in ver_fail.error


@pytest.mark.anyio
async def test_feature_2_3_catalog_rest_api():
    await connect_db()
    try:
        # Pre-cleanup in case of prior runs
        await db.marketsymbol.delete_many(where={"symbol": "TEST_IEX"})

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
            # 1. Login as SuperAdmin to get session token
            login_resp = await client.post(
                "/api/v1/auth/login",
                json={"identifier": "rajat.18.ds@gmail.com", "password": "Abcd@1234"},
            )
            assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
            token = login_resp.json()["token"]
            auth_headers = {"Authorization": f"Bearer {token}"}

            # 2. Test GET /catalog/groups
            groups_resp = await client.get("/catalog/groups", headers=auth_headers)
            assert groups_resp.status_code == 200
            groups = groups_resp.json()
            assert len(groups) >= 5
            nse_group = next(g for g in groups if g["groupId"] == "NSE")
            assert nse_group["symbolCount"] > 0

            # 3. Test GET /catalog/symbols
            syms_resp = await client.get("/catalog/symbols?group=NSE&limit=50", headers=auth_headers)
            assert syms_resp.status_code == 200
            syms = syms_resp.json()
            assert len(syms) > 0
            assert any(s["symbol"] == "RELIANCE" for s in syms)

            # 4. Test GET /catalog/search (TradingView live search endpoint)
            search_resp = await client.get("/catalog/search?query=INFY&market=INDIAN_EQUITY", headers=auth_headers)
            assert search_resp.status_code == 200
            search_data = search_resp.json()
            assert len(search_data) > 0
            assert any("INFY" in item["symbol"] for item in search_data)

            # 5. Test POST /catalog/verify (Live Verification endpoint)
            verify_resp = await client.post(
                "/catalog/verify",
                json={"query": "TCS", "market": "INDIAN_EQUITY"},
                headers=auth_headers,
            )
            assert verify_resp.status_code == 200
            ver_res = verify_resp.json()
            assert ver_res["verified"] is True
            assert ver_res["asset"]["symbol"] == "TCS"
            assert ver_res["asset"]["decimalPlaces"] == 4

            # 6. Test POST /catalog/add (Add new symbol to catalog)
            add_resp = await client.post(
                "/catalog/add",
                json={
                    "symbol": "TEST_IEX",
                    "shortName": "Indian Energy Exchange Test",
                    "fullName": "Indian Energy Exchange Ltd",
                    "market": "INDIAN_EQUITY",
                    "exchange": "NSE",
                    "assetType": "STOCK",
                    "sector": "Power",
                    "decimalPlaces": 4,
                    "groupId": "NSE",
                    "lotSize": 1,
                    "tickSize": 0.05,
                    "tvSymbol": "NSE:IEX",
                },
                headers=auth_headers,
            )
            assert add_resp.status_code == 200, f"Add asset failed: {add_resp.text}"
            added_sym = add_resp.json()
            assert added_sym["symbol"] == "TEST_IEX"
            assert added_sym["decimalPlaces"] == 4
            assert added_sym["isPreseeded"] is False
            assert added_sym["createdBy"] == "rajat.18.ds@gmail.com"
            assert added_sym["updatedBy"] == "rajat.18.ds@gmail.com"

            # 7. Test PATCH /catalog/symbols/{symbol}/toggle (Deactivate & Reactivate)
            deact_resp = await client.patch("/catalog/symbols/TEST_IEX/toggle?isActive=false", headers=auth_headers)
            assert deact_resp.status_code == 200
            assert deact_resp.json()["isActive"] is False

            react_resp = await client.patch("/catalog/symbols/TEST_IEX/toggle?isActive=true", headers=auth_headers)
            assert react_resp.status_code == 200
            assert react_resp.json()["isActive"] is True

            # 8. Test DELETE /catalog/symbols/{symbol} (Soft-Delete)
            del_resp = await client.delete("/catalog/symbols/TEST_IEX", headers=auth_headers)
            assert del_resp.status_code == 200
            assert del_resp.json()["deleted"] is True

            # Verify soft-deletion in database (Record preserved, isDeleted=True, isActive=False)
            check_db = await db.marketsymbol.find_unique(where={"symbol": "TEST_IEX"})
            assert check_db is not None
            assert check_db.isDeleted is True
            assert check_db.isActive is False
            assert check_db.deletedAt is not None

            # Verify GET /catalog/symbols excludes soft-deleted symbols
            query_resp = await client.get("/catalog/symbols?search=TEST_IEX", headers=auth_headers)
            assert query_resp.status_code == 200
            assert len(query_resp.json()) == 0

            # 9. Test Re-Adding Soft-Deleted Asset (Reactivation without 409)
            readd_resp = await client.post(
                "/catalog/add",
                json={
                    "symbol": "TEST_IEX",
                    "shortName": "Indian Energy Exchange Restored",
                    "fullName": "Indian Energy Exchange Ltd Restored",
                    "market": "INDIAN_EQUITY",
                    "exchange": "NSE",
                    "assetType": "STOCK",
                    "sector": "Power",
                    "decimalPlaces": 4,
                    "groupId": "NSE",
                    "lotSize": 1,
                    "tickSize": 0.05,
                    "tvSymbol": "NSE:IEX",
                },
                headers=auth_headers,
            )
            assert readd_resp.status_code == 200, f"Re-add asset failed: {readd_resp.text}"
            readded_sym = readd_resp.json()
            assert readded_sym["symbol"] == "TEST_IEX"
            assert readded_sym["shortName"] == "Indian Energy Exchange Restored"
            assert readded_sym["isDeleted"] is False
            assert readded_sym["isActive"] is True
            assert readded_sym["deletedAt"] is None

            # 10. Test Adding Active Asset triggers 409 Conflict
            duplicate_resp = await client.post(
                "/catalog/add",
                json={
                    "symbol": "TEST_IEX",
                    "shortName": "Duplicate",
                    "fullName": "Duplicate Ltd",
                    "market": "INDIAN_EQUITY",
                    "exchange": "NSE",
                },
                headers=auth_headers,
            )
            assert duplicate_resp.status_code == 409
            assert "already exists in the catalog" in duplicate_resp.json()["detail"]

    finally:
        # Cleanup test symbol
        await db.marketsymbol.delete_many(where={"symbol": "TEST_IEX"})
        await disconnect_db()
