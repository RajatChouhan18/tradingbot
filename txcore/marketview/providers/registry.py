"""
txcore.marketview.providers.registry
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Provider Registry and Dynamic Routing Engine.
Routes market data requests to the optimal primary provider with automatic resilient fallback.
"""

import logging
from typing import Dict, Optional, List, Tuple
from datetime import datetime

from txcore.marketview.models import CandleData, LiveQuote
from txcore.marketview.providers.base import BaseDataProvider
from txcore.marketview.providers.tradingview import TradingViewProvider
from txcore.marketview.providers.binance import BinanceProvider
from txcore.marketview.providers.yahoo import YahooFinanceProvider
from txcore.marketview.providers.nse import NseDirectProvider

logger = logging.getLogger("auratrade.marketview.registry")


class ProviderRegistry:
    """
    Central factory registry for financial market data providers.
    Implements Open/Closed Principle (OCP) and Dependency Inversion (DIP).
    """

    def __init__(self):
        # Instantiate singleton adapters
        self.tv_provider = TradingViewProvider()
        self.binance_provider = BinanceProvider()
        self.yahoo_provider = YahooFinanceProvider()
        self.nse_provider = NseDirectProvider()

        # Market routing table: Market Code -> (Primary Provider, Secondary Fallback Provider)
        self._routing_table: Dict[str, Tuple[BaseDataProvider, Optional[BaseDataProvider]]] = {
            "INDIAN_EQUITY": (self.nse_provider, self.tv_provider),
            "US_EQUITY": (self.tv_provider, self.yahoo_provider),
            "CRYPTO": (self.binance_provider, self.tv_provider),
            "FOREX": (self.tv_provider, self.yahoo_provider),
            "MCX": (self.tv_provider, self.yahoo_provider),
            "GLOBAL": (self.tv_provider, self.yahoo_provider),
        }

    def register_provider(
        self,
        market: str,
        primary: BaseDataProvider,
        fallback: Optional[BaseDataProvider] = None,
    ) -> None:
        """Registers or overrides a provider for a specific market class."""
        self._routing_table[market.upper()] = (primary, fallback)

    def get_provider(self, market: str) -> BaseDataProvider:
        """Returns the primary provider for the given market code."""
        routing = self._routing_table.get(market.upper())
        if routing:
            return routing[0]
        return self.tv_provider

    async def fetch_candles_with_fallback(
        self,
        symbol: str,
        market: str = "INDIAN_EQUITY",
        timeframe: str = "5m",
        lookback: int = 180,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        **kwargs,
    ) -> List[CandleData]:
        """
        Fetches candles from primary provider; automatically falls back to secondary
        provider if primary fails or returns empty data.
        """
        clean_market = market.upper()
        primary, fallback = self._routing_table.get(clean_market, (self.tv_provider, None))

        try:
            candles = await primary.get_cached_candles(
                symbol=symbol,
                timeframe=timeframe,
                lookback=lookback,
                start_time=start_time,
                end_time=end_time,
                **kwargs,
            )
            if candles:
                return candles
        except Exception as e:
            logger.warning(f"Primary provider '{primary.name}' failed for {symbol} ({clean_market}): {e}")

        # Try fallback if available
        if fallback:
            try:
                logger.info(f"Flipping to fallback provider '{fallback.name}' for {symbol}")
                candles = await fallback.get_cached_candles(
                    symbol=symbol,
                    timeframe=timeframe,
                    lookback=lookback,
                    start_time=start_time,
                    end_time=end_time,
                    **kwargs,
                )
                if candles:
                    return candles
            except Exception as e:
                logger.error(f"Fallback provider '{fallback.name}' also failed for {symbol}: {e}")

        return []

    async def fetch_live_quote_with_fallback(
        self,
        symbol: str,
        market: str = "INDIAN_EQUITY",
        **kwargs,
    ) -> Optional[LiveQuote]:
        """Fetches live spot quote with automatic fallback failover."""
        clean_market = market.upper()
        primary, fallback = self._routing_table.get(clean_market, (self.tv_provider, None))

        try:
            quote = await primary.get_cached_live_quote(symbol=symbol, **kwargs)
            if quote:
                return quote
        except Exception as e:
            logger.warning(f"Primary provider '{primary.name}' live quote failed for {symbol}: {e}")

        if fallback:
            try:
                quote = await fallback.get_cached_live_quote(symbol=symbol, **kwargs)
                if quote:
                    return quote
            except Exception as e:
                logger.error(f"Fallback provider '{fallback.name}' live quote failed for {symbol}: {e}")

        return None


# Global singleton registry instance
provider_registry = ProviderRegistry()
