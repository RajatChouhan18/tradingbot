"""
txcore.marketview.providers
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Unified market data provider adapters for AuraTrade.
"""

from txcore.marketview.providers.base import BaseDataProvider
from txcore.marketview.providers.tradingview import TradingViewProvider
from txcore.marketview.providers.binance import BinanceProvider
from txcore.marketview.providers.yahoo import YahooFinanceProvider
from txcore.marketview.providers.nse import NseDirectProvider
from txcore.marketview.providers.registry import ProviderRegistry, provider_registry

__all__ = [
    "BaseDataProvider",
    "TradingViewProvider",
    "BinanceProvider",
    "YahooFinanceProvider",
    "NseDirectProvider",
    "ProviderRegistry",
    "provider_registry",
]
