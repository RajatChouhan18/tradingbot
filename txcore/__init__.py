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
)
from txcore.providers.tradingview import TradingViewProvider
from txcore.strategies.pdf_price_action import PDFPriceActionStrategy
from txcore.filters.news_finnhub import FinnhubNewsFilter
from txcore.execution.telegram import TelegramNotifier
from txcore.execution.file_logger import log_signal_to_file, log_market_data_to_file
from txcore.audit.deduplicator import SignalDeduplicator
from txcore.audit.auditor import TradeAuditor
from txcore.visualization.chart_builder import create_interactive_chart

__version__ = "1.0.0"
__all__ = [
    "Direction",
    "CandleType",
    "PatternType",
    "SignalStatus",
    "Candle",
    "SetupResult",
    "Signal",
    "TradingViewProvider",
    "PDFPriceActionStrategy",
    "FinnhubNewsFilter",
    "TelegramNotifier",
    "log_signal_to_file",
    "log_market_data_to_file",
    "SignalDeduplicator",
    "TradeAuditor",
    "create_interactive_chart",
]
