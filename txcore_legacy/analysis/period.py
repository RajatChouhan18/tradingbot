"""
txcore.analysis.period
~~~~~~~~~~~~~~~~~~~~~~
Utilities for parsing historical date ranges, estimating candle counts across timeframes,
and slicing DataFrames for strategy backtesting and historical evaluation.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Union, Tuple
import pandas as pd


def parse_datetime(val: Optional[Union[str, datetime]], is_end_of_day: bool = False) -> Optional[datetime]:
    """
    Parses flexible datetime formats into a UTC-aware datetime.
    Supports formats:
      - '2026-09-01'
      - '2026-09-01 09:15'
      - '2026-09-01 09:15:00'
      - '2026-09-01T09:15:00'
      - datetime object
    If is_end_of_day is True and a date-only string is provided, sets time to 23:59:59.
    Returns None if val is None, empty string, whitespace, null, or invalid.
    """
    if val is None:
        return None
    if isinstance(val, datetime):
        if pd.isna(val):
            return None
        dt = val if val.tzinfo is not None else val.replace(tzinfo=timezone.utc)
        dt = dt.astimezone(timezone.utc)
        if is_end_of_day and dt.hour == 0 and dt.minute == 0 and dt.second == 0:
            dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        return dt

    s = str(val).strip()
    if not s or s.lower() in ("none", "null", "nat", "nan", ""):
        return None

    # Date-only formats
    date_only_formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%Y",
    ]
    for fmt in date_only_formats:
        try:
            dt = datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
            if is_end_of_day:
                dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
            return dt
        except ValueError:
            pass

    # Datetime with time component
    datetime_formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
    ]
    for fmt in datetime_formats:
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    # Fallback to pandas to_datetime
    try:
        ts = pd.to_datetime(s, utc=True)
        if pd.isna(ts):
            return None
        res = ts.to_pydatetime()
        if pd.isna(res):
            return None
        if is_end_of_day and res.hour == 0 and res.minute == 0 and res.second == 0 and len(s) <= 10:
            res = res.replace(hour=23, minute=59, second=59, microsecond=999999)
        return res
    except Exception:
        return None


def timeframe_to_seconds(timeframe: str) -> int:
    """Converts a timeframe string (e.g. '1m', '5m', '15m', '1h', '1d') to seconds."""
    tf = timeframe.lower().strip()
    try:
        if tf.endswith("m") and tf[:-1].isdigit():
            return int(tf[:-1]) * 60
        elif tf.endswith("h") and tf[:-1].isdigit():
            return int(tf[:-1]) * 3600
        elif tf.endswith("d") and tf[:-1].isdigit():
            return int(tf[:-1]) * 86400
        elif tf.endswith("s") and tf[:-1].isdigit():
            return int(tf[:-1])
    except Exception:
        pass
    # Default 5 minutes
    return 300


def estimate_required_bars(
    start_dt: Optional[datetime],
    end_dt: Optional[datetime] = None,
    timeframe: str = "5m",
) -> int:
    """
    Estimates the number of bars needed from the present back to start_dt
    to ensure full coverage of the requested historical window.
    Because market feeds (TradingView, NSE, Zerodha) count n_bars backward from NOW,
    the fetch depth must cover the entire span from the current moment back to start_dt.
    Includes generous buffer for non-trading hours, overnight gaps, weekends, and holidays.
    """
    if start_dt is None or pd.isna(start_dt):
        return 60

    now = datetime.now(timezone.utc)
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=timezone.utc)

    # Calculate span from now back to start_dt
    try:
        span_from_now = (now - start_dt).total_seconds()
        if pd.isna(span_from_now) or span_from_now <= 0:
            span_from_now = 3600
    except Exception:
        span_from_now = 3600

    # Also respect target_end if provided
    if end_dt is not None and not pd.isna(end_dt):
        target_end = end_dt if end_dt.tzinfo is not None else end_dt.replace(tzinfo=timezone.utc)
        window_diff = max(60, (target_end - start_dt).total_seconds())
        # Use whichever is larger to guarantee full coverage
        total_seconds = max(span_from_now, window_diff)
    else:
        total_seconds = span_from_now

    tf_seconds = max(1, timeframe_to_seconds(timeframe))
    raw_bars = total_seconds // tf_seconds
    buffered_bars = int(raw_bars * 1.5) + 30
    return max(60, min(5000, buffered_bars))


def filter_candles_by_date(
    df: Optional[pd.DataFrame],
    start_date: Optional[Union[str, datetime]] = None,
    end_date: Optional[Union[str, datetime]] = None,
) -> Optional[pd.DataFrame]:
    """
    Filters a candlestick DataFrame to only include bars within [start_date, end_date].
    """
    if df is None or df.empty or "time" not in df.columns:
        return df

    start_dt = parse_datetime(start_date)
    end_dt = parse_datetime(end_date, is_end_of_day=True)

    filtered = df.copy()
    if start_dt is not None:
        filtered = filtered[filtered["time"] >= start_dt]
    if end_dt is not None:
        filtered = filtered[filtered["time"] <= end_dt]

    return filtered.reset_index(drop=True)
