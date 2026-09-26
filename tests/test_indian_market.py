"""
tests.test_indian_market
~~~~~~~~~~~~~~~~~~~~~~~~
Comprehensive test suite for Indian Stocks, Indices, VIX Volatility, Market Breadth,
and Session Management modules in txcore.indian_market.
"""

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
import pandas as pd
import pytest

from config.settings import (
    INDIAN_INDEXES,
    INDIAN_STOCKS,
    INDIAN_TIMEZONE,
    VIX_REGIMES,
    PCR_THRESHOLDS,
)
from txcore.models import (
    IndianMarketStatus,
    MarketStatus,
    VixRegime,
    IndianIndexQuote,
    IndexQuote,
    IndianStockQuote,
    StockQuote,
    MarketBreadth,
    MarketSessionInfo,
    VixAnalysis,
)
from txcore.providers import (
    IndianMarketSessionManager,
    MarketSessionManager,
    NSEClient,
    create_indian_session_manager,
)
from txcore.analysis.volatility import analyze_vix
from txcore.analysis.indicators import analyze_trend
from txcore.visualization.chart_builder import create_interactive_chart, scan_df_for_patterns
from txcore.providers.indian_provider import IndianMarketDataProvider
from txcore.providers.base import BaseDataProvider
from txcore.strategies.pdf_price_action import PDFPriceActionStrategy
from txcore.algotrade import (
    AlgoTrade,
    AlgoTradeConfig,
    AlgoTradeManager,
    AlgoTradeStatus,
    TradeAlgo,
    TradeAlgoConfig,
    TradeAlgoManager,
    TradeAlgoStatus,
)



class MockDataProvider(BaseDataProvider):
    """Synthetic provider generating schema-compliant candles."""

    def __init__(self, n_bars: int = 50, base_price: float = 2400.0):
        self.n_bars = n_bars
        self.base_price = base_price

    def get_candles(self, symbol: str, timeframe: str = "5m", lookback_bars: int = 50, **kwargs):
        now = datetime.now(timezone.utc)
        data = []
        for i in range(lookback_bars):
            t = now - timedelta(minutes=5 * (lookback_bars - i))
            p = self.base_price + i * 0.5
            data.append({
                "time": t,
                "open": p,
                "high": p + 2.0,
                "low": p - 1.5,
                "close": p + 1.0,
                "volume": 10000.0 + i * 100,
            })
        df = pd.DataFrame(data)
        df["time"] = pd.to_datetime(df["time"], utc=True)
        return df


# =============================================================================
# 1. CONSTANTS AND CATALOG TESTS
# =============================================================================

def test_indian_indexes_catalog():
    """Verify that core benchmark and sectoral indexes exist."""
    assert "NIFTY" in INDIAN_INDEXES
    assert "BANKNIFTY" in INDIAN_INDEXES
    assert "FINNIFTY" in INDIAN_INDEXES
    assert "MIDCPNIFTY" in INDIAN_INDEXES
    assert "SENSEX" in INDIAN_INDEXES
    assert "INDIAVIX" in INDIAN_INDEXES
    assert "NIFTYIT" in INDIAN_INDEXES

    # Verify exchanges
    assert INDIAN_INDEXES["NIFTY"]["exchange"] == "NSE"
    assert INDIAN_INDEXES["SENSEX"]["exchange"] == "BSE"
    assert INDIAN_INDEXES["NIFTYIT"]["symbol"] == "CNXIT"


def test_indian_stocks_catalog():
    """Verify standard liquid Indian equities in catalog."""
    assert "RELIANCE" in INDIAN_STOCKS
    assert "TCS" in INDIAN_STOCKS
    assert "HDFCBANK" in INDIAN_STOCKS
    assert "INFY" in INDIAN_STOCKS
    assert "SBIN" in INDIAN_STOCKS
    assert INDIAN_STOCKS["RELIANCE"]["exchange"] == "NSE"


# =============================================================================
# 2. SESSION AND TRADING HOURS TESTS
# =============================================================================

def test_session_manager_regular_trading_hour():
    """Verify market is detected as OPEN during regular trading hours (e.g. 10:30 AM IST on Wednesday)."""
    mgr = IndianMarketSessionManager()
    # 2026-09-23 was Wednesday
    ist_time = datetime(2026, 9, 23, 10, 30, tzinfo=mgr.tz)
    info = mgr.get_session_info(ist_time)
    assert info.status == IndianMarketStatus.OPEN
    assert info.is_trading_active is True
    assert mgr.is_market_open(ist_time) is True


