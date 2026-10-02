"""
tests.test_feature_3_4_overlays
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Automated test verification suite for Feature 3.4:
- Technical Overlays & Add-on Engine.
- Moving averages (EMA 9/21/50/200, SMA 20).
- Momentum & Volatility (RSI 14, MACD, Bollinger Bands, ATR, VWAP).
- VIX volatility regime classification.
- Price action candlestick pattern detectors.
- REST API integration via GET /marketview/data?overlays=...
"""

import sys
import os
import pytest
import httpx
from datetime import datetime, timezone, timedelta

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from txcore.database import connect_db, disconnect_db
from txcore.marketview.models import CandleData
from txcore.marketview.overlays import (
    compute_market_technicals,
    detect_candlestick_patterns,
    calculate_ema,
    calculate_sma,
    calculate_vwap,
    calculate_rsi,
    calculate_macd,
    calculate_bollinger_bands,
    calculate_atr,
    classify_vix_regime,
    candles_to_dataframe,
)
from txcore.service import app


def test_pure_indicator_calculations():
    now = datetime.now(timezone.utc)
    # Generate 30 sample rising/falling candles
    sample_candles = []
    price = 100.0
    for i in range(30):
        o = price
        h = price + 2.0
        l = price - 1.0
        c = price + (1.5 if i % 2 == 0 else -0.5)
        vol = 1000.0 + i * 50
        sample_candles.append(
            CandleData(
                timestamp=now + timedelta(minutes=5 * i),
                open=o,
                high=h,
                low=l,
                close=c,
                volume=vol,
            )
        )
        price = c

    df = candles_to_dataframe(sample_candles)

    # 1. EMA & SMA
    ema_9 = calculate_ema(df["close"], 9)
    assert len(ema_9) == 30
    assert ema_9[-1] is not None

    sma_20 = calculate_sma(df["close"], 20)
    assert len(sma_20) == 30

    # 2. VWAP
    vwap = calculate_vwap(df)
    assert len(vwap) == 30
    assert vwap[-1] > 90.0

    # 3. RSI
    rsi = calculate_rsi(df["close"], 14)
    assert len(rsi) == 30
    for r in rsi:
        assert 0.0 <= r <= 100.0

    # 4. MACD
    macd, sig, hist = calculate_macd(df["close"], 12, 26, 9)
    assert len(macd) == 30
    assert len(sig) == 30
    assert len(hist) == 30

    # 5. Bollinger Bands
    upper, mid, lower = calculate_bollinger_bands(df["close"], 20, 2.0)
    assert len(upper) == 30
    for i in range(19, 30):
        assert upper[i] >= mid[i] >= lower[i]

    # 6. ATR
    atr = calculate_atr(df, 14)
    assert len(atr) == 30
    assert atr[-1] > 0.0


def test_vix_regime_classification():
    assert classify_vix_regime(11.5) == "LOW_VOLATILITY"
    assert classify_vix_regime(15.2) == "NORMAL_VOLATILITY"
    assert classify_vix_regime(21.0) == "ELEVATED_VOLATILITY"
    assert classify_vix_regime(28.5) == "HIGH_VOLATILITY"
    assert classify_vix_regime(None) == "NORMAL_VOLATILITY"


def test_candlestick_pattern_detection():
    now = datetime.now(timezone.utc)
    pattern_candles = [
        # 0: Normal candle
        CandleData(timestamp=now, open=100.0, high=105.0, low=95.0, close=102.0, volume=100),
        # 1: Doji (tiny body 101.0 - 100.95 = 0.05 on 10.0 range)
        CandleData(timestamp=now + timedelta(minutes=5), open=101.0, high=106.0, low=96.0, close=100.95, volume=100),
        # 2: Hammer (open 98, close 99, high 99.2, low 92 -> lower wick 6, body 1)
        CandleData(timestamp=now + timedelta(minutes=10), open=98.0, high=99.2, low=92.0, close=99.0, volume=100),
        # 3: Shooting Star (open 102, close 101, high 108, low 100.8 -> upper wick 6, body 1)
        CandleData(timestamp=now + timedelta(minutes=15), open=102.0, high=108.0, low=100.8, close=101.0, volume=100),
        # 4: Red candle
        CandleData(timestamp=now + timedelta(minutes=20), open=102.0, high=103.0, low=98.0, close=99.0, volume=100),
        # 5: Bullish Engulfing (opens at 98 <= 99, closes at 104 >= 102)
        CandleData(timestamp=now + timedelta(minutes=25), open=98.0, high=104.5, low=97.5, close=104.0, volume=100),
    ]

    df = candles_to_dataframe(pattern_candles)
    markers = detect_candlestick_patterns(df)

    pattern_names = [m.pattern for m in markers]
    assert "DOJI" in pattern_names
    assert "HAMMER" in pattern_names
    assert "ENGULFING_BULLISH" in pattern_names or "BULLISH_ENGULFING" in pattern_names


@pytest.mark.anyio
async def test_marketview_overlays_rest_api():
    await connect_db()
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
            # Login as SuperAdmin
            login_resp = await client.post(
                "/api/v1/auth/login",
                json={"identifier": "rajat.18.ds@gmail.com", "password": "Abcd@1234"},
            )
            assert login_resp.status_code == 200
            token = login_resp.json()["token"]
            auth_headers = {"Authorization": f"Bearer {token}"}

            # Request data with selective overlays
            resp = await client.get(
                "/marketview/data?symbol=BTCUSDT&timeframe=5m&mode=LIVE&lookback=25&overlays=EMA_9,VWAP,RSI,MACD,BB,PATTERNS",
                headers=auth_headers,
            )
            assert resp.status_code == 200, f"Overlays request failed: {resp.text}"
            data = resp.json()

            assert data["technicals"] is not None
            tech = data["technicals"]
            assert tech["symbol"] == "BTCUSDT"
            assert "EMA_9" in tech["overlays"]
            assert "VWAP" in tech["overlays"]
            assert "RSI_14" in tech["overlays"]
            assert "MACD_LINE" in tech["overlays"]
            assert "BB_UPPER" in tech["overlays"]
            assert isinstance(tech["patterns"], list)
            assert tech["vixRegime"] is not None

    finally:
        await disconnect_db()
