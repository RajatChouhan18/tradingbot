"""
txcore.catalog.historical
~~~~~~~~~~~~~~~~~~~~~~~~~
20-Day 1m & 5m Historical OHLCV Data Pre-Seeder and Retrieval Engine.
Connects to TradingView's lightweight feed to fetch authentic market candlestick data,
normalizes intervals, and persists bars directly into the unified PostgreSQL `market_candles` table.

Guarantees:
- Unified storage: Both historical and live streaming bars reside in `market_candles`.
- Zero synthetic dummy data: Only real market prices from TradingView.
- High-speed indexed lookups on [symbol, timeframe, timestamp DESC].
- Mandatory audit tracking (createdBy = "TV_HISTORICAL_SEEDER").
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import pandas as pd
from tvDatafeed import TvDatafeed, Interval

from txcore.database import db

logger = logging.getLogger("auratrade.catalog.historical")

TIMEFRAME_MAP = {
    "1m": Interval.in_1_minute,
    "3m": Interval.in_3_minute,
    "5m": Interval.in_5_minute,
    "15m": Interval.in_15_minute,
    "1h": Interval.in_1_hour,
    "1d": Interval.in_daily,
}


def fetch_tradingview_bars(
    symbol: str,
    exchange: str,
    timeframe: str = "5m",
    n_bars: int = 500,
    max_retries: int = 3,
) -> List[Dict[str, Any]]:
    """
    Synchronously fetches historical OHLCV bars from TradingView with robust retry
    and fallback exchange recovery. Safely terminates sockets.
    """
    import time
    interval = TIMEFRAME_MAP.get(timeframe.lower(), Interval.in_5_minute)

    # Determine fallback exchanges
    exchanges_to_try = [exchange.upper()]
    if exchange.upper() == "NSE":
        exchanges_to_try.append("BSE")
    elif exchange.upper() == "BSE":
        exchanges_to_try.append("NSE")

    df = None
    for curr_exch in exchanges_to_try:
        for attempt in range(max_retries):
            tv = None
            try:
                tv = TvDatafeed()
                df = tv.get_hist(
                    symbol=symbol,
                    exchange=curr_exch,
                    interval=interval,
                    n_bars=n_bars,
                )
                if df is not None and not df.empty:
                    break
            except Exception as e:
                logger.debug(f"Attempt {attempt + 1} failed for {curr_exch}:{symbol}: {e}")
            finally:
                if tv is not None and hasattr(tv, "ws") and tv.ws:
                    try:
                        tv.ws.close()
                    except Exception:
                        pass
            if attempt < max_retries - 1:
                time.sleep(0.6)

        if df is not None and not df.empty:
            break

    if df is None or df.empty:
        logger.warning(f"No bars returned for {exchange}:{symbol} at {timeframe}")
        return []

    bars: List[Dict[str, Any]] = []
    for dt_idx, row in df.iterrows():
        # Convert pandas Timestamp to UTC datetime
        ts = dt_idx.to_pydatetime()
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        else:
            ts = ts.astimezone(timezone.utc)

        bars.append(
            {
                "symbol": symbol.upper(),
                "timeframe": timeframe.lower(),
                "timestamp": ts,
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"]) if "volume" in row and pd.notna(row["volume"]) else 0.0,
            }
        )
    return bars


async def save_candles_to_database(bars: List[Dict[str, Any]]) -> int:
    """
    Persists a batch of candlestick dictionaries into the unified `market_candles` table.
    Uses upsert or insert-with-skip-duplicates to maintain idempotency.
    """
    if not bars:
        return 0

    inserted_count = 0
    for b in bars:
        try:
            # Check existing to prevent duplicate unique key violations
            existing = await db.marketcandle.find_unique(
                where={
                    "symbol_timeframe_timestamp": {
                        "symbol": b["symbol"],
                        "timeframe": b["timeframe"],
                        "timestamp": b["timestamp"],
                    }
                }
            )
            if not existing:
                await db.marketcandle.create(
                    data={
                        "symbol": b["symbol"],
                        "timeframe": b["timeframe"],
                        "timestamp": b["timestamp"],
                        "open": b["open"],
                        "high": b["high"],
                        "low": b["low"],
                        "close": b["close"],
                        "volume": b["volume"],
                        "createdBy": "TV_HISTORICAL_SEEDER",
                        "updatedBy": "TV_HISTORICAL_SEEDER",
                    }
                )
                inserted_count += 1
            else:
                # Update existing bar if prices changed (e.g. unclosed bar update)
                await db.marketcandle.update(
                    where={
                        "symbol_timeframe_timestamp": {
                            "symbol": b["symbol"],
                            "timeframe": b["timeframe"],
                            "timestamp": b["timestamp"],
                        }
                    },
                    data={
                        "open": b["open"],
                        "high": b["high"],
                        "low": b["low"],
                        "close": b["close"],
                        "volume": b["volume"],
                        "updatedBy": "TV_HISTORICAL_SEEDER",
                    },
                )
        except Exception as e:
            logger.debug(f"Candle save skipped or failed for {b['symbol']} at {b['timestamp']}: {e}")

    return inserted_count


async def seed_benchmark_historical_candles(
    symbols: Optional[List[Dict[str, str]]] = None,
    timeframes: List[str] = ["1m", "5m"],
    n_bars: int = 500,
) -> Dict[str, Any]:
    """
    Seeds historical candles for selected benchmark symbols across 1m and 5m intervals.
    """
    if not symbols:
        # Default key benchmarks across asset classes
        symbols = [
            {"symbol": "RELIANCE", "exchange": "NSE"},
            {"symbol": "INFY", "exchange": "NSE"},
            {"symbol": "AAPL", "exchange": "NASDAQ"},
            {"symbol": "BTCUSDT", "exchange": "BINANCE"},
            {"symbol": "EURUSD", "exchange": "FX_IDC"},
        ]

    total_inserted = 0
    results_by_symbol: Dict[str, Dict[str, int]] = {}

    for item in symbols:
        sym = item["symbol"]
        exch = item["exchange"]
        results_by_symbol[sym] = {}

        for tf in timeframes:
            bars = fetch_tradingview_bars(symbol=sym, exchange=exch, timeframe=tf, n_bars=n_bars)
            inserted = await save_candles_to_database(bars)
            results_by_symbol[sym][tf] = inserted
            total_inserted += inserted
            logger.info(f"Seeded {inserted}/{len(bars)} bars for {exch}:{sym} [{tf}]")

    return {
        "total_candles_processed": total_inserted,
        "details": results_by_symbol,
    }


async def query_market_candles(
    symbol: str,
    timeframe: str = "5m",
    limit: int = 180,
    before: Optional[datetime] = None,
    ascending: bool = True,
) -> List[Any]:
    """
    High-speed retrieval of OHLCV candles from PostgreSQL using the composite index.
    Returns chronologically ordered candles.
    """
    clean_sym = symbol.strip().upper()
    clean_tf = timeframe.strip().lower()

    where_clause: Dict[str, Any] = {
        "symbol": clean_sym,
        "timeframe": clean_tf,
    }
    if before:
        where_clause["timestamp"] = {"lt": before}

    # Fetch descending using the composite B-tree index
    candles = await db.marketcandle.find_many(
        where=where_clause,
        take=limit,
        order={"timestamp": "desc"},
    )

    if ascending:
        # Reverse to chronological order (oldest to newest)
        return list(reversed(candles))
    return candles