def test_session_manager_pre_open():
    """Verify market is detected as PRE_OPEN between 09:00 and 09:15 IST."""
    mgr = IndianMarketSessionManager()
    ist_time = datetime(2026, 9, 23, 9, 5, tzinfo=mgr.tz)
    info = mgr.get_session_info(ist_time)
    assert info.status == IndianMarketStatus.PRE_OPEN
    assert info.is_trading_active is False
    assert mgr.is_pre_market(ist_time) is True


def test_session_manager_post_market():
    """Verify market is detected as POST_CLOSE between 15:30 and 16:00 IST."""
    mgr = IndianMarketSessionManager()
    ist_time = datetime(2026, 9, 23, 15, 45, tzinfo=mgr.tz)
    info = mgr.get_session_info(ist_time)
    assert info.status == IndianMarketStatus.POST_CLOSE
    assert info.is_trading_active is False


def test_session_manager_after_hours():
    """Verify market is detected as CLOSED after 16:00 IST."""
    mgr = IndianMarketSessionManager()
    ist_time = datetime(2026, 9, 23, 18, 0, tzinfo=mgr.tz)
    info = mgr.get_session_info(ist_time)
    assert info.status == IndianMarketStatus.CLOSED
    assert info.is_trading_active is False


def test_session_manager_weekend():
    """Verify Saturday and Sunday are detected as WEEKEND."""
    mgr = IndianMarketSessionManager()
    saturday = datetime(2026, 9, 26, 11, 0, tzinfo=mgr.tz)
    info = mgr.get_session_info(saturday)
    assert info.status == IndianMarketStatus.WEEKEND
    assert info.is_trading_active is False
    assert mgr.is_weekend(saturday) is True
    assert mgr.is_trading_day(saturday) is False


def test_session_manager_holiday():
    """Verify exchange declared holidays are recognized."""
    mgr = IndianMarketSessionManager(holidays=["2026-01-26"])
    republic_day = datetime(2026, 1, 26, 10, 30, tzinfo=mgr.tz)
    info = mgr.get_session_info(republic_day)
    assert info.status == IndianMarketStatus.HOLIDAY
    assert info.is_trading_active is False
    assert mgr.is_holiday(republic_day) is True
    assert mgr.is_trading_day(republic_day) is False


# =============================================================================
# 3. MODELS & METRICS TESTS
# =============================================================================

def test_market_breadth_adr_and_sentiment():
    """Test Advance-Decline Ratio and sentiment classification."""
    # Strongly bullish
    b1 = MarketBreadth(advances=40, declines=10, unchanged=0)
    assert b1.advance_decline_ratio == 4.0
    assert b1.sentiment == "STRONGLY_BULLISH"
    assert b1.total == 50

    # Neutral
    b2 = MarketBreadth(advances=25, declines=25, unchanged=0)
    assert b2.advance_decline_ratio == 1.0
    assert b2.sentiment == "NEUTRAL"

    # Strongly bearish
    b3 = MarketBreadth(advances=8, declines=40, unchanged=2)
    assert b3.advance_decline_ratio == 0.2
    assert b3.sentiment == "STRONGLY_BEARISH"

    # Zero declines edge case
    b4 = MarketBreadth(advances=50, declines=0, unchanged=0)
    assert b4.advance_decline_ratio == 50.0
    assert b4.sentiment == "STRONGLY_BULLISH"


def test_vix_regime_classification():
    """Test VIX categorization into LOW, NORMAL, ELEVATED, EXTREME using analyze_vix."""
    vix_low = analyze_vix(11.5, change=-0.4, percent_change=-3.3)
    assert vix_low.regime == VixRegime.LOW
    assert vix_low.current_vix == 11.5

    vix_norm = analyze_vix(15.2, change=0.1, percent_change=0.6)
    assert vix_norm.regime == VixRegime.NORMAL

    vix_elev = analyze_vix(21.0, change=1.5, percent_change=7.7)
    assert vix_elev.regime == VixRegime.ELEVATED

    vix_ext = analyze_vix(28.5, change=4.5, percent_change=18.7)
    assert vix_ext.regime == VixRegime.EXTREME



# =============================================================================
# 4. DATA PROVIDER & SYMBOL RESOLUTION TESTS
# =============================================================================

