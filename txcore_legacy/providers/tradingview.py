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

    def _resolve_symbol_exchange(self, symbol: str, override_exchange: Optional[str] = None) -> tuple:
        clean = symbol.strip().upper()

        # 1. Explicit override passed
        if override_exchange:
            if ":" in clean:
                clean = clean.split(":", 1)[1]
            return clean.replace("/", "").replace("_", ""), override_exchange

        # 2. Check if exchange prefix specified (e.g. NSE:IEX, BSE:TCS, BINANCE:BTCUSDT, NASDAQ:AAPL)
        if ":" in clean:
            exch, sym = clean.split(":", 1)
            return sym.strip(), exch.strip()

        # 3. Check suffix (e.g. IEX.NS, TCS.BO)
        if clean.endswith(".NS"):
            return clean[:-3], "NSE"
        if clean.endswith(".BO"):
            return clean[:-3], "BSE"

        # 4. Check pair mappings
        if clean in self.pair_mappings:
            return (
                self.pair_mappings[clean]["symbol"],
                self.pair_mappings[clean].get("exchange", self.default_exchange),
            )

        clean_symbol = clean.replace("/", "").replace("_", "")
        return clean_symbol, self.default_exchange

    def get_candles(
        self,
        symbol: str,
        timeframe: str = "1m",
        lookback_bars: int = 180,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
        max_retries: int = 2,
        exchange: Optional[str] = None,
        **kwargs
    ) -> Optional[pd.DataFrame]:
        from tvDatafeed import Interval
        from txcore.analysis.period import parse_datetime, estimate_required_bars, filter_candles_by_date

        target_exchange = exchange or kwargs.get("exchange")
        raw_symbol, exch = self._resolve_symbol_exchange(symbol, override_exchange=target_exchange)

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

        # Dynamically scale n_bars if a historical start_date is requested
        effective_bars = lookback_bars
        start_dt = parse_datetime(start_date)
        end_dt = parse_datetime(end_date)
        if start_dt is not None:
            needed = estimate_required_bars(start_dt, end_dt, timeframe)
            effective_bars = max(lookback_bars, needed)

        # Determine exchanges to attempt (with automatic secondary fallback for Indian equities)
        exchanges_to_try = [exch]
        if exch == "NSE":
            exchanges_to_try.append("BSE")
        elif exch == "BSE":
            exchanges_to_try.append("NSE")

        min_required = min(10, max(1, lookback_bars))
        raw = None
        for current_exch in exchanges_to_try:
            for attempt in range(max_retries + 1):
                tv = None
                try:
                    tv = self._create_instance()
                    raw = tv.get_hist(
                        symbol=raw_symbol,
                        exchange=current_exch,
                        interval=interval,
                        n_bars=effective_bars,
                    )
                    if raw is not None and not raw.empty and len(raw) >= min_required:
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
                    time.sleep(0.5)

            if raw is not None and not raw.empty and len(raw) >= min_required:
                break

        if raw is None or raw.empty or len(raw) < min_required:
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

        res = df[["time", "open", "high", "low", "close", "volume"]]

        # Apply date range filter if start_date or end_date are specified
        if start_dt or end_dt:
            res = filter_candles_by_date(res, start_date=start_dt, end_date=end_dt)

        return res
