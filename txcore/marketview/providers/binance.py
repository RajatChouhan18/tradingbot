"""
txcore.marketview.providers.binance
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Binance direct public REST provider for high-speed cryptocurrency data.
Requires zero authentication and provides sub-100ms global crypto feeds.
"""

import logging
from typing import Optional, List
from datetime import datetime, timezone
import httpx

from txcore.marketview.models import CandleData, LiveQuote
from txcore.marketview.providers.base import BaseDataProvider

logger = logging.getLogger("auratrade.marketview.provider.binance")

BINANCE_TIMEFRAME_MAP = {
    "1m": "1m",
    "3m": "3m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
}


class BinanceProvider(BaseDataProvider):
    """
    Direct Binance provider for real-time and historical crypto data (BTCUSDT, ETHUSDT, etc.).
    """

    def __init__(self, cache_ttl_seconds: float = 3.0):
        super().__init__(name="BINANCE", cache_ttl_seconds=cache_ttl_seconds)
        self.base_url = "https://api.binance.com/api/v3"

    async def fetch_candles(
        self,
        symbol: str,
        timeframe: str = "5m",
        lookback: int = 180,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        **kwargs,
    ) -> List[CandleData]:
        """Fetches OHLCV candlestick data directly from Binance public API."""
        clean_symbol = symbol.strip().upper().replace("/", "").replace("-", "")
        interval = BINANCE_TIMEFRAME_MAP.get(timeframe.lower(), "5m")

        params = {
            "symbol": clean_symbol,
            "interval": interval,
            "limit": min(lookback, 1000),
        }
        if start_time:
            params["startTime"] = int(start_time.timestamp() * 1000)
        if end_time:
            params["endTime"] = int(end_time.timestamp() * 1000)

        results: List[CandleData] = []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.base_url}/klines", params=params)
                if resp.status_code == 200:
                    raw_bars = resp.json()
                    for item in raw_bars:
                        # Binance kline structure:
                        # [0: Open time, 1: Open, 2: High, 3: Low, 4: Close, 5: Volume, 6: Close time, ...]
                        ts = datetime.fromtimestamp(item[0] / 1000.0, tz=timezone.utc)
                        results.append(
                            CandleData(
                                timestamp=ts,
                                open=float(item[1]),
                                high=float(item[2]),
                                low=float(item[3]),
                                close=float(item[4]),
                                volume=float(item[5]),
                            )
                        )
                else:
                    logger.warning(f"Binance klines error {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"Binance fetch_candles error for {clean_symbol}: {e}")

        results.sort(key=lambda c: c.timestamp)
        return results[-lookback:] if results else []

    async def fetch_live_quote(self, symbol: str, **kwargs) -> Optional[LiveQuote]:
        """Fetches 24hr ticker spot quote directly from Binance."""
        clean_symbol = symbol.strip().upper().replace("/", "").replace("-", "")
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.get(
                    f"{self.base_url}/ticker/24hr",
                    params={"symbol": clean_symbol},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return LiveQuote(
                        symbol=clean_symbol,
                        market="CRYPTO",
                        exchange="BINANCE",
                        lastPrice=float(data["lastPrice"]),
                        open=float(data["openPrice"]),
                        high=float(data["highPrice"]),
                        low=float(data["lowPrice"]),
                        prevClose=float(data["prevClosePrice"]),
                        change=float(data["priceChange"]),
                        changePct=float(data["priceChangePercent"]),
                        volume=float(data["volume"]),
                        timestamp=datetime.fromtimestamp(data["closeTime"] / 1000.0, tz=timezone.utc),
                        provider=self.name,
                    )
        except Exception as e:
            logger.error(f"Binance fetch_live_quote error for {clean_symbol}: {e}")

        return None