def test_indian_provider_symbol_resolution():
    """Verify symbol normalization across exchanges and conventions."""
    mock_sub = MockDataProvider()
    provider = IndianMarketDataProvider(underlying_provider=mock_sub)

    assert provider.resolve_symbol("NIFTY 50") == ("NIFTY", "NSE")
    assert provider.resolve_symbol("NIFTY") == ("NIFTY", "NSE")
    assert provider.resolve_symbol("BANKNIFTY") == ("BANKNIFTY", "NSE")
    assert provider.resolve_symbol("SENSEX") == ("SENSEX", "BSE")
    assert provider.resolve_symbol("RELIANCE") == ("RELIANCE", "NSE")
    assert provider.resolve_symbol("BSE:TCS") == ("TCS", "BSE")
    assert provider.resolve_symbol("INFY.NS") == ("INFY", "NSE")
    assert provider.resolve_symbol("ITC.BO") == ("ITC", "BSE")


def test_indian_provider_get_candles_schema():
    """Verify DataFrame structure returned conforms to BaseDataProvider contract."""
    mock_sub = MockDataProvider(n_bars=30)
    provider = IndianMarketDataProvider(underlying_provider=mock_sub)

    df = provider.get_candles("RELIANCE", timeframe="5m", lookback_bars=30)
    assert df is not None
    assert len(df) == 30
    assert list(df.columns) == ["time", "open", "high", "low", "close", "volume"]
    assert pd.api.types.is_datetime64_any_dtype(df["time"])
    assert provider.validate_schema(df) is True


# =============================================================================
# 5. MODULAR PIPELINE STAGES (FETCH, IDENTIFY, DETECT, VISUALIZE)
# =============================================================================

def test_provider_batch_extraction():
    """Test batch candlestick extraction via IndianMarketDataProvider."""
    mock_sub = MockDataProvider(n_bars=25)
    provider = IndianMarketDataProvider(underlying_provider=mock_sub)

    # Fetch multiple stocks
    df_rel = provider.get_candles("RELIANCE", timeframe="5m", lookback_bars=25)
    df_tcs = provider.get_candles("TCS", timeframe="5m", lookback_bars=25)
    assert df_rel is not None and df_tcs is not None
    assert len(df_rel) == 25
    assert len(df_tcs) == 25

    # Fetch index
    df_nifty = provider.get_candles("NIFTY", timeframe="15m", lookback_bars=20)
    assert df_nifty is not None
    assert len(df_nifty) == 20


def test_nse_client_indices_and_breadth():
    """Test NSEClient index querying, breadth computation, and quote fuzzy matching."""
    client = NSEClient()

    mock_nifty = IndianIndexQuote(name="NIFTY 50", symbol="NIFTY 50", last_price=23140.0, change=70.0, percent_change=0.3, advances=32, declines=18, unchanged=0)
    mock_vix = IndianIndexQuote(name="INDIA VIX", symbol="INDIA VIX", last_price=12.2, change=-0.5, percent_change=-3.9)

    client.get_all_indices = MagicMock(return_value=[mock_nifty, mock_vix])

    quote_nifty = client.get_index_quote("NIFTY")
    assert quote_nifty is not None
    assert quote_nifty.last_price == 23140.0

    breadth = client.get_market_breadth("NIFTY 50")
    assert breadth.advances == 32
    assert breadth.declines == 18
    assert breadth.sentiment == "MODERATELY_BULLISH"


# =============================================================================
# 6. STRATEGY & ANALYSIS INTEGRATION TESTS
# =============================================================================

def test_strategy_engine_on_indian_market_candles():
    """Test running PDFPriceActionStrategy directly on IndianMarketDataProvider feed."""
    mock_sub = MockDataProvider(n_bars=60, base_price=23000.0)
    provider = IndianMarketDataProvider(underlying_provider=mock_sub)
    strategy = PDFPriceActionStrategy()

    df = provider.get_candles("NIFTY", timeframe="5m", lookback_bars=60)
    assert df is not None
    completed = df.iloc[:-1].copy()

    signal = strategy.evaluate(completed, symbol="NIFTY")
    assert signal is None or hasattr(signal, "direction")


def test_trend_and_pattern_analysis():
    """Test pure trend analysis and pattern detection functions."""
    mock_sub = MockDataProvider(n_bars=60, base_price=2400.0)
    df = mock_sub.get_candles("RELIANCE", timeframe="5m", lookback_bars=60)

    # Pure Trend Analysis
    trend = analyze_trend(df, symbol="RELIANCE", timeframe="5m", lookback_bars=60)
    assert trend["symbol"] == "RELIANCE"
    assert "trend" in trend
    assert "ema20" in trend
    assert "ema50" in trend
    assert "support" in trend
    assert "resistance" in trend

    # Pure Pattern Detection
    patterns = scan_df_for_patterns(df)
    assert isinstance(patterns, list)


