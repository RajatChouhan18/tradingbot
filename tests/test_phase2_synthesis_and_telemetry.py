"""
tests.test_phase2_synthesis_and_telemetry
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Comprehensive verification of Phase 2 capabilities:
  1. Real-time tick & quote synthesis for active candle (index -1)
  2. NSEClient stock and index quote acquisition
  3. Hybrid dual-engine data provider integration
  4. Concurrency transparency & execution latency telemetry
  5. Asynchronous SSE telemetry broadcasting and event delivery
"""

import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
import pandas as pd
import pytest

from txcore.models.types import StockQuote, IndexQuote
from txcore.providers.synthesizer import (
    RealTimeTickSynthesizer,
    parse_timeframe_seconds,
    align_timestamp_to_timeframe,
)
from txcore.providers.nse_provider import NSEClient
from txcore.providers.indian_provider import IndianMarketDataProvider
from txcore.providers.base import BaseDataProvider
from txcore.stream import TelemetryBroadcaster, telemetry_broadcaster
from txcore.algotrade import AlgoTrade, AlgoTradeConfig, AlgoTradeManager


class DummyProvider(BaseDataProvider):
    """Generates predictable OHLCV bars for testing."""

    def __init__(self, base_price: float = 2500.0, num_bars: int = 20):
        super().__init__()
        self.base_price = base_price
        self.num_bars = num_bars

    def get_candles(self, symbol: str, timeframe: str = "5m", lookback_bars: int = 20, **kwargs):
        now = datetime.now(timezone.utc)
        data = []
        for i in range(self.num_bars):
            t = now - timedelta(minutes=5 * (self.num_bars - i))
            p = self.base_price + i * 2.0
            data.append({
                "time": t,
                "open": p,
                "high": p + 5.0,
                "low": p - 3.0,
                "close": p + 1.0,
                "volume": 1000.0 * (i + 1),
            })
        df = pd.DataFrame(data)
        df["time"] = pd.to_datetime(df["time"], utc=True)
        return df


# =============================================================================
# 1. TIMEFRAME PARSER & ALIGNMENT TESTS
# =============================================================================

def test_timeframe_seconds_parsing():
    assert parse_timeframe_seconds("1m") == 60
    assert parse_timeframe_seconds("3m") == 180
    assert parse_timeframe_seconds("5m") == 300
    assert parse_timeframe_seconds("15m") == 900
    assert parse_timeframe_seconds("1h") == 3600
    assert parse_timeframe_seconds("1d") == 86400
    assert parse_timeframe_seconds("invalid") == 300  # Safe default


def test_align_timestamp_to_timeframe():
    dt = datetime(2026, 9, 27, 9, 23, 45, tzinfo=timezone.utc)
    aligned_5m = align_timestamp_to_timeframe(dt, 300)
    assert aligned_5m == datetime(2026, 9, 27, 9, 20, 0, tzinfo=timezone.utc)

    aligned_15m = align_timestamp_to_timeframe(dt, 900)
    assert aligned_15m == datetime(2026, 9, 27, 9, 15, 0, tzinfo=timezone.utc)

    aligned_1h = align_timestamp_to_timeframe(dt, 3600)
    assert aligned_1h == datetime(2026, 9, 27, 9, 0, 0, tzinfo=timezone.utc)


# =============================================================================
# 2. REAL-TIME TICK SYNTHESIZER TESTS
# =============================================================================

def test_synthesizer_updates_existing_forming_bar():
    """Verify that a quote arriving within the current bar's timeframe updates high/low/close/volume."""
    base_time = datetime(2026, 9, 27, 10, 0, 0, tzinfo=timezone.utc)
    df = pd.DataFrame([
        {"time": base_time, "open": 100.0, "high": 105.0, "low": 98.0, "close": 102.0, "volume": 500.0}
    ])

    quote = StockQuote(
        symbol="TEST",
        company_name="Test Corp",
        last_price=108.50,  # New high and close
        change=8.50,
        percent_change=8.5,
        open=100.0,
        high=108.50,
        low=98.0,
        volume=1200.0,     # Higher volume
        timestamp=datetime(2026, 9, 27, 10, 2, 30, tzinfo=timezone.utc),  # Within 10:00 - 10:05
    )

    enriched = RealTimeTickSynthesizer.synthesize_active_candle(df, quote, timeframe="5m")
    assert len(enriched) == 1
    last = enriched.iloc[-1]
    assert float(last["close"]) == 108.50
    assert float(last["high"]) == 108.50
    assert float(last["low"]) == 98.0
    assert float(last["volume"]) == 1200.0


