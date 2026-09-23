"""
txcore.providers.base
~~~~~~~~~~~~~~~~~~~~~
Abstract base class defining the standardized contract for all market data providers.
Extensible for TradingView, Zerodha Kite, Dhan, Angel One, OANDA, Finnhub, MT5.
"""

from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd


class BaseDataProvider(ABC):
    """
    Standard interface for all candlestick data feeds.
    Every subclass must return a chronologically sorted DataFrame with columns:
    ['time', 'open', 'high', 'low', 'close']
    where 'time' is a UTC pd.Timestamp and prices are floats.
    """

    @abstractmethod
    def get_candles(
        self,
        symbol: str,
        timeframe: str = "1m",
        lookback_bars: int = 180,
        **kwargs
    ) -> Optional[pd.DataFrame]:
        """
        Fetches historical bars for a given symbol and timeframe.
        """
        pass

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
