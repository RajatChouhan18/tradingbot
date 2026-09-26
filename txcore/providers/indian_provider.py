"""
txcore.providers.indian_provider
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Specialized Indian market data provider conforming to the BaseDataProvider contract.
Coordinates TradingView feeds for Indian Equities (NSE/BSE) and Benchmark/Sectoral Indices.
"""

import logging
from typing import Optional, Dict, Any
import pandas as pd

from txcore.providers.base import BaseDataProvider
from txcore.providers.tradingview import TradingViewProvider
from config.settings import INDIAN_INDEXES, INDIAN_STOCKS

logger = logging.getLogger(__name__)


class IndianMarketDataProvider(BaseDataProvider):
    """
    Modular data provider dedicated to Indian stock and index market feeds.
    Conforms to BaseDataProvider returning normalized OHLCV DataFrames:
      ['time', 'open', 'high', 'low', 'close', 'volume']
    """

    def __init__(
        self,
        username: str = "",
        password: str = "",
        default_exchange: str = "NSE",
        underlying_provider: Optional[BaseDataProvider] = None,
    ):
        self.default_exchange = default_exchange
        if underlying_provider:
            self._provider = underlying_provider
        else:
            self._provider = TradingViewProvider(
                username=username,
                password=password,
                default_exchange=default_exchange,
            )

    def resolve_symbol(self, raw_symbol: str) -> tuple[str, str]:
        """
        Normalizes various user inputs to (symbol, exchange).
        Examples:
          'NIFTY 50'   -> ('NIFTY', 'NSE')
          'BANKNIFTY'  -> ('BANKNIFTY', 'NSE')
          'SENSEX'     -> ('SENSEX', 'BSE')
          'BSE:RELIANCE' -> ('RELIANCE', 'BSE')
          'TCS.NS'     -> ('TCS', 'NSE')
          'RELIANCE'   -> ('RELIANCE', 'NSE')
        """
        clean = raw_symbol.strip().upper()

        # Handle prefix like NSE:RELIANCE or BSE:SENSEX
        if ":" in clean:
            exch, sym = clean.split(":", 1)
            return sym.strip(), exch.strip()

        # Handle suffix like RELIANCE.NS or RELIANCE.BO
        if clean.endswith(".NS"):
            return clean[:-3], "NSE"
        if clean.endswith(".BO"):
            return clean[:-3], "BSE"

        # Check known canonical Indian indexes
        index_key = clean.replace(" ", "").replace("_", "")
        if index_key in INDIAN_INDEXES:
            meta = INDIAN_INDEXES[index_key]
            return meta.get("tv_symbol", meta["symbol"]), meta.get("exchange", "NSE")

        # Check known Indian stocks
        if clean in INDIAN_STOCKS:
            meta = INDIAN_STOCKS[clean]
            return meta["symbol"], meta.get("exchange", self.default_exchange)

        # Default fallback
        return clean.replace("/", "").replace("_", ""), self.default_exchange

    def get_candles(
        self,
        symbol: str,
        timeframe: str = "5m",
        lookback_bars: int = 180,
        **kwargs
    ) -> Optional[pd.DataFrame]:
        """
        Fetches historical candlestick bars for an Indian stock or index.
        Schema: ['time', 'open', 'high', 'low', 'close', 'volume']
        """
        clean_symbol, exchange = self.resolve_symbol(symbol)

        # Pass exchange directly or let underlying provider resolve it
        if isinstance(self._provider, TradingViewProvider):
            # Temporarily configure exchange mapping for this fetch
            prev_mappings = dict(self._provider.pair_mappings)
            self._provider.pair_mappings[clean_symbol] = {
                "symbol": clean_symbol,
                "exchange": exchange,
            }
            try:
                df = self._provider.get_candles(
                    clean_symbol,
                    timeframe=timeframe,
                    lookback_bars=lookback_bars,
                    **kwargs,
                )
            finally:
                self._provider.pair_mappings = prev_mappings
        else:
            df = self._provider.get_candles(
                clean_symbol,
                timeframe=timeframe,
                lookback_bars=lookback_bars,
                **kwargs,
            )

        if not self.validate_schema(df):
            return None

        return df