def test_synthesizer_appends_new_candle_when_interval_elapses():
    """Verify that when the interval boundary elapses, a new candle is synthesized and appended."""
    base_time = datetime(2026, 9, 27, 10, 0, 0, tzinfo=timezone.utc)
    df = pd.DataFrame([
        {"time": base_time, "open": 100.0, "high": 105.0, "low": 98.0, "close": 103.0, "volume": 500.0}
    ])

    # Quote is at 10:06:15 -> New 5-minute candle starts at 10:05:00
    quote = StockQuote(
        symbol="TEST",
        company_name="Test Corp",
        last_price=104.50,
        change=1.50,
        percent_change=1.5,
        open=103.0,
        volume=300.0,
        timestamp=datetime(2026, 9, 27, 10, 6, 15, tzinfo=timezone.utc),
    )

    enriched = RealTimeTickSynthesizer.synthesize_active_candle(df, quote, timeframe="5m")
    assert len(enriched) == 2
    new_bar = enriched.iloc[-1]
    assert pd.to_datetime(new_bar["time"], utc=True) == datetime(2026, 9, 27, 10, 5, 0, tzinfo=timezone.utc)
    assert float(new_bar["open"]) == 103.0
    assert float(new_bar["close"]) == 104.50
    assert float(new_bar["high"]) >= 104.50
    assert float(new_bar["low"]) <= 103.0


def test_synthesizer_empty_dataframe_initialization():
    """Verify synthesizer can initialize from an empty dataframe."""
    quote = StockQuote(
        symbol="TEST",
        company_name="Test Corp",
        last_price=500.0,
        change=5.0,
        percent_change=1.0,
        open=498.0,
        timestamp=datetime(2026, 9, 27, 9, 17, 0, tzinfo=timezone.utc),
    )
    res = RealTimeTickSynthesizer.synthesize_active_candle(None, quote, timeframe="5m")
    assert res is not None
    assert len(res) == 1
    assert float(res.iloc[0]["close"]) == 500.0


def test_forming_candle_summary():
    """Verify diagnostic summary extraction of forming candle."""
    df = pd.DataFrame([
        {"time": datetime.now(timezone.utc), "open": 100.0, "high": 110.0, "low": 95.0, "close": 105.0, "volume": 800.0}
    ])
    summary = RealTimeTickSynthesizer.get_forming_candle_summary(df)
    assert summary["open"] == 100.0
    assert summary["close"] == 105.0
    assert summary["change_from_open"] == 5.0
    assert summary["percent_from_open"] == 5.0
    assert summary["is_bullish"] is True


# =============================================================================
# 3. NSECLIENT QUOTE TESTS
# =============================================================================

def test_nse_client_get_stock_quote_parsing():
    """Verify NSEClient.get_stock_quote parses official quote-equity payload."""
    client = NSEClient()
    mock_payload = {
        "info": {
            "symbol": "RELIANCE",
            "companyName": "Reliance Industries Limited",
            "industry": "Oil & Gas",
        },
        "priceInfo": {
            "lastPrice": 2980.50,
            "change": 25.50,
            "pChange": 0.86,
            "open": 2960.0,
            "close": 2980.50,
            "intraDayHighLow": {"min": 2955.0, "max": 2990.0},
            "weekHighLow": {"min": 2200.0, "max": 3050.0},
        },
        "marketDeptOrderBook": {
            "totalTradedVolume": 6543200,
        }
    }

    client._get_api = MagicMock(return_value=mock_payload)
    quote = client.get_stock_quote("RELIANCE")

    assert quote is not None
    assert quote.symbol == "RELIANCE"
    assert quote.company_name == "Reliance Industries Limited"
    assert quote.last_price == 2980.50
    assert quote.change == 25.50
    assert quote.percent_change == 0.86
    assert quote.open == 2960.0
    assert quote.high == 2990.0
    assert quote.low == 2955.0
    assert quote.volume == 6543200.0
    assert quote.sector == "Oil & Gas"


