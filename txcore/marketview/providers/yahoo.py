"""
txcore.marketview.providers.yahoo
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Yahoo Finance global fallback provider adapter for US Equities, Forex, and Global Indices.
"""

import logging
from typing import Optional, List
from datetime import datetime, timezone
import httpx

from txcore.marketview.models import CandleData, LiveQuote
from txcore.marketview.providers.base import BaseDataProvider

logger = logging.getLogger("auratrade.marketview.provider.yahoo")

YAHOO_TIMEFRAME_MAP = {
    "1m": "1m",
    "2m": "2m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "60m": "60m",
    "1h": "1h",
    "1d": "1d",
}


class YahooFinanceProvider(BaseDataProvider):
    """
    Yahoo Finance provider adapter acting as a global secondary / fallback provider.
    """

    def __init__(self, cache_ttl_seconds: float = 5.0):
        super().__init__(name="YAHOO_FINANCE", cache_ttl_seconds=cache_ttl_seconds)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
        }

    async def fetch_candles(
        self,
        symbol: str,
        timeframe: str = "5m",
        lookback: int = 180,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        **kwargs,
    ) -> List[CandleData]:
        """Fetches OHLCV bars from Yahoo Finance chart API."""
        clean_symbol = symbol.strip().upper()
        # Normalization for Yahoo symbols
        if clean_symbol in ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCHF"]:
            clean_symbol = f"{clean_symbol}=X"

        interval = YAHOO_TIMEFRAME_MAP.get(timeframe.lower(), "5m")
        # Determine range query parameter
        if interval in ["1m", "2m"]:
            range_param = "5d"
        elif interval in ["5m", "15m", "30m"]:
            range_param = "1mo"
        elif interval in ["60m", "1h"]:
            range_param = "3mo"
        else:
            range_param = "1y"

        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{clean_symbol}"
        params = {
            "interval": interval,
            "range": range_param,
            "includePrePost": "false",
        }

        results: List[CandleData] = []
        try:
            async with httpx.AsyncClient(timeout=10.0, headers=self.headers) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    chart = data.get("chart", {}).get("result", [])
                    if chart:
                        res = chart[0]
                        timestamps = res.get("timestamp", [])
                        quote_data = res.get("indicators", {}).get("quote", [{}])[0]
                        opens = quote_data.get("open", [])
                        highs = quote_data.get("high", [])
                        lows = quote_data.get("low", [])
                        closes = quote_data.get("close", [])
                        volumes = quote_data.get("volume", [])

                        for i, ts_val in enumerate(timestamps):
                            if (
                                i < len(opens)
                                and opens[i] is not None
                                and highs[i] is not None
                                and lows[i] is not None
                                and closes[i] is not None
                            ):
                                ts = datetime.fromtimestamp(ts_val, tz=timezone.utc)
                                if start_time and ts < start_time:
                                    continue
                                if end_time and ts > end_time:
                                    continue
                                vol = float(volumes[i]) if (i < len(volumes) and volumes[i] is not None) else 0.0
                                results.append(
                                    CandleData(
                                        timestamp=ts,
                                        open=float(opens[i]),
                                        high=float(highs[i]),
                                        low=float(lows[i]),
                                        close=float(closes[i]),
                                        volume=vol,
                                    )
                                )
                else:
                    logger.warning(f"Yahoo chart error {resp.status_code} for {clean_symbol}")
        except Exception as e:
            logger.error(f"Yahoo fetch_candles error for {clean_symbol}: {e}")

        results.sort(key=lambda c: c.timestamp)
        return results[-lookback:] if results else []

    async def fetch_live_quote(self, symbol: str, **kwargs) -> Optional[LiveQuote]:
        """Fetches live quote from Yahoo Finance."""
        clean_symbol = symbol.strip().upper()
        if clean_symbol in ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCHF"]:
            clean_symbol = f"{clean_symbol}=X"

        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{clean_symbol}?interval=1m&range=1d"
        try:
            async with httpx.AsyncClient(timeout=8.0, headers=self.headers) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    chart = data.get("chart", {}).get("result", [])
                    if chart:
                        meta = chart[0].get("meta", {})
                        regular_price = meta.get("regularMarketPrice", 0.0)
                        prev_close = meta.get("chartPreviousClose", meta.get("previousClose", regular_price))
                        change = regular_price - prev_close
                        change_pct = (change / prev_close * 100.0) if prev_close != 0 else 0.0

                        return LiveQuote(
                            symbol=symbol.upper(),
                            market="GLOBAL",
                            exchange=meta.get("exchangeName", "GLOBAL"),
                            lastPrice=float(regular_price),
                            open=float(meta.get("regularMarketOpen", regular_price)),
                            high=float(meta.get("regularMarketDayHigh", regular_price)),
                            low=float(meta.get("regularMarketDayLow", regular_price)),
                            prevClose=float(prev_close),
                            change=round(change, 4),
                            changePct=round(change_pct, 2),
                            volume=float(meta.get("regularMarketVolume", 0.0)),
                            timestamp=datetime.fromtimestamp(meta.get("regularMarketTime", datetime.now().timestamp()), tz=timezone.utc),
                            provider=self.name,
                        )
        except Exception as e:
            logger.error(f"Yahoo fetch_live_quote error for {clean_symbol}: {e}")

        return None
