"""
txcore.providers.synthesizer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Market-agnostic real-time tick and quote synthesizer.
Dynamically merges real-time quotes, index ticks, and streaming exchange prices
into historical candlestick bars so that the active forming candle (index -1)
never lags behind the live market by 15 minutes or omits recent price action.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Union
import pandas as pd

logger = logging.getLogger(__name__)

TIMEFRAME_SECONDS: Dict[str, int] = {
    "1m": 60,
    "3m": 180,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "45m": 2700,
    "1h": 3600,
    "60m": 3600,
    "2h": 7200,
    "4h": 14400,
    "1d": 86400,
    "d": 86400,
}


def parse_timeframe_seconds(timeframe: str) -> int:
    """Parses a timeframe string (e.g. '1m', '5m', '15m', '1h', '1d') into total seconds."""
    clean = str(timeframe).lower().strip()
    if clean in TIMEFRAME_SECONDS:
        return TIMEFRAME_SECONDS[clean]
    if clean.endswith("m"):
        try:
            return int(clean[:-1]) * 60
        except ValueError:
            pass
    elif clean.endswith("h"):
        try:
            return int(clean[:-1]) * 3600
        except ValueError:
            pass
    elif clean.endswith("d"):
        try:
            return int(clean[:-1]) * 86400
        except ValueError:
            pass
    return 300  # Default 5-minute interval


def align_timestamp_to_timeframe(dt: datetime, tf_seconds: int) -> datetime:
    """
    Floors a timezone-aware UTC datetime to the nearest timeframe interval boundary.
    Example: 09:23:45 on a 5m (300s) boundary floors to 09:20:00 UTC.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    ts = dt.timestamp()
    floored_ts = ts - (ts % tf_seconds)
    return datetime.fromtimestamp(floored_ts, tz=timezone.utc)


class RealTimeTickSynthesizer:
    """
    Universal, market-agnostic real-time tick synthesizer.
    Combines historical lookback bars with live spot quotes/ticks to form
    and update the active candle (index -1) dynamically in memory.
    """

    @classmethod
    def synthesize_active_candle(
        cls,
        df: Optional[pd.DataFrame],
        quote: Any,
        timeframe: str = "5m",
        current_time: Optional[datetime] = None,
    ) -> Optional[pd.DataFrame]:
        """
        Synthesizes or updates the active forming candle at index -1 in df using
        the provided real-time quote/tick.

        Args:
            df: Historical candlestick DataFrame (must contain 'time', 'open', 'high', 'low', 'close', 'volume').
            quote: Real-time quote (StockQuote, IndexQuote, dict, or float price).
            timeframe: Execution timeframe (e.g. '1m', '5m', '15m', '1h').
            current_time: Reference time (defaults to quote timestamp or current UTC).

        Returns:
            Enriched DataFrame with zero-lag active candle at index -1.
        """
        if quote is None:
            return df.copy() if df is not None else None

        # Extract live price
        live_price = None
        if hasattr(quote, "last_price"):
            live_price = float(quote.last_price or 0.0)
        elif isinstance(quote, dict):
            live_price = float(quote.get("last_price") or quote.get("price") or quote.get("close") or 0.0)
        elif isinstance(quote, (int, float)):
            live_price = float(quote)

        if live_price is None or live_price <= 0:
            return df.copy() if df is not None else None

        # Extract volume
        live_volume = 0.0
        if hasattr(quote, "volume"):
            live_volume = float(quote.volume or 0.0)
        elif isinstance(quote, dict):
            live_volume = float(quote.get("volume") or 0.0)

        # Determine quote timestamp
        quote_dt = getattr(quote, "timestamp", None)
        if quote_dt is None and isinstance(quote, dict):
            quote_dt = quote.get("timestamp")
        if quote_dt is None:
            quote_dt = current_time or datetime.now(timezone.utc)

        if isinstance(quote_dt, str):
            try:
                quote_dt = pd.to_datetime(quote_dt, utc=True).to_pydatetime()
            except Exception:
                quote_dt = datetime.now(timezone.utc)
        elif quote_dt.tzinfo is None:
            quote_dt = quote_dt.replace(tzinfo=timezone.utc)
        else:
            quote_dt = quote_dt.astimezone(timezone.utc)

        tf_sec = parse_timeframe_seconds(timeframe)
        aligned_dt = align_timestamp_to_timeframe(quote_dt, tf_sec)

        # Handle empty or missing DataFrame
        if df is None or df.empty:
            return pd.DataFrame([{
                "time": aligned_dt,
                "open": live_price,
                "high": live_price,
                "low": live_price,
                "close": live_price,
                "volume": live_volume,
            }])

        res_df = df.copy()
        res_df["time"] = pd.to_datetime(res_df["time"], utc=True)

        last_row = res_df.iloc[-1]
        last_bar_time = pd.to_datetime(last_row["time"], utc=True)
        time_diff_sec = (aligned_dt - last_bar_time).total_seconds()

        # CASE 1: The latest bar in df is already within the current timeframe window
        if abs(time_diff_sec) < (tf_sec * 0.75):
            res_df.iloc[-1, res_df.columns.get_loc("close")] = live_price
            res_df.iloc[-1, res_df.columns.get_loc("high")] = max(float(last_row["high"]), live_price)
            res_df.iloc[-1, res_df.columns.get_loc("low")] = min(float(last_row["low"]), live_price)
            if live_volume > float(last_row.get("volume", 0.0)):
                res_df.iloc[-1, res_df.columns.get_loc("volume")] = live_volume
            return res_df

        # CASE 2: The current quote is newer than the latest bar in df (feed delay / new bar started)
        elif time_diff_sec > 0:
            # New candle has started! Use previous close or quote open
            prev_close = float(last_row["close"])
            quote_open = getattr(quote, "open", 0.0) if hasattr(quote, "open") else (quote.get("open", 0.0) if isinstance(quote, dict) else 0.0)
            open_price = float(quote_open) if (quote_open and quote_open > 0 and abs(time_diff_sec) < tf_sec * 1.5) else prev_close

            high_price = max(open_price, live_price)
            low_price = min(open_price, live_price)

            new_candle = pd.DataFrame([{
                "time": aligned_dt,
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": live_price,
                "volume": live_volume if live_volume > 0 else 0.0,
            }])
            res_df = pd.concat([res_df, new_candle], ignore_index=True)
            return res_df

        # CASE 3: Clock skew or historical timestamp
        else:
            res_df.iloc[-1, res_df.columns.get_loc("close")] = live_price
            res_df.iloc[-1, res_df.columns.get_loc("high")] = max(float(last_row["high"]), live_price)
            res_df.iloc[-1, res_df.columns.get_loc("low")] = min(float(last_row["low"]), live_price)
            return res_df

    @classmethod
    def get_forming_candle_summary(cls, df: pd.DataFrame) -> Dict[str, Any]:
        """Returns a diagnostic summary of the current forming candle at index -1."""
        if df is None or df.empty:
            return {"status": "NO_DATA"}
        last = df.iloc[-1]
        open_p = float(last["open"])
        close_p = float(last["close"])
        chg = close_p - open_p
        pct = (chg / open_p * 100.0) if open_p > 0 else 0.0
        return {
            "candle_time": str(last["time"]),
            "open": open_p,
            "high": float(last["high"]),
            "low": float(last["low"]),
            "close": close_p,
            "volume": float(last.get("volume", 0.0)),
            "change_from_open": round(chg, 2),
            "percent_from_open": round(pct, 2),
            "is_bullish": close_p >= open_p,
        }