def test_interactive_chart_generation(tmp_path):
    """Test interactive TradingView HTML chart creation."""
    mock_sub = MockDataProvider(n_bars=30, base_price=2400.0)
    df = mock_sub.get_candles("RELIANCE", timeframe="5m", lookback_bars=30)

    chart_file = create_interactive_chart(df, symbol="RELIANCE", lookback_bars=30, auto_open=False)
    assert chart_file is not None
    assert chart_file.endswith(".html")


# =============================================================================
# 7. TRADEALGO PROCESS MODEL & PIPELINE TESTS
# =============================================================================

def test_algotrade_config_and_lifecycle():
    """Verify AlgoTrade configuration, unique AT- ID generation, and parallel lifecycle states."""
    config = AlgoTradeConfig(
        algo_name="Ishaq strategy 1",
        market="INDIAN_EQUITY",
        timeframe="5m",
        symbols=["RELIANCE", "TCS"],
        indicators=["EMA_20", "EMA_50", "RSI"],
        max_workers=4,
    )
    assert config.algo_name == "Ishaq strategy 1"
    assert config.algo_id.startswith("AT-Ishaqstrategy1-")
    assert config.market == "INDIAN_EQUITY"
    assert "EMA_20" in config.indicators

    mock_sub = MockDataProvider(n_bars=50, base_price=2400.0)
    algo = AlgoTrade(config=config, provider=mock_sub)
    assert algo.status == AlgoTradeStatus.IDLE
    assert algo.cycle_count == 0

    # Run parallel cycle across symbols
    results = algo.run_cycle()
    assert algo.status == AlgoTradeStatus.RUNNING
    assert algo.cycle_count == 1
    assert len(results) == 2  # RELIANCE and TCS

    metrics = algo.get_metrics()
    assert metrics["algo_name"] == "Ishaq strategy 1"
    assert metrics["cycle_count"] == 1
    assert metrics["status"] == "RUNNING"
    algo.close()


def test_algotrade_manager_and_legacy_alias():
    """Verify AlgoTradeManager multi-instance registration, parallel run, and TradeAlgo alias."""
    mgr = AlgoTradeManager()

    config1 = AlgoTradeConfig(algo_name="NiftyScalper", market="INDIAN_EQUITY", symbols=["NIFTY"])
    # Testing legacy TradeAlgoConfig alias
    config2 = TradeAlgoConfig(algo_name="ForexMajors", market="FOREX", symbols=["EUR/USD"])

    mock_sub = MockDataProvider(n_bars=40, base_price=23000.0)
    algo1 = mgr.register_algo(config1, provider=mock_sub)
    algo2 = mgr.register_algo(config2, provider=mock_sub)

    assert mgr.get_algo(algo1.algo_id) is algo1
    assert mgr.get_algo_by_name("NiftyScalper") is algo1
    assert mgr.get_algo_by_name("ForexMajors") is algo2

    algos = mgr.list_algos()
    assert len(algos) == 2
    assert any(a["algo_name"] == "NiftyScalper" for a in algos)
    assert any(a["algo_name"] == "ForexMajors" for a in algos)

    # Test parallel batch run
    all_res = mgr.run_all_cycles()
    assert "NiftyScalper" in all_res
    assert "ForexMajors" in all_res
    algo1.close()
    algo2.close()


def test_provider_caching_and_precalculation():
    """Verify BaseDataProvider thread-safe TTL caching and vectorized precalculation."""
    mock_sub = MockDataProvider(n_bars=30, base_price=2500.0)
    
    # Test caching
    df1 = mock_sub.get_cached_candles("RELIANCE", timeframe="5m", lookback_bars=30)
    df2 = mock_sub.get_cached_candles("RELIANCE", timeframe="5m", lookback_bars=30)
    assert df1 is not None and df2 is not None
    assert len(df1) == len(df2)

    # Test precalculation
    df_enriched = mock_sub.precalculate_indicators(df1, indicators=["EMA_20", "EMA_50", "RSI"])
    assert "ema_20" in df_enriched.columns
    assert "ema_50" in df_enriched.columns
    assert "rsi" in df_enriched.columns



