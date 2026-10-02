"""
tests.test_feature_3_5_incremental
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Automated test verification suite for Feature 3.5:
- Strict Incremental Computation Engine (Zero Recalculation O(1) Accumulators).
- State bootstrapping from 180 baseline bars.
- O(1) indicator mathematical parity against vectorized bulk formulas.
- Sub-millisecond execution latency verification (< 1.0 ms).
- Real-time tick synthesis on forming bar (index -1).
"""

import sys
import os
import time
import pytest
from datetime import datetime, timezone, timedelta

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from txcore.marketview.models import CandleData, LiveQuote
from txcore.marketview.incremental import (
    IncrementalMarketState,
    IncrementalEngine,
    incremental_engine,
)
from txcore.marketview.overlays import (
    calculate_ema,
    calculate_vwap,
    calculate_rsi,
    calculate_atr,
    candles_to_dataframe,
)


def generate_synthetic_candles(n: int = 180) -> list[CandleData]:
    """Generates realistic trending candles for precision verification."""
    now = datetime(2026, 6, 1, 9, 15, tzinfo=timezone.utc)
    candles = []
    price = 2500.0
    for i in range(n):
        o = price
        change = 5.0 if i % 3 != 0 else -3.0
        c = o + change
        h = max(o, c) + 2.0
        l = min(o, c) - 2.0
        vol = 5000.0 + (i * 20.0)
        candles.append(
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
    return candles


def test_incremental_state_bootstrap_and_ring_buffer():
    """Verifies that state hydrates up to max 180 candles in FIFO buffer."""
    candles = generate_synthetic_candles(200)
    state = IncrementalMarketState(symbol="RELIANCE", timeframe="5m", max_candles=180)
    state.bootstrap_from_candles(candles)

    # Must hold exactly 180 candles
    assert len(state.candles) == 180
    assert state.candles[-1].timestamp == candles[-1].timestamp

    # Ring buffer property: adding 1 candle drops oldest
    oldest_ts = state.candles[0].timestamp
    new_candle = CandleData(
        timestamp=candles[-1].timestamp + timedelta(minutes=5),
        open=2600.0,
        high=2610.0,
        low=2595.0,
        close=2605.0,
        volume=6000.0,
    )
    state._apply_closed_candle(new_candle)
    assert len(state.candles) == 180
    assert state.candles[-1].timestamp == new_candle.timestamp
    assert state.candles[0].timestamp > oldest_ts


def test_incremental_mathematical_parity():
    """Verifies O(1) running accumulators match bulk vectorized indicator values."""
    candles = generate_synthetic_candles(100)
    state = IncrementalMarketState(symbol="RELIANCE", timeframe="5m")
    state.bootstrap_from_candles(candles)

    # Bulk vectorized reference
    df = candles_to_dataframe(candles)
    ref_ema_9 = calculate_ema(df["close"], 9)[-1]
    ref_ema_21 = calculate_ema(df["close"], 21)[-1]
    ref_vwap = calculate_vwap(df)[-1]
    ref_rsi = calculate_rsi(df["close"], 14)[-1]
    ref_atr = calculate_atr(df, 14)[-1]

    # Incremental O(1) values
    inc_tech = state.get_instantaneous_technicals()

    assert abs(inc_tech["EMA_9"] - ref_ema_9) < 0.05
    assert abs(inc_tech["EMA_21"] - ref_ema_21) < 0.05
    assert abs(inc_tech["VWAP"] - ref_vwap) < 0.05
    assert abs(inc_tech["RSI_14"] - ref_rsi) < 1.0  # RSI within 1 point tolerance
    assert abs(inc_tech["ATR_14"] - ref_atr) < 0.05


def test_sub_millisecond_latency_guarantee():
    """Verifies that O(1) single candle update takes strictly under 1.0 millisecond."""
    engine = IncrementalEngine()
    candles = generate_synthetic_candles(180)
    engine.get_or_create_state("BTCUSDT", "5m", initial_candles=candles)

    new_candle = CandleData(
        timestamp=candles[-1].timestamp + timedelta(minutes=5),
        open=95000.0,
        high=95200.0,
        low=94900.0,
        close=95150.0,
        volume=120.5,
    )

    # Benchmark 100 consecutive O(1) bar updates
    latencies = []
    for _ in range(100):
        t0 = time.perf_counter()
        res = engine.process_closed_candle("BTCUSDT", "5m", new_candle)
        t_elapsed_ms = (time.perf_counter() - t0) * 1000.0
        latencies.append(t_elapsed_ms)

    avg_latency_ms = sum(latencies) / len(latencies)
    max_latency_ms = max(latencies)

    # Strict invariant: average latency must be under 0.5ms (typically 0.01 - 0.05ms)
    assert avg_latency_ms < 0.5, f"Average latency too high: {avg_latency_ms:.4f}ms"
    assert max_latency_ms < 1.0, f"Max latency exceeded 1.0ms: {max_latency_ms:.4f}ms"


def test_live_tick_active_candle_synthesis():
    """Verifies dynamic synthesis of the active forming candle (index -1) from live spot quote."""
    state = IncrementalMarketState(symbol="AAPL", timeframe="5m")

    # Tick 1 at 09:30:15
    q1 = LiveQuote(
        symbol="AAPL",
        market="US_EQUITY",
        exchange="NASDAQ",
        lastPrice=230.50,
        volume=100.0,
        timestamp=datetime(2026, 6, 9, 13, 30, 15, tzinfo=timezone.utc),
        provider="TRADINGVIEW",
    )
    forming_bar = state.process_incoming_tick(q1, tf_seconds=300)
    assert forming_bar.open == 230.50
    assert forming_bar.high == 230.50
    assert forming_bar.low == 230.50
    assert forming_bar.close == 230.50
    assert forming_bar.timestamp == datetime(2026, 6, 9, 13, 30, 0, tzinfo=timezone.utc)

    # Tick 2 at 09:32:00 (New high)
    q2 = LiveQuote(
        symbol="AAPL",
        market="US_EQUITY",
        exchange="NASDAQ",
        lastPrice=232.00,
        volume=250.0,
        timestamp=datetime(2026, 6, 9, 13, 32, 0, tzinfo=timezone.utc),
        provider="TRADINGVIEW",
    )
    forming_bar = state.process_incoming_tick(q2, tf_seconds=300)
    assert forming_bar.open == 230.50
    assert forming_bar.high == 232.00
    assert forming_bar.low == 230.50
    assert forming_bar.close == 232.00

    # Tick 3 at 09:35:10 (Next 5m interval boundary -> new forming candle)
    q3 = LiveQuote(
        symbol="AAPL",
        market="US_EQUITY",
        exchange="NASDAQ",
        lastPrice=231.80,
        volume=50.0,
        timestamp=datetime(2026, 6, 9, 13, 35, 10, tzinfo=timezone.utc),
        provider="TRADINGVIEW",
    )
    new_forming_bar = state.process_incoming_tick(q3, tf_seconds=300)
    assert new_forming_bar.open == 231.80
    assert new_forming_bar.timestamp == datetime(2026, 6, 9, 13, 35, 0, tzinfo=timezone.utc)
