"""
txcore.marketview.providers.tradingview
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
TradingView multi-asset market data provider adapter.
Fetches authentic real-time and historical OHLCV candlestick data across global markets.
"""

import asyncio
import logging
from typing import Optional, List
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

from txcore.marketview.models import CandleData, LiveQuote
from txcore.marketview.providers.base import BaseDataProvider
from txcore.catalog.historical import fetch_tradingview_bars

logger = logging.getLogger("auratrade.marketview.provider.tradingview")

_tv_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="tv_provider_worker")


class TradingViewProvider(BaseDataProvider):
    """
    TradingView multi-asset market data provider.
    Supports Indian Equities (NSE/BSE), US Equities (NASDAQ/NYSE), Crypto, Forex, and MCX.
    """

    def __init__(self, cache_ttl_seconds: float = 3.0):
        super().__init__(name="TRADINGVIEW", cache_ttl_seconds=cache_ttl_seconds)

    async def fetch_candles(
        self,
        symbol: str,
        timeframe: str = "5m",
        lookback: int = 180,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        exchange: str = "NSE",
        **kwargs,
    ) -> List[CandleData]:
        """Fetches OHLCV candles asynchronously using TradingView provider."""
        clean_symbol = symbol.strip().upper()
        clean_exchange = exchange.strip().upper() if exchange else "NSE"

        loop = asyncio.get_running_loop()
        try:
            bars = await loop.run_in_executor(
                _tv_executor,
                fetch_tradingview_bars,
                clean_symbol,
                clean_exchange,
                timeframe,
                lookback,
                3,  # max_retries
            )
        except Exception as e:
            logger.error(f"Error fetching TradingView bars for {clean_symbol}: {e}")
            bars = []

        results: List[CandleData] = []
        for b in bars:
            ts = b["timestamp"]
            if start_time and ts < start_time:
                continue
            if end_time and ts > end_time:
                continue
            results.append(
                CandleData(
                    timestamp=ts,
                    open=float(b["open"]),
                    high=float(b["high"]),
                    low=float(b["low"]),
                    close=float(b["close"]),
                    volume=float(b.get("volume", 0.0)),
                )
            )

        # Ensure chronological ordering
        results.sort(key=lambda c: c.timestamp)
        return results[-lookback:] if results else []

    async def fetch_live_quote(self, symbol: str, exchange: str = "NSE", **kwargs) -> Optional[LiveQuote]:
        """Fetches the latest spot tick / quote from the newest candle."""
        candles = await self.fetch_candles(symbol=symbol, timeframe="1m", lookback=2, exchange=exchange, **kwargs)
        if not candles:
            return None

        latest = candles[-1]
        prev = candles[-2] if len(candles) > 1 else latest
        change = latest.close - prev.close if len(candles) > 1 else 0.0
        change_pct = (change / prev.close * 100.0) if prev.close != 0 else 0.0

        return LiveQuote(
            symbol=symbol.upper(),
            market="GLOBAL",
            exchange=exchange.upper(),
            lastPrice=latest.close,
            open=latest.open,
            high=latest.high,
            low=latest.low,
            prevClose=prev.close,
            change=round(change, 4),
            changePct=round(change_pct, 2),
            volume=latest.volume,
            timestamp=latest.timestamp,
            provider=self.name,
        )