def test_nse_client_get_stock_quote_index_fallback():
    """Verify NSEClient.get_stock_quote seamlessly falls back to get_index_quote for indices."""
    client = NSEClient()
    mock_index = IndexQuote(
        name="NIFTY 50",
        symbol="NIFTY 50",
        last_price=24500.0,
        change=150.0,
        percent_change=0.62,
        open=24400.0,
        high=24550.0,
        low=24380.0,
        previous_close=24350.0,
    )
    client.get_index_quote = MagicMock(return_value=mock_index)

    quote = client.get_stock_quote("NIFTY 50")
    assert quote is not None
    assert quote.symbol == "NIFTY 50"
    assert quote.last_price == 24500.0
    assert quote.sector == "Index"


# =============================================================================
# 4. HYBRID DUAL-ENGINE DATA PROVIDER TESTS
# =============================================================================

def test_indian_provider_with_realtime_synthesis():
    """Verify IndianMarketDataProvider merges live quotes into base candles."""
    dummy = DummyProvider(base_price=2000.0, num_bars=15)
    mock_nse = NSEClient()
    mock_quote = StockQuote(
        symbol="TCS",
        company_name="Tata Consultancy Services",
        last_price=2055.0,  # Live tick higher than last bar
        change=15.0,
        percent_change=0.74,
        open=2030.0,
        high=2060.0,
        low=2025.0,
        volume=99999.0,
        timestamp=datetime.now(timezone.utc),
    )
    mock_nse.get_stock_quote = MagicMock(return_value=mock_quote)

    provider = IndianMarketDataProvider(
        underlying_provider=dummy,
        nse_client=mock_nse,
        enable_realtime_synthesis=True,
    )

    df = provider.get_candles("TCS", timeframe="5m", lookback_bars=15)
    assert df is not None
    assert len(df) >= 15
    # The active candle close should reflect the synthesized real-time tick!
    assert float(df.iloc[-1]["close"]) == 2055.0


# =============================================================================
# 5. CONCURRENCY & LATENCY TELEMETRY TESTS
# =============================================================================

def test_algotrade_concurrency_stats():
    """Verify that AlgoTrade tracks execution latency and concurrency telemetry."""
    dummy = DummyProvider()
    config = AlgoTradeConfig(
        algo_name="Concurrency Telemetry Test",
        market="INDIAN_EQUITY",
        symbols=["RELIANCE", "TCS", "INFY"],
        max_workers=4,
    )
    algo = AlgoTrade(config=config, provider=dummy)

    # Run one scan cycle
    results = algo.run_cycle()
    assert len(results) == 3

    # Inspect metrics
    metrics = algo.get_metrics()
    assert "concurrency" in metrics
    stats = metrics["concurrency"]
    assert stats["max_workers"] >= 4
    assert stats["last_cycle_duration_ms"] > 0
    assert len(stats["symbol_latencies_ms"]) == 3
    assert "RELIANCE" in stats["symbol_latencies_ms"]
    assert "TCS" in stats["symbol_latencies_ms"]
    assert "INFY" in stats["symbol_latencies_ms"]

    algo.close()


# =============================================================================
# 6. ASYNC SSE TELEMETRY BROADCASTER TESTS
# =============================================================================

def test_telemetry_broadcaster():
    """Verify TelemetryBroadcaster pub/sub and queue management."""
    async def _run():
        broadcaster = TelemetryBroadcaster()
        queue = broadcaster.subscribe()

        assert len(broadcaster._subscribers) == 1

        # Broadcast event
        await broadcaster.broadcast("test_event", {"key": "value"})

        item = await asyncio.wait_for(queue.get(), timeout=2.0)
        assert "event: test_event" in item
        assert '"key": "value"' in item

        # Unsubscribe
        broadcaster.unsubscribe(queue)
        assert len(broadcaster._subscribers) == 0

    asyncio.run(_run())

