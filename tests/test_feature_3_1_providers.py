"""
tests.test_feature_3_1_providers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Automated test verification suite for Feature 3.1:
- Data Provider Architecture (LSP-compliant BaseDataProvider).
- Thread-safe async TTL caching.
- Concrete providers: BinanceProvider, YahooFinanceProvider, TradingViewProvider, NseDirectProvider.
- ProviderRegistry factory routing and resilient fallback mechanics.
"""

import sys
import os
import pytest
import asyncio

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from txcore.marketview.models import CandleData, LiveQuote
from txcore.marketview.providers.base import BaseDataProvider
from txcore.marketview.providers.binance import BinanceProvider
from txcore.marketview.providers.yahoo import YahooFinanceProvider
from txcore.marketview.providers.tradingview import TradingViewProvider
from txcore.marketview.providers.nse import NseDirectProvider
from txcore.marketview.providers.registry import ProviderRegistry, provider_registry


class MockFailingProvider(BaseDataProvider):
    """Test helper: provider that fails on demand."""
    def __init__(self):
        super().__init__(name="MOCK_FAIL", cache_ttl_seconds=1.0)

    async def fetch_candles(self, *args, **kwargs):
        raise ConnectionError("Simulated primary provider outage")

    async def fetch_live_quote(self, *args, **kwargs):
        raise ConnectionError("Simulated quote failure")


@pytest.mark.anyio
async def test_base_provider_ttl_caching():
    """Verifies that BaseDataProvider caches candle queries and invalidates properly."""
    provider = BinanceProvider(cache_ttl_seconds=2.0)

    # 1. Fetch candles
    candles1 = await provider.get_cached_candles("BTCUSDT", timeframe="1m", lookback=10)
    assert len(candles1) > 0

    # 2. Second fetch within TTL must return cached items instantly
    candles2 = await provider.get_cached_candles("BTCUSDT", timeframe="1m", lookback=10)
    assert len(candles2) == len(candles1)
    assert candles1[0].timestamp == candles2[0].timestamp

    # 3. Invalidate cache
    await provider.invalidate_cache("BTCUSDT")
    assert len(provider._cache) == 0


@pytest.mark.anyio
async def test_binance_provider_real_crypto():
    """Verifies BinanceProvider fetches real crypto candles and spot quotes."""
    provider = BinanceProvider()

    # Test candles
    candles = await provider.fetch_candles("BTCUSDT", timeframe="5m", lookback=20)
    assert len(candles) >= 15
    for c in candles:
        assert c.open > 0
        assert c.high >= c.low
        assert c.close > 0

    # Test 24hr live quote
    quote = await provider.fetch_live_quote("BTCUSDT")
    assert quote is not None
    assert quote.symbol == "BTCUSDT"
    assert quote.market == "CRYPTO"
    assert quote.lastPrice > 1000.0
    assert quote.provider == "BINANCE"


@pytest.mark.anyio
async def test_yahoo_finance_provider_global():
    """Verifies YahooFinanceProvider fetches US equities and Forex data."""
    provider = YahooFinanceProvider()

    # Test US stock candles
    candles = await provider.fetch_candles("AAPL", timeframe="5m", lookback=15)
    assert len(candles) > 0
    assert candles[0].close > 50.0

    # Test live quote
    quote = await provider.fetch_live_quote("AAPL")
    assert quote is not None
    assert quote.symbol == "AAPL"
    assert quote.lastPrice > 50.0


@pytest.mark.anyio
async def test_provider_registry_and_fallback():
    """Verifies ProviderRegistry market routing and automatic failover."""
    registry = ProviderRegistry()

    # 1. Check default market routing
    crypto_prov = registry.get_provider("CRYPTO")
    assert crypto_prov.name == "BINANCE"

    indian_prov = registry.get_provider("INDIAN_EQUITY")
    assert indian_prov.name == "NSE_DIRECT"

    us_prov = registry.get_provider("US_EQUITY")
    assert us_prov.name == "TRADINGVIEW"

    # 2. Test fallback mechanism
    # Setup custom market with failing primary and working fallback
    registry.register_provider(
        "TEST_MARKET",
        primary=MockFailingProvider(),
        fallback=BinanceProvider(),
    )

    # Fetching candles should seamlessly succeed via fallback
    candles = await registry.fetch_candles_with_fallback(
        symbol="BTCUSDT",
        market="TEST_MARKET",
        timeframe="5m",
        lookback=10,
    )
    assert len(candles) > 0
    assert candles[-1].close > 0
