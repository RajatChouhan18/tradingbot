"""
txcore.marketview.providers.nse
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
NSE India direct market data provider adapter.
Fetches official spot quotes, indices, India VIX, and breadth from NSE India endpoints.
"""

import time
import logging
from typing import Optional, List
from datetime import datetime, timezone
import httpx

from txcore.marketview.models import CandleData, LiveQuote
from txcore.marketview.providers.base import BaseDataProvider
from txcore.marketview.providers.tradingview import TradingViewProvider

logger = logging.getLogger("auratrade.marketview.provider.nse")


class NseDirectProvider(BaseDataProvider):
    """
    Direct provider for National Stock Exchange of India (NSE).
    Supplies official spot ticks, Nifty index levels, and India VIX quotes.
    """

    BASE_URL = "https://www.nseindia.com"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
    }
    API_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/market-data/live-market-indices",
        "X-Requested-With": "XMLHttpRequest",
    }

    def __init__(self, cache_ttl_seconds: float = 3.0):
        super().__init__(name="NSE_DIRECT", cache_ttl_seconds=cache_ttl_seconds)
        self.tv_fallback = TradingViewProvider(cache_ttl_seconds=cache_ttl_seconds)
        self._cookies = {}
        self._last_cookie_time: float = 0.0

    async def _ensure_cookies(self, client: httpx.AsyncClient) -> None:
        """Primes cookies by loading the main NSE homepage if needed."""
        now = time.monotonic()
        if not self._cookies or (now - self._last_cookie_time) > 300.0:
            try:
                resp = await client.get(self.BASE_URL, headers=self.HEADERS, timeout=6.0)
                self._cookies = dict(resp.cookies)
                self._last_cookie_time = time.monotonic()
            except Exception as e:
                logger.warning(f"Could not prime NSE cookies: {e}")

    async def fetch_candles(
        self,
        symbol: str,
        timeframe: str = "5m",
        lookback: int = 180,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        **kwargs,
    ) -> List[CandleData]:
        """Fetches OHLCV candlestick data for Indian assets via TradingView engine."""
        kwargs_clean = dict(kwargs)
        exchange = kwargs_clean.pop("exchange", "NSE")
        return await self.tv_fallback.fetch_candles(
            symbol=symbol,
            timeframe=timeframe,
            lookback=lookback,
            start_time=start_time,
            end_time=end_time,
            exchange=exchange,
            **kwargs_clean,
        )

    async def fetch_live_quote(self, symbol: str, **kwargs) -> Optional[LiveQuote]:
        """Fetches official live spot quote from NSE."""
        clean_symbol = symbol.strip().upper()
        # Handle index quote vs equity quote
        is_index = clean_symbol in ["NIFTY 50", "NIFTY", "BANKNIFTY", "NIFTY BANK", "FINNIFTY", "INDIA VIX", "INDIAVIX"]
        kwargs_clean = dict(kwargs)
        exchange = kwargs_clean.pop("exchange", "NSE")

        try:
            async with httpx.AsyncClient(timeout=8.0, cookies=self._cookies) as client:
                await self._ensure_cookies(client)
                if is_index:
                    url = f"{self.BASE_URL}/api/allIndices"
                    resp = await client.get(url, headers=self.API_HEADERS)
                    if resp.status_code == 200:
                        data = resp.json()
                        indices = data.get("data", [])
                        target_name = "NIFTY 50" if clean_symbol in ["NIFTY", "NIFTY 50"] else clean_symbol
                        if clean_symbol in ["BANKNIFTY", "NIFTY BANK"]:
                            target_name = "NIFTY BANK"
                        elif clean_symbol in ["INDIA VIX", "INDIAVIX"]:
                            target_name = "INDIA VIX"

                        for idx in indices:
                            if idx.get("indexSymbol") == target_name or idx.get("index") == target_name:
                                last = float(idx.get("last", 0.0))
                                prev = float(idx.get("previousClose", last))
                                change = float(idx.get("variation", last - prev))
                                pct = float(idx.get("percentChange", 0.0))
                                return LiveQuote(
                                    symbol=clean_symbol,
                                    market="INDIAN_EQUITY",
                                    exchange="NSE",
                                    lastPrice=last,
                                    open=float(idx.get("open", last)),
                                    high=float(idx.get("high", last)),
                                    low=float(idx.get("low", last)),
                                    prevClose=prev,
                                    change=round(change, 2),
                                    changePct=round(pct, 2),
                                    volume=0.0,
                                    timestamp=datetime.now(timezone.utc),
                                    provider=self.name,
                                )
                else:
                    url = f"{self.BASE_URL}/api/quote-equity?symbol={clean_symbol}"
                    resp = await client.get(url, headers=self.API_HEADERS)
                    if resp.status_code == 200:
                        data = resp.json()
                        price_info = data.get("priceInfo", {})
                        last = float(price_info.get("lastPrice", 0.0))
                        prev = float(price_info.get("previousClose", last))
                        change = float(price_info.get("change", last - prev))
                        pct = float(price_info.get("pChange", 0.0))

                        return LiveQuote(
                            symbol=clean_symbol,
                            market="INDIAN_EQUITY",
                            exchange="NSE",
                            lastPrice=last,
                            open=float(price_info.get("open", last)),
                            high=float(price_info.get("intraDayHighLow", {}).get("max", last)),
                            low=float(price_info.get("intraDayHighLow", {}).get("min", last)),
                            prevClose=prev,
                            change=round(change, 2),
                            changePct=round(pct, 2),
                            volume=float(data.get("securityWiseDP", {}).get("quantityTraded", 0.0)),
                            timestamp=datetime.now(timezone.utc),
                            provider=self.name,
                        )
        except Exception as e:
            logger.warning(f"Direct NSE quote fetch failed for {clean_symbol}: {e}. Falling back to TradingView.")

        # Fallback to TradingView
        return await self.tv_fallback.fetch_live_quote(symbol=clean_symbol, exchange=exchange, **kwargs_clean)
