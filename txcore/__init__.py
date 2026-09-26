"""
txcore
~~~~~~
Extensible Multi-Market Quantitative & Price Action Trading Framework.
"""

from txcore.models.types import (
    Direction,
    CandleType,
    PatternType,
    SignalStatus,
    Candle,
    SetupResult,
    Signal,
    MarketStatus,
    VixRegime,
    IndexQuote,
    StockQuote,
    MarketBreadth,
    MarketSessionInfo,
    VixAnalysis,
    OptionChainSummary,
    IndianMarketStatus,
    IndianIndexQuote,
    IndianStockQuote,
)
from txcore.providers.base import BaseDataProvider
from txcore.providers.tradingview import TradingViewProvider
from txcore.providers.indian_provider import IndianMarketDataProvider
from txcore.providers.nse_provider import NSEClient
from txcore.providers.session_manager import (
    MarketSessionManager,
    create_indian_session_manager,
    IndianMarketSessionManager,
)
from txcore.algotrade import (
    AlgoTrade,
    AlgoTradeConfig,
    AlgoTradeStatus,
    AlgoTradeManager,
    TradeAlgo,
    TradeAlgoConfig,
    TradeAlgoStatus,
    TradeAlgoManager,
)
from txcore.strategies.pdf_price_action import PDFPriceActionStrategy
from txcore.filters.news_finnhub import FinnhubNewsFilter
from txcore.execution.telegram import TelegramNotifier
from txcore.execution.file_logger import log_signal_to_file, log_market_data_to_file
from txcore.audit.deduplicator import SignalDeduplicator
from txcore.audit.auditor import TradeAuditor
from txcore.visualization.chart_builder import (
    create_interactive_chart,
    build_tradingview_chart_html,
    build_plotly_chart,
    recreate_tradingview_chart,
    audit_pair_patterns,
    run_test_signal,
)
from txcore.analysis.indicators import analyze_trend, calculate_rsi, calculate_ema
from txcore.analysis.volatility import analyze_vix
from config.settings import INDIAN_INDEXES, INDIAN_STOCKS

__version__ = "2.0.0"
__all__ = [
    # Domain Models
    "Direction",
    "CandleType",
    "PatternType",
    "SignalStatus",
    "Candle",
    "SetupResult",
    "Signal",
    "MarketStatus",
    "VixRegime",
    "IndexQuote",
    "StockQuote",
    "MarketBreadth",
    "MarketSessionInfo",
    "VixAnalysis",
    "OptionChainSummary",
    "IndianMarketStatus",
    "IndianIndexQuote",
    "IndianStockQuote",
    # Providers
    "BaseDataProvider",
    "TradingViewProvider",
    "IndianMarketDataProvider",
    "NSEClient",
    "MarketSessionManager",
    "create_indian_session_manager",
    "IndianMarketSessionManager",
    # AlgoTrade Process Model & Pipeline
    "AlgoTrade",
    "AlgoTradeConfig",
    "AlgoTradeStatus",
    "AlgoTradeManager",
    "TradeAlgo",
    "TradeAlgoConfig",
    "TradeAlgoStatus",
    "TradeAlgoManager",
    # Reference Catalog
    "INDIAN_INDEXES",
    "INDIAN_STOCKS",
    # Strategies & Filters
    "PDFPriceActionStrategy",
    "FinnhubNewsFilter",
    # Execution & Audit
    "TelegramNotifier",
    "log_signal_to_file",
    "log_market_data_to_file",
    "SignalDeduplicator",
    "TradeAuditor",
    # Visualization
    "create_interactive_chart",
    "build_tradingview_chart_html",
    "build_plotly_chart",
    "recreate_tradingview_chart",
    "audit_pair_patterns",
    "run_test_signal",
    "run_chart_cli",
    # Analysis
    "analyze_trend",
    "analyze_vix",
    "calculate_rsi",
    "calculate_ema",
]


def __getattr__(name: str):
    if name == "run_chart_cli":
        from txcore.visualization.chart_cli import run_chart_cli
        return run_chart_cli
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
