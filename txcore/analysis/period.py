"""
txcore.analysis.period
~~~~~~~~~~~~~~~~~~~~~~
Utilities for parsing historical date ranges, estimating candle counts across timeframes,
and slicing DataFrames for strategy backtesting and historical evaluation.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Union, Tuple
import pandas as pd


def parse_datetime(val: Optional[Union[str, datetime]]) -> Optional[datetime]:
    """
    Parses flexible datetime formats into a UTC-aware datetime.
    Supports formats:
      - '2026-09-01'
      - '2026-09-01 09:15'
      - '2026-09-01 09:15:00'
      - '2026-09-01T09:15:00'
      - datetime object
    """
    if val is None:
        return None
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=timezone.utc)
        return val.astimezone(timezone.utc)

    s = str(val).strip()
    # Try common formats
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y/%m/%d",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d-%m-%Y",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    # Fallback to pandas to_datetime
    try:
        ts = pd.to_datetime(s, utc=True)
        return ts.to_pydatetime()
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
    start_dt: datetime,
    end_dt: Optional[datetime] = None,
    timeframe: str = "5m",
) -> int:
    """
    Estimates the number of bars needed from the present back to start_dt
    to ensure full coverage of the requested historical window.
    Includes buffer for non-trading hours, weekends, and holidays.
    """
    now = datetime.now(timezone.utc)
    target_end = end_dt or now

    # Total elapsed seconds from start_dt to now
    total_seconds = max(60, int((now - start_dt).total_seconds()))
    tf_seconds = timeframe_to_seconds(timeframe)

    raw_bars = total_seconds // tf_seconds
    # Add a 20% safety buffer to guarantee coverage
    buffered_bars = int(raw_bars * 1.2) + 20
    # Cap to reasonable maximum supported by providers (e.g. 5000 bars)
    return max(50, min(5000, buffered_bars))


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
    end_dt = parse_datetime(end_date)

    filtered = df.copy()
    if start_dt:
        filtered = filtered[filtered["time"] >= start_dt]
    if end_dt:
        filtered = filtered[filtered["time"] <= end_dt]

    return filtered.reset_index(drop=True)
