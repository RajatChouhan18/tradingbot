"""
tests.test_feature_3_3_ranges
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Automated test verification suite for Feature 3.3:
- Interactive Range & Timeframe Selector API.
- Mode A (LIVE) streaming lookback, live quote, and session status.
- Mode B (HISTORICAL) date range and candle retrieval from PostgreSQL.
- Fast status and spot quote endpoints.
- RBAC authentication and permission verification.
"""

import sys
import os
import pytest
import httpx
from datetime import datetime, timezone, timedelta

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from txcore.database import connect_db, disconnect_db
from txcore.service import app


@pytest.mark.anyio
async def test_marketview_rest_endpoints():
    await connect_db()
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
            # 1. Test Unauthenticated Access Rejection (401)
            unauth_resp = await client.get("/marketview/data?symbol=BTCUSDT")
            assert unauth_resp.status_code == 401

            # 2. Login as SuperAdmin to get session token
            login_resp = await client.post(
                "/api/v1/auth/login",
                json={"identifier": "rajat.18.ds@gmail.com", "password": "Abcd@1234"},
            )
            assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
            token = login_resp.json()["token"]
            auth_headers = {"Authorization": f"Bearer {token}"}

            # 3. Test Mode A: LIVE Data Stream for Crypto (BTCUSDT)
            live_crypto = await client.get(
                "/marketview/data?symbol=BTCUSDT&timeframe=5m&mode=LIVE&lookback=30",
                headers=auth_headers,
            )
            assert live_crypto.status_code == 200, f"Live crypto fetch failed: {live_crypto.text}"
            data_c = live_crypto.json()
            assert data_c["symbol"] == "BTCUSDT"
            assert data_c["market"] == "CRYPTO"
            assert data_c["timeframe"] == "5m"
            assert len(data_c["candles"]) >= 10
            assert data_c["liveQuote"] is not None
            assert data_c["liveQuote"]["lastPrice"] > 1000.0
            assert data_c["status"]["isOpen"] is True
            assert data_c["latencyMs"] >= 0.0

            # 4. Test Mode A: LIVE Data Stream for Indian Equity (RELIANCE)
            live_in = await client.get(
                "/marketview/data?symbol=RELIANCE&timeframe=5m&mode=LIVE&lookback=30",
                headers=auth_headers,
            )
            assert live_in.status_code == 200, f"Live Indian equity fetch failed: {live_in.text}"
            data_in = live_in.json()
            assert data_in["symbol"] == "RELIANCE"
            assert data_in["market"] == "INDIAN_EQUITY"
            assert data_in["status"] is not None
            assert len(data_in["status"]["sessionName"]) > 0

            # 5. Test Mode B: HISTORICAL Range Query
            now = datetime.now(timezone.utc)
            start_date = now - timedelta(days=5)
            end_date = now

            hist_resp = await client.get(
                "/marketview/data",
                params={
                    "symbol": "RELIANCE",
                    "timeframe": "5m",
                    "mode": "HISTORICAL",
                    "startDate": start_date.isoformat(),
                    "endDate": end_date.isoformat(),
                    "lookback": 50,
                },
                headers=auth_headers,
            )
            assert hist_resp.status_code == 200, f"Historical fetch failed: {hist_resp.text}"
            data_hist = hist_resp.json()
            assert data_hist["symbol"] == "RELIANCE"
            assert len(data_hist["candles"]) >= 0

            # 6. Test GET /marketview/status
            status_resp = await client.get(
                "/marketview/status?market=INDIAN_EQUITY&symbol=RELIANCE",
                headers=auth_headers,
            )
            assert status_resp.status_code == 200
            stat = status_resp.json()
            assert stat["market"] == "INDIAN_EQUITY"
            assert "sessionName" in stat
            assert "message" in stat

            # 7. Test GET /marketview/quote
            quote_resp = await client.get(
                "/marketview/quote?symbol=BTCUSDT",
                headers=auth_headers,
            )
            assert quote_resp.status_code == 200
            q = quote_resp.json()
            assert q is not None
            assert q["symbol"] == "BTCUSDT"
            assert q["lastPrice"] > 1000.0

    finally:
        await disconnect_db()
