"""
Module 3: MarketView Engine (txcore.marketview)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Data Provider Layer, live streaming data, market-closed overlays, optional indicators/OI/VIX overlays,
and strict incremental rolling calculation (computing only new incoming candles).
"""

from txcore.marketview.models import (
    CandleData,
    LiveQuote,
    MarketStatusInfo,
    PatternMarker,
    ProviderTechnicals,
    MarketDataResponse,
)
from txcore.marketview.providers import (
    BaseDataProvider,
    TradingViewProvider,
    BinanceProvider,
    YahooFinanceProvider,
    NseDirectProvider,
    ProviderRegistry,
    provider_registry,
)
from txcore.marketview.session import (
    BaseMarketCalendar,
    IndianEquityCalendar,
    UsEquityCalendar,
    CryptoCalendar,
    ForexCalendar,
    McxCalendar,
    MarketSessionManager,
    session_manager,
)
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
)
from txcore.marketview.incremental import (
    IncrementalMarketState,
    IncrementalEngine,
    incremental_engine,
)

__all__ = [
    "CandleData",
    "LiveQuote",
    "MarketStatusInfo",
    "PatternMarker",
    "ProviderTechnicals",
    "MarketDataResponse",
    "BaseDataProvider",
    "TradingViewProvider",
    "BinanceProvider",
    "YahooFinanceProvider",
    "NseDirectProvider",
    "ProviderRegistry",
    "provider_registry",
    "BaseMarketCalendar",
    "IndianEquityCalendar",
    "UsEquityCalendar",
    "CryptoCalendar",
    "ForexCalendar",
    "McxCalendar",
    "MarketSessionManager",
    "session_manager",
    "compute_market_technicals",
    "detect_candlestick_patterns",
    "calculate_ema",
    "calculate_sma",
    "calculate_vwap",
    "calculate_rsi",
    "calculate_macd",
    "calculate_bollinger_bands",
    "calculate_atr",
    "classify_vix_regime",
    "IncrementalMarketState",
    "IncrementalEngine",
    "incremental_engine",
]
