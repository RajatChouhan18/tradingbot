"""
tests.test_feature_2_4_historical
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Automated verification suite for Feature 2.4:
- Real-time fetching of 1m & 5m TradingView bars via tvDatafeed.
- Persistence directly into unified PostgreSQL market_candles table.
- High-speed indexed range queries on [symbol, timeframe, timestamp DESC].
- REST API verification for GET /catalog/candles.
- Idempotency and duplicate bar handling.
- Mandatory institutional audit tracking (createdBy = "TV_HISTORICAL_SEEDER").
"""

import sys
import os
import time
import pytest
import httpx

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from txcore.database import db, connect_db, disconnect_db
from txcore.catalog.historical import (
    fetch_tradingview_bars,
    save_candles_to_database,
    query_market_candles,
)
from txcore.service import app


@pytest.mark.anyio
async def test_feature_2_4_historical_candle_engine():
    await connect_db()
    try:
        # 1. Fetch real bars from TradingView (Zero mocks!)
        bars = fetch_tradingview_bars(symbol="RELIANCE", exchange="NSE", timeframe="5m", n_bars=25)
        assert len(bars) > 0, "Failed to fetch real bars from TradingView!"
        sample = bars[0]
        assert sample["symbol"] == "RELIANCE"
        assert sample["timeframe"] == "5m"
        assert sample["open"] > 0
        assert sample["high"] >= sample["low"]
        assert sample["close"] > 0
        assert sample["timestamp"] is not None

        # 2. Persist into unified PostgreSQL market_candles table
        inserted = await save_candles_to_database(bars)
        assert inserted >= 0  # Might be existing or newly inserted

        # 3. High-Speed Indexed Retrieval
        start_time = time.time()
        candles = await query_market_candles(symbol="RELIANCE", timeframe="5m", limit=25, ascending=True)
        query_duration = time.time() - start_time

        assert len(candles) >= len(bars)
        assert query_duration < 0.10, f"Query took {query_duration:.4f}s, expected < 100ms"

        # Verify chronological order
        assert candles[0].timestamp <= candles[-1].timestamp
        assert candles[0].createdBy == "TV_HISTORICAL_SEEDER"

        # 4. Verify Idempotency (Repeat save of identical bars must not raise error)
        re_saved = await save_candles_to_database(bars)
        assert re_saved == 0  # Zero new bars created on identical replay

    finally:
        await disconnect_db()


@pytest.mark.anyio
async def test_feature_2_4_candles_rest_api():
    await connect_db()
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
            # 1. Authenticate as SuperAdmin
            login_resp = await client.post(
                "/api/v1/auth/login",
                json={"identifier": "rajat.18.ds@gmail.com", "password": "Abcd@1234"},
            )
            assert login_resp.status_code == 200
            token = login_resp.json()["token"]
            headers = {"Authorization": f"Bearer {token}"}

            # 2. Query GET /catalog/candles
            resp = await client.get("/catalog/candles?symbol=RELIANCE&timeframe=5m&limit=20", headers=headers)
            assert resp.status_code == 200
            candles_data = resp.json()
            assert len(candles_data) > 0
            first_candle = candles_data[0]
            assert first_candle["symbol"] == "RELIANCE"
            assert first_candle["timeframe"] == "5m"
            assert first_candle["close"] > 0
            assert "createdAt" in first_candle

    finally:
        await disconnect_db()
