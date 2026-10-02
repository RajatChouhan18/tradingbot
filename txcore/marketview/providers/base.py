"""
txcore.marketview.providers.base
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Abstract Base Data Provider contract and thread-safe async TTL caching infrastructure.
"""

import asyncio
import time
import logging
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from txcore.marketview.models import CandleData, LiveQuote

logger = logging.getLogger("auratrade.marketview.provider.base")


class BaseDataProvider(ABC):
    """
    Abstract Base Class for all financial market data providers.
    Enforces the Liskov Substitution Principle (LSP) across Indian Equities,
    US Equities, Crypto, Forex, and MCX Commodities.
    """

    def __init__(self, name: str, cache_ttl_seconds: float = 0.8):
        self.name = name
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: Dict[Tuple[str, str], Tuple[float, List[CandleData]]] = {}
        self._quote_cache: Dict[str, Tuple[float, LiveQuote]] = {}
        self._lock = asyncio.Lock()

    @abstractmethod
    async def fetch_candles(
        self,
        symbol: str,
        timeframe: str = "5m",
        lookback: int = 180,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        **kwargs,
    ) -> List[CandleData]:
        """Subclass implementation to fetch chronologically sorted OHLCV candles."""
        pass

    @abstractmethod
    async def fetch_live_quote(self, symbol: str, **kwargs) -> Optional[LiveQuote]:
        """Subclass implementation to fetch the latest live quote / spot tick."""
        pass

    async def get_cached_candles(
        self,
        symbol: str,
        timeframe: str = "5m",
        lookback: int = 180,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        **kwargs,
    ) -> List[CandleData]:
        """
        Retrieves candles with async thread-safe TTL caching.
        Eliminates duplicate remote API queries when multiple modules or strategies
        request the same symbol/timeframe.
        """
        cache_key = (symbol.upper(), timeframe.lower())
        now = time.monotonic()

        async with self._lock:
            cached = self._cache.get(cache_key)
            if cached:
                cached_time, candles = cached
                if (now - cached_time) < self.cache_ttl_seconds and len(candles) >= lookback:
                    return list(candles[-lookback:])

        # Cache miss or expired — fetch from remote source
        candles = await self.fetch_candles(
            symbol=symbol,
            timeframe=timeframe,
            lookback=lookback,
            start_time=start_time,
            end_time=end_time,
            **kwargs,
        )

        async with self._lock:
            self._cache[cache_key] = (now, list(candles))

        return list(candles[-lookback:])

    async def get_cached_live_quote(self, symbol: str, **kwargs) -> Optional[LiveQuote]:
        """Retrieves live spot quote with thread-safe TTL caching."""
        clean_sym = symbol.upper()
        now = time.monotonic()

        async with self._lock:
            cached = self._quote_cache.get(clean_sym)
            if cached:
                cached_time, quote = cached
                if (now - cached_time) < self.cache_ttl_seconds:
                    return quote

        quote = await self.fetch_live_quote(symbol=clean_sym, **kwargs)
        if quote:
            async with self._lock:
                self._quote_cache[clean_sym] = (now, quote)

        return quote

    async def invalidate_cache(self, symbol: Optional[str] = None) -> None:
        """Invalidates cache for a specific symbol or all entries."""
        async with self._lock:
            if symbol:
                clean_sym = symbol.upper()
                keys_to_del = [k for k in self._cache if k[0] == clean_sym]
                for k in keys_to_del:
                    self._cache.pop(k, None)
                self._quote_cache.pop(clean_sym, None)
            else:
                self._cache.clear()
                self._quote_cache.clear()
