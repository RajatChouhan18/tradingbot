"""
txcore.providers.tradingview
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Resilient TradingView data provider wrapping tvDatafeed.
Features automatic socket closure, transient disconnection recovery, and schema normalization.
"""

import time
import logging
from typing import Optional, Dict
import pandas as pd
from txcore.providers.base import BaseDataProvider

# Suppress repetitive websocket connection warnings from tvDatafeed library
logging.getLogger("tvDatafeed.main").setLevel(logging.CRITICAL)


class TradingViewProvider(BaseDataProvider):
    """
    Connects to TradingView's free or authenticated feed.
    Supports Forex (FX_IDC), Indian Markets (NSE/BSE), and global equities.
    """

    def __init__(
        self,
        username: str = "",
        password: str = "",
        default_exchange: str = "FX_IDC",
        pair_mappings: Optional[Dict[str, Dict[str, str]]] = None,
    ):
        self.username = username
        self.password = password
        self.default_exchange = default_exchange
        self.pair_mappings = pair_mappings or {}

    def _create_instance(self):
        from tvDatafeed import TvDatafeed
        if self.username and self.password:
            return TvDatafeed(username=self.username, password=self.password)
        return TvDatafeed()

    def _resolve_symbol_exchange(self, symbol: str) -> tuple:
        if symbol in self.pair_mappings:
            return (
                self.pair_mappings[symbol]["symbol"],
                self.pair_mappings[symbol].get("exchange", self.default_exchange),
            )
        clean_symbol = symbol.replace("/", "").replace("_", "")
        return clean_symbol, self.default_exchange

    def get_candles(
        self,
        symbol: str,
        timeframe: str = "1m",
        lookback_bars: int = 180,
        max_retries: int = 2,
        **kwargs
    ) -> Optional[pd.DataFrame]:
        from tvDatafeed import Interval

        raw_symbol, exchange = self._resolve_symbol_exchange(symbol)

        # Map timeframe string to tvDatafeed Interval
        interval_map = {
            "1m": Interval.in_1_minute,
            "3m": Interval.in_3_minute,
            "5m": Interval.in_5_minute,
            "15m": Interval.in_15_minute,
            "1h": Interval.in_1_hour,
            "1d": Interval.in_daily,
        }
        interval = interval_map.get(timeframe.lower(), Interval.in_1_minute)

        raw = None
        for attempt in range(max_retries + 1):
            tv = None
            try:
                tv = self._create_instance()
                raw = tv.get_hist(
                    symbol=raw_symbol,
                    exchange=exchange,
                    interval=interval,
                    n_bars=lookback_bars,
                )
                if raw is not None and not raw.empty and len(raw) >= 10:
                    break
            except Exception:
                pass
            finally:
                if tv is not None and hasattr(tv, "ws") and tv.ws:
                    try:
                        tv.ws.close()
                    except Exception:
                        pass

            if attempt < max_retries:
                time.sleep(1.0)

        if raw is None or raw.empty or len(raw) < 10:
            return None

        # Reset DatetimeIndex to standard column
        df = raw.reset_index().rename(columns={"datetime": "time"})
        df["time"] = pd.to_datetime(df["time"], utc=True)

        for col in ["open", "high", "low", "close"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        if "volume" in df.columns:
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0.0)
        else:
            df["volume"] = 0.0

        df = df.dropna(subset=["time", "open", "high", "low", "close"]).drop_duplicates("time")
        df = df.sort_values("time").reset_index(drop=True)

        return df[["time", "open", "high", "low", "close", "volume"]]
