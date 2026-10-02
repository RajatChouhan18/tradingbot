"""
txcore.providers.base
~~~~~~~~~~~~~~~~~~~~~
Abstract base class defining the standardized contract for all market data providers.
Extensible for TradingView, Zerodha Kite, Dhan, Angel One, OANDA, Finnhub, MT5.
Includes thread-safe candle caching and indicator precalculation hooks for maximum performance.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Tuple, List, Any
import time
import threading
import pandas as pd


class BaseDataProvider(ABC):
    """
    Standard interface for all candlestick data feeds.
    Every subclass must return a chronologically sorted DataFrame with columns:
    ['time', 'open', 'high', 'low', 'close']
    where 'time' is a UTC pd.Timestamp and prices are floats.
    Includes built-in computation-saving caching and precalculation capabilities.
    """

    def __init__(self, cache_ttl_seconds: float = 3.0):
        self._candle_cache: Dict[Tuple[str, str, int], Tuple[float, pd.DataFrame]] = {}
        self._cache_lock = threading.Lock()
        self._cache_ttl = cache_ttl_seconds

    @abstractmethod
    def get_candles(
        self,
        symbol: str,
        timeframe: str = "1m",
        lookback_bars: int = 180,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
        **kwargs
    ) -> Optional[pd.DataFrame]:
        """
        Fetches historical bars for a given symbol, timeframe, and optional date range.
        """
        pass

    def _ensure_cache_initialized(self):
        """Ensures caching structures are available even if subclass omitted super().__init__()."""
        if not hasattr(self, "_cache_lock"):
            self._cache_lock = threading.Lock()
        if not hasattr(self, "_candle_cache"):
            self._candle_cache = {}
        if not hasattr(self, "_cache_ttl"):
            self._cache_ttl = 3.0

    def get_cached_candles(
        self,
        symbol: str,
        timeframe: str = "1m",
        lookback_bars: int = 180,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
        **kwargs
    ) -> Optional[pd.DataFrame]:
        """
        Retrieves bars from the in-memory cache if fresh (within cache_ttl),
        otherwise fetches from the provider and updates cache. Saves network and compute.
        Supports date range filtering across past dates.
        """
        self._ensure_cache_initialized()
        cache_key = (
            symbol.upper().strip(),
            timeframe.lower(),
            lookback_bars,
            str(start_date or ""),
            str(end_date or ""),
        )
        now = time.time()

        with self._cache_lock:
            if cache_key in self._candle_cache:
                ts, cached_df = self._candle_cache[cache_key]
                if now - ts < self._cache_ttl:
                    return cached_df.copy()

        # Fetch fresh bars from underlying provider
        df = self.get_candles(
            symbol,
            timeframe=timeframe,
            lookback_bars=lookback_bars,
            start_date=start_date,
            end_date=end_date,
            **kwargs
        )
        if df is not None and not df.empty:
            with self._cache_lock:
                self._candle_cache[cache_key] = (now, df)
        return df

    def invalidate_cache(self, symbol: Optional[str] = None):
        """Invalidates all cached entries or entries matching a specific symbol."""
        self._ensure_cache_initialized()
        with self._cache_lock:
            if symbol:
                clean = symbol.upper().strip()
                keys_to_del = [k for k in self._candle_cache if k[0] == clean]
                for k in keys_to_del:
                    del self._candle_cache[k]
            else:
                self._candle_cache.clear()

    def precalculate_indicators(
        self,
        df: pd.DataFrame,
        indicators: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Precalculates requested indicators directly onto the DataFrame in a vectorized pass.
        Saves redundant downstream recomputations across strategy and analysis stages.
        """
        if df is None or df.empty or len(df) < 2:
            return df

        from txcore.analysis.indicators import (
            calculate_ema,
            calculate_rsi,
            calculate_vwap,
            calculate_bollinger_bands,
        )

        ind_set = set(indicators or ["EMA_20", "EMA_50", "RSI"])
        closes = df["close"]

        if "EMA_20" in ind_set and "ema_20" not in df.columns:
            df["ema_20"] = calculate_ema(closes, min(20, len(df)))

        if "EMA_50" in ind_set and "ema_50" not in df.columns:
            df["ema_50"] = calculate_ema(closes, min(50, len(df)))

        if "RSI" in ind_set and "rsi" not in df.columns:
            df["rsi"] = calculate_rsi(closes, period=14)

        if "VWAP" in ind_set and "volume" in df.columns and "vwap" not in df.columns:
            df["vwap"] = calculate_vwap(df)

        if "BOLLINGER" in ind_set and "bb_upper" not in df.columns:
            upper, mid, lower = calculate_bollinger_bands(closes, period=20)
            df["bb_upper"] = upper
            df["bb_mid"] = mid
            df["bb_lower"] = lower

        return df

    def validate_schema(self, df: Optional[pd.DataFrame]) -> bool:
        """
        Validates that the returned DataFrame conforms to the engine's strict schema.
        """
        if df is None or df.empty:
            return False
        required_cols = {"time", "open", "high", "low", "close"}
        if not required_cols.issubset(df.columns):
            return False
        if not pd.api.types.is_datetime64_any_dtype(df["time"]):
            return False
        return True
