"""
PDF-BASED PRICE ACTION BOT (VERSION 3 - TRADINGVIEW FEED)
Source: BO Price Action Book by Ishaq's Binary Academy

KEY CHARACTERISTICS:
1. Data Provider: TRADINGVIEW (tvDatafeed)
   - Real-time 1-minute candlestick data fetched directly from TradingView (FX_IDC exchange).
   - Supports 100% free usage (no-login method) or optional TradingView account credentials.
   - Eliminates Finnhub 403 Forbidden restrictions on Forex candles.
2. Verified Standardization:
   - Transforms TradingView's raw OHLCV DatetimeIndex DataFrame into the exact
     standardized format expected by the pure price-action rule engine:
     ['time', 'open', 'high', 'low', 'close'] (UTC, chronologically sorted).
3. 100% Pure Price Action Preserved:
   - Bullish/Bearish Engulfing, Piercing Line, Dark Cloud Cover.
   - Retracement verification and dynamic Support/Resistance rejection.
   - No laggy indicators (RSI, EMA, MACD).
4. Candle-Boundary Synchronization:
   - Automatically synchronizes scan loops to 2 seconds after the minute boundary (:02s).
5. Output Modularity:
   - Simple, direct commenting: comment or uncomment log_signal_to_file(message)
     or send_telegram(message) directly in the output block.
"""

import os
import sys
import time
import math
import json
import sqlite3
import webbrowser
import argparse
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
import requests
import pandas as pd
import logging

# Suppress repetitive websocket connection warnings from tvDatafeed library
logging.getLogger("tvDatafeed.main").setLevel(logging.CRITICAL)

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Load environment configuration
load_dotenv()


# ============================================================
# CONFIGURATION & SETTINGS
# ============================================================

# TradingView Credentials (Optional: leave empty for public no-login access)
TRADINGVIEW_USERNAME = os.getenv("TRADINGVIEW_USERNAME", "")
TRADINGVIEW_PASSWORD = os.getenv("TRADINGVIEW_PASSWORD", "")

# News Filter API Key (Finnhub is used for macro news safety filter)
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
FINNHUB_BASE_URL = "https://finnhub.io/api/v1"

# Telegram Notification Settings
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")

# Execution Schedule & Rate Limiting
CANDLE_SYNC = os.getenv("CANDLE_SYNC", "true").lower() == "true"
PAIR_REQUEST_DELAY = float(os.getenv("PAIR_REQUEST_DELAY", "0.8"))  # Delay in seconds between pairs
SCAN_INTERVAL_SECONDS = int(os.getenv("SCAN_INTERVAL_SECONDS", "60"))  # Fallback if CANDLE_SYNC is false
LOOKBACK_MINUTES = 180       # 3 hours of historical 1-minute bars
NEWS_LOOKBACK_MINUTES = 10   # High-impact news window
NEWS_CACHE_TTL = 60          # Cache news API responses for 60 seconds

# 19 Monitored Currency Pairs on TradingView (Exchange: FX_IDC)
PAIRS = {
    "EUR/JPY": {"symbol": "EURJPY", "exchange": "FX_IDC"},
    "CAD/JPY": {"symbol": "CADJPY", "exchange": "FX_IDC"},
    "EUR/USD": {"symbol": "EURUSD", "exchange": "FX_IDC"},
    "USD/JPY": {"symbol": "USDJPY", "exchange": "FX_IDC"},
    "AUD/JPY": {"symbol": "AUDJPY", "exchange": "FX_IDC"},
    "AUD/USD": {"symbol": "AUDUSD", "exchange": "FX_IDC"},
    "AUD/CAD": {"symbol": "AUDCAD", "exchange": "FX_IDC"},
    "GBP/USD": {"symbol": "GBPUSD", "exchange": "FX_IDC"},
    "GBP/AUD": {"symbol": "GBPAUD", "exchange": "FX_IDC"},
    "GBP/CAD": {"symbol": "GBPCAD", "exchange": "FX_IDC"},
    "GBP/CHF": {"symbol": "GBPCHF", "exchange": "FX_IDC"},
    "GBP/JPY": {"symbol": "GBPJPY", "exchange": "FX_IDC"},
    "USD/CAD": {"symbol": "USDCAD", "exchange": "FX_IDC"},
    "USD/CHF": {"symbol": "USDCHF", "exchange": "FX_IDC"},
    "EUR/GBP": {"symbol": "EURGBP", "exchange": "FX_IDC"},
    "CHF/JPY": {"symbol": "CHFJPY", "exchange": "FX_IDC"},
    "EUR/AUD": {"symbol": "EURAUD", "exchange": "FX_IDC"},
    "EUR/CAD": {"symbol": "EURCAD", "exchange": "FX_IDC"},
    "EUR/CHF": {"symbol": "EURCHF", "exchange": "FX_IDC"},
}

PAIR_CURRENCIES = {pair: set(pair.split("/")) for pair in PAIRS}

# Global runtime caches
NEWS_CACHE = {"timestamp": 0, "data": []}
SENT_KEYS_CACHE = {}  # key -> timestamp for deduplication auto-pruning

# ============================================================
# TRADINGVIEW MARKET DATA LAYER (RESILIENT FEED)
# ============================================================

def create_tv_instance():
    """
    Creates a new tvDatafeed instance with configured credentials.
    """
    from tvDatafeed import TvDatafeed
    if TRADINGVIEW_USERNAME and TRADINGVIEW_PASSWORD:
        return TvDatafeed(username=TRADINGVIEW_USERNAME, password=TRADINGVIEW_PASSWORD)
    return TvDatafeed()


def check_settings():
    """
    Validates environment settings and prerequisites.
    """
    try:
        tv = create_tv_instance()
        if hasattr(tv, "ws") and tv.ws:
            try:
                tv.ws.close()
            except Exception:
                pass
        print("🌐 TradingView Client verified successfully.")
    except Exception as e:
        raise RuntimeError(f"Could not initialize TradingView client: {e}")

    if not CHAT_ID or CHAT_ID == "dummy_chat_id":
        print("⚠️ [WARNING] CHAT_ID is empty or set to 'dummy_chat_id'. If Telegram alert is uncommented, it will be skipped.")


def fetch_tv_raw_with_retry(symbol, exchange, n_bars=180, max_retries=2):
    """
    Fetches raw candlestick data from TradingView with automatic retry and socket cleanup.
    
    Why this prevents 'Connection to remote host was lost':
      1. Sockets are explicitly closed immediately after each request, preventing
         socket exhaustion on TradingView's servers.
      2. If a momentary network or websocket reset occurs, it automatically retries
         with a clean session after a short backoff.
    """
    from tvDatafeed import Interval

    for attempt in range(max_retries + 1):
        tv = None
        try:
            tv = create_tv_instance()
            raw = tv.get_hist(
                symbol=symbol,
                exchange=exchange,
                interval=Interval.in_1_minute,
                n_bars=n_bars,
            )

            if raw is not None and not raw.empty and len(raw) >= 10:
                return raw

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

    return None


def get_candles(pair):
    """
    Fetches 1-minute historical candlestick data directly from TradingView.
    
    Standardization Pipeline:
      TradingView raw format:
        Index: pd.DatetimeIndex ('datetime')
        Columns: ['symbol', 'open', 'high', 'low', 'close', 'volume']
      
      Converted output format:
        Columns: ['time', 'open', 'high', 'low', 'close']
        time: UTC Timestamp
        sorted: Chronological ascending order (oldest at 0, newest at -1)
    """
    info = PAIRS[pair]
    symbol = info["symbol"]
    exchange = info["exchange"]

    try:
        raw = fetch_tv_raw_with_retry(
            symbol=symbol,
            exchange=exchange,
            n_bars=LOOKBACK_MINUTES,
        )

        if raw is None or raw.empty or len(raw) < 20:
            return None

        # Reset DatetimeIndex to convert 'datetime' into a standard column
        df = raw.reset_index().rename(columns={"datetime": "time"})

        # Guarantee UTC timezone
        df["time"] = pd.to_datetime(df["time"], utc=True)

        # Cast price columns to float
        for col in ["open", "high", "low", "close"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # Drop duplicates and sort chronologically
        df = df.dropna().drop_duplicates("time")
        df = df.sort_values("time").reset_index(drop=True)

        return df[["time", "open", "high", "low", "close"]]

    except Exception as e:
        print(f"{pair} [TradingView]: Candle fetch error: {e}")
        return None


# ============================================================
# CANDLE GEOMETRY & ANATOMY (NO INDICATORS)
# ============================================================

def candle_parts(row):
    """
    Calculates body, upper wick, and lower wick from candle OHLC.
    """
    o = float(row["open"])
    h = float(row["high"])
    l = float(row["low"])
    c = float(row["close"])

    body = abs(c - o)
    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l

    return {
        "open": o,
        "high": h,
        "low": l,
        "close": c,
        "body": body,
        "upper_wick": max(0.0, upper_wick),
        "lower_wick": max(0.0, lower_wick),
        "bullish": c > o,
        "bearish": c < o,
    }


def weak_bullish(row):
    p = candle_parts(row)
    if not p["bullish"]:
        return False
    return p["body"] <= max(p["upper_wick"], p["lower_wick"]) * 1.5


def weak_bearish(row):
    p = candle_parts(row)
    if not p["bearish"]:
        return False
    return p["body"] <= max(p["upper_wick"], p["lower_wick"]) * 1.5


def classify_candle(row):
    """
    Classifies candle anatomy according to the PDF Price Action rules:
    Calculates body, upper wick, lower wick, ratio, and assigns type:
    - Strong Bullish / Weak Bullish (Retracement)
    - Strong Bearish / Weak Bearish (Retracement)
    - Doji / Spinning Top / Neutral
    """
    p = candle_parts(row)
    body = p["body"]
    uw = p["upper_wick"]
    lw = p["lower_wick"]
    total_range = p["high"] - p["low"]
    max_wick = max(uw, lw)
    ratio = body / max(0.000001, max_wick)

    if total_range == 0:
        c_type = "Flat"
    elif body <= total_range * 0.10:
        c_type = "Doji"
    elif body <= total_range * 0.30 and uw > body and lw > body:
        c_type = "Spinning Top"
    elif p["bullish"]:
        if body <= max_wick * 1.5:
            c_type = "Weak Bullish (Retracement)"
        else:
            c_type = "Strong Bullish"
    elif p["bearish"]:
        if body <= max_wick * 1.5:
            c_type = "Weak Bearish (Retracement)"
        else:
            c_type = "Strong Bearish"
    else:
        c_type = "Neutral"

    return {
        "body": body,
        "upper_wick": uw,
        "lower_wick": lw,
        "ratio": ratio,
        "bullish": p["bullish"],
        "bearish": p["bearish"],
        "is_weak_bullish": weak_bullish(row),
        "is_weak_bearish": weak_bearish(row),
        "candle_type": c_type,
    }



# ============================================================
# TREND & SUPPORT / RESISTANCE DETECTION
# ============================================================

def prior_downtrend(df, end_index, bars=5):
    start = max(0, end_index - bars)
    x = df.iloc[start:end_index]
    if len(x) < 4:
        return False

    highs = x["high"].tolist()
    lows = x["low"].tolist()

    lower_highs = sum(highs[i] <= highs[i - 1] for i in range(1, len(highs)))
    lower_lows = sum(lows[i] <= lows[i - 1] for i in range(1, len(lows)))

    return lower_highs >= len(highs) - 2 and lower_lows >= len(lows) - 2


def prior_uptrend(df, end_index, bars=5):
    start = max(0, end_index - bars)
    x = df.iloc[start:end_index]
    if len(x) < 4:
        return False

    highs = x["high"].tolist()
    lows = x["low"].tolist()

    higher_highs = sum(highs[i] >= highs[i - 1] for i in range(1, len(highs)))
    higher_lows = sum(lows[i] >= lows[i - 1] for i in range(1, len(lows)))

    return higher_highs >= len(highs) - 2 and higher_lows >= len(lows) - 2


def key_levels(df, end_index, window=20):
    start = max(0, end_index - window)
    x = df.iloc[start:end_index]
    support = float(x["low"].min())
    resistance = float(x["high"].max())
    return support, resistance


def touches_level(row, level):
    return float(row["low"]) <= level <= float(row["high"])


def rejects_support(row, support):
    p = candle_parts(row)
    return touches_level(row, support) and p["close"] > support


def rejects_resistance(row, resistance):
    p = candle_parts(row)
    return touches_level(row, resistance) and p["close"] < resistance


# ============================================================
# CANDLESTICK PATTERN RECOGNITION
# ============================================================

def bullish_engulfing(df, i):
    if i < 1:
        return False
    a = candle_parts(df.iloc[i - 1])
    b = candle_parts(df.iloc[i])

    return (
        a["bearish"]
        and b["bullish"]
        and b["open"] <= a["close"]
        and b["close"] >= a["open"]
        and b["high"] >= a["high"]
        and b["low"] <= a["low"]
    )


def bearish_engulfing(df, i):
    if i < 1:
        return False
    a = candle_parts(df.iloc[i - 1])
    b = candle_parts(df.iloc[i])

    return (
        a["bullish"]
        and b["bearish"]
        and b["open"] >= a["close"]
        and b["close"] <= a["open"]
        and b["high"] >= a["high"]
        and b["low"] <= a["low"]
    )


def piercing_line(df, i):
    if i < 1:
        return False
    a = candle_parts(df.iloc[i - 1])
    b = candle_parts(df.iloc[i])
    midpoint = (a["open"] + a["close"]) / 2.0

    return (
        a["bearish"]
        and b["bullish"]
        and b["open"] < a["close"]
        and b["close"] > midpoint
        and b["close"] < a["open"]
    )


def dark_cloud_cover(df, i):
    if i < 1:
        return False
    a = candle_parts(df.iloc[i - 1])
    b = candle_parts(df.iloc[i])
    midpoint = (a["open"] + a["close"]) / 2.0

    return (
        a["bullish"]
        and b["bearish"]
        and b["open"] > a["high"]
        and b["close"] < midpoint
        and b["close"] > a["open"]
    )


# ============================================================
# STATE MACHINE: SETUP VERIFICATION WITH RETRACEMENT
# ============================================================

def find_recent_setup(df):
    """
    Evaluates completed candles for PDF trading setups:
    Pattern + Retracement candle + Key Level rejection.
    """
    n = len(df)

    for i in range(max(1, n - 8), n - 1):
        # 1. Bullish Engulfing
        if bullish_engulfing(df, i):
            support, _ = key_levels(df, i)
            retracement = df.iloc[i + 1]

            if weak_bearish(retracement) and rejects_support(retracement, support):
                return {
                    "direction": "CALL",
                    "pattern": "Bullish Engulfing",
                    "pattern_index": i,
                    "entry_index": i + 2,
                    "level": support,
                    "reason": "Retracement touched support, rejected and formed weak bearish candle.",
                }

            if float(retracement["close"]) < support:
                second = df.iloc[i + 2] if i + 2 < n else None
                if second is not None and rejects_support(second, support):
                    return {
                        "direction": "CALL",
                        "pattern": "Bullish Engulfing",
                        "pattern_index": i,
                        "entry_index": i + 3,
                        "level": support,
                        "reason": "Second retracement touched support and rejected.",
                    }

        # 2. Bearish Engulfing
        if bearish_engulfing(df, i):
            _, resistance = key_levels(df, i)
            retracement = df.iloc[i + 1]

            if weak_bullish(retracement) and rejects_resistance(retracement, resistance):
                return {
                    "direction": "PUT",
                    "pattern": "Bearish Engulfing",
                    "pattern_index": i,
                    "entry_index": i + 2,
                    "level": resistance,
                    "reason": "Retracement touched resistance, rejected and formed weak bullish candle.",
                }

            if float(retracement["close"]) > resistance:
                second = df.iloc[i + 2] if i + 2 < n else None
                if second is not None and rejects_resistance(second, resistance):
                    return {
                        "direction": "PUT",
                        "pattern": "Bearish Engulfing",
                        "pattern_index": i,
                        "entry_index": i + 3,
                        "level": resistance,
                        "reason": "Second retracement touched resistance and rejected.",
                    }

        # 3. Piercing Line
        if piercing_line(df, i) and prior_downtrend(df, i):
            a = candle_parts(df.iloc[i - 1])
            pattern_50 = (a["open"] + a["close"]) / 2.0
            support, _ = key_levels(df, i)
            retracement = df.iloc[i + 1]

            if float(retracement["close"]) > pattern_50:
                if rejects_support(retracement, support):
                    return {
                        "direction": "CALL",
                        "pattern": "Piercing Line",
                        "pattern_index": i,
                        "entry_index": i + 2,
                        "level": support,
                        "reason": "Retracement closed above 50% level and rejected support.",
                    }

                if float(retracement["close"]) < support:
                    second = df.iloc[i + 2] if i + 2 < n else None
                    if second is not None and rejects_support(second, support):
                        return {
                            "direction": "CALL",
                            "pattern": "Piercing Line",
                            "pattern_index": i,
                            "entry_index": i + 3,
                            "level": support,
                            "reason": "Second candle touched key level and rejected.",
                        }

        # 4. Dark Cloud Cover
        if dark_cloud_cover(df, i) and prior_uptrend(df, i):
            _, resistance = key_levels(df, i)
            retracement = df.iloc[i + 1]

            if rejects_resistance(retracement, resistance):
                return {
                    "direction": "PUT",
                    "pattern": "Dark Cloud Cover",
                    "pattern_index": i,
                    "entry_index": i + 2,
                    "level": resistance,
                    "reason": "Retracement touched resistance and rejected.",
                }

            if weak_bullish(retracement):
                return {
                    "direction": "PUT",
                    "pattern": "Dark Cloud Cover",
                    "pattern_index": i,
                    "entry_index": i + 2,
                    "level": resistance,
                    "reason": "No rejection; retracement closed as weak bullish candle.",
                }

    return None


def find_all_setups(df):
    """
    Scans the entire candlestick series for all PDF Price Action patterns,
    evaluating both 1st and 2nd retracement confirmation and S/R rejections.
    Returns a comprehensive list of all detected setups for visual verification and audit.
    """
    n = len(df)
    setups = []

    for i in range(20, n - 1):
        p_row = df.iloc[i]
        p_time = str(p_row["time"])
        p_ts = int(pd.to_datetime(p_row["time"]).timestamp())
        ret_row = df.iloc[i + 1]
        ret_time = str(ret_row["time"])
        ret_ts = int(pd.to_datetime(ret_row["time"]).timestamp())

        # 1. Bullish Engulfing
        if bullish_engulfing(df, i):
            support, _ = key_levels(df, i)

            if weak_bearish(ret_row) and rejects_support(ret_row, support):
                setups.append({
                    "direction": "CALL",
                    "pattern": "Bullish Engulfing",
                    "pattern_index": i,
                    "pattern_time": p_time,
                    "pattern_timestamp": p_ts,
                    "retracement_index": i + 1,
                    "retracement_time": ret_time,
                    "retracement_timestamp": ret_ts,
                    "entry_index": i + 2 if i + 2 < n else None,
                    "entry_time": str(df.iloc[i + 2]["time"]) if i + 2 < n else None,
                    "level": support,
                    "status": "CONFIRMED_SIGNAL",
                    "reason": "Retracement touched support, rejected and formed weak bearish candle.",
                })
            elif float(ret_row["close"]) < support:
                if i + 2 < n:
                    second = df.iloc[i + 2]
                    if rejects_support(second, support):
                        setups.append({
                            "direction": "CALL",
                            "pattern": "Bullish Engulfing",
                            "pattern_index": i,
                            "pattern_time": p_time,
                            "pattern_timestamp": p_ts,
                            "retracement_index": i + 2,
                            "retracement_time": str(second["time"]),
                            "retracement_timestamp": int(pd.to_datetime(second["time"]).timestamp()),
                            "entry_index": i + 3 if i + 3 < n else None,
                            "entry_time": str(df.iloc[i + 3]["time"]) if i + 3 < n else None,
                            "level": support,
                            "status": "CONFIRMED_SIGNAL",
                            "reason": "Second retracement touched support and rejected.",
                        })
                    else:
                        setups.append({
                            "direction": "CALL",
                            "pattern": "Bullish Engulfing",
                            "pattern_index": i,
                            "pattern_time": p_time,
                            "pattern_timestamp": p_ts,
                            "retracement_index": i + 1,
                            "retracement_time": ret_time,
                            "retracement_timestamp": ret_ts,
                            "entry_index": None,
                            "entry_time": None,
                            "level": support,
                            "status": "LEVEL_BROKEN",
                            "reason": "Support broken on retracement without rejection.",
                        })
                else:
                    setups.append({
                        "direction": "CALL",
                        "pattern": "Bullish Engulfing",
                        "pattern_index": i,
                        "pattern_time": p_time,
                        "pattern_timestamp": p_ts,
                        "retracement_index": i + 1,
                        "retracement_time": ret_time,
                        "retracement_timestamp": ret_ts,
                        "entry_index": None,
                        "entry_time": None,
                        "level": support,
                        "status": "INCOMPLETE",
                        "reason": "Retracement broke support; awaiting second candle confirmation.",
                    })
            else:
                setups.append({
                    "direction": "CALL",
                    "pattern": "Bullish Engulfing",
                    "pattern_index": i,
                    "pattern_time": p_time,
                    "pattern_timestamp": p_ts,
                    "retracement_index": i + 1,
                    "retracement_time": ret_time,
                    "retracement_timestamp": ret_ts,
                    "entry_index": None,
                    "entry_time": None,
                    "level": support,
                    "status": "PATTERN_ONLY",
                    "reason": "Engulfing formed, but retracement candle did not meet weak bearish + support rejection.",
                })

        # 2. Bearish Engulfing
        if bearish_engulfing(df, i):
            _, resistance = key_levels(df, i)

            if weak_bullish(ret_row) and rejects_resistance(ret_row, resistance):
                setups.append({
                    "direction": "PUT",
                    "pattern": "Bearish Engulfing",
                    "pattern_index": i,
                    "pattern_time": p_time,
                    "pattern_timestamp": p_ts,
                    "retracement_index": i + 1,
                    "retracement_time": ret_time,
                    "retracement_timestamp": ret_ts,
                    "entry_index": i + 2 if i + 2 < n else None,
                    "entry_time": str(df.iloc[i + 2]["time"]) if i + 2 < n else None,
                    "level": resistance,
                    "status": "CONFIRMED_SIGNAL",
                    "reason": "Retracement touched resistance, rejected and formed weak bullish candle.",
                })
            elif float(ret_row["close"]) > resistance:
                if i + 2 < n:
                    second = df.iloc[i + 2]
                    if rejects_resistance(second, resistance):
                        setups.append({
                            "direction": "PUT",
                            "pattern": "Bearish Engulfing",
                            "pattern_index": i,
                            "pattern_time": p_time,
                            "pattern_timestamp": p_ts,
                            "retracement_index": i + 2,
                            "retracement_time": str(second["time"]),
                            "retracement_timestamp": int(pd.to_datetime(second["time"]).timestamp()),
                            "entry_index": i + 3 if i + 3 < n else None,
                            "entry_time": str(df.iloc[i + 3]["time"]) if i + 3 < n else None,
                            "level": resistance,
                            "status": "CONFIRMED_SIGNAL",
                            "reason": "Second retracement touched resistance and rejected.",
                        })
                    else:
                        setups.append({
                            "direction": "PUT",
                            "pattern": "Bearish Engulfing",
                            "pattern_index": i,
                            "pattern_time": p_time,
                            "pattern_timestamp": p_ts,
                            "retracement_index": i + 1,
                            "retracement_time": ret_time,
                            "retracement_timestamp": ret_ts,
                            "entry_index": None,
                            "entry_time": None,
                            "level": resistance,
                            "status": "LEVEL_BROKEN",
                            "reason": "Resistance broken on retracement without rejection.",
                        })
                else:
                    setups.append({
                        "direction": "PUT",
                        "pattern": "Bearish Engulfing",
                        "pattern_index": i,
                        "pattern_time": p_time,
                        "pattern_timestamp": p_ts,
                        "retracement_index": i + 1,
                        "retracement_time": ret_time,
                        "retracement_timestamp": ret_ts,
                        "entry_index": None,
                        "entry_time": None,
                        "level": resistance,
                        "status": "INCOMPLETE",
                        "reason": "Retracement broke resistance; awaiting second candle confirmation.",
                    })
            else:
                setups.append({
                    "direction": "PUT",
                    "pattern": "Bearish Engulfing",
                    "pattern_index": i,
                    "pattern_time": p_time,
                    "pattern_timestamp": p_ts,
                    "retracement_index": i + 1,
                    "retracement_time": ret_time,
                    "retracement_timestamp": ret_ts,
                    "entry_index": None,
                    "entry_time": None,
                    "level": resistance,
                    "status": "PATTERN_ONLY",
                    "reason": "Engulfing formed, but retracement candle did not meet weak bullish + resistance rejection.",
                })

        # 3. Piercing Line
        if piercing_line(df, i) and prior_downtrend(df, i):
            a = candle_parts(df.iloc[i - 1])
            pattern_50 = (a["open"] + a["close"]) / 2.0
            support, _ = key_levels(df, i)

            if float(ret_row["close"]) > pattern_50:
                if rejects_support(ret_row, support):
                    setups.append({
                        "direction": "CALL",
                        "pattern": "Piercing Line",
                        "pattern_index": i,
                        "pattern_time": p_time,
                        "pattern_timestamp": p_ts,
                        "retracement_index": i + 1,
                        "retracement_time": ret_time,
                        "retracement_timestamp": ret_ts,
                        "entry_index": i + 2 if i + 2 < n else None,
                        "entry_time": str(df.iloc[i + 2]["time"]) if i + 2 < n else None,
                        "level": support,
                        "status": "CONFIRMED_SIGNAL",
                        "reason": "Retracement closed above 50% level and rejected support.",
                    })
                elif float(ret_row["close"]) < support:
                    if i + 2 < n and rejects_support(df.iloc[i + 2], support):
                        second = df.iloc[i + 2]
                        setups.append({
                            "direction": "CALL",
                            "pattern": "Piercing Line",
                            "pattern_index": i,
                            "pattern_time": p_time,
                            "pattern_timestamp": p_ts,
                            "retracement_index": i + 2,
                            "retracement_time": str(second["time"]),
                            "retracement_timestamp": int(pd.to_datetime(second["time"]).timestamp()),
                            "entry_index": i + 3 if i + 3 < n else None,
                            "entry_time": str(df.iloc[i + 3]["time"]) if i + 3 < n else None,
                            "level": support,
                            "status": "CONFIRMED_SIGNAL",
                            "reason": "Second candle touched key level and rejected.",
                        })

        # 4. Dark Cloud Cover
        if dark_cloud_cover(df, i) and prior_uptrend(df, i):
            _, resistance = key_levels(df, i)

            if rejects_resistance(ret_row, resistance):
                setups.append({
                    "direction": "PUT",
                    "pattern": "Dark Cloud Cover",
                    "pattern_index": i,
                    "pattern_time": p_time,
                    "pattern_timestamp": p_ts,
                    "retracement_index": i + 1,
                    "retracement_time": ret_time,
                    "retracement_timestamp": ret_ts,
                    "entry_index": i + 2 if i + 2 < n else None,
                    "entry_time": str(df.iloc[i + 2]["time"]) if i + 2 < n else None,
                    "level": resistance,
                    "status": "CONFIRMED_SIGNAL",
                    "reason": "Retracement touched resistance and rejected.",
                })
            elif weak_bullish(ret_row):
                setups.append({
                    "direction": "PUT",
                    "pattern": "Dark Cloud Cover",
                    "pattern_index": i,
                    "pattern_time": p_time,
                    "pattern_timestamp": p_ts,
                    "retracement_index": i + 1,
                    "retracement_time": ret_time,
                    "retracement_timestamp": ret_ts,
                    "entry_index": i + 2 if i + 2 < n else None,
                    "entry_time": str(df.iloc[i + 2]["time"]) if i + 2 < n else None,
                    "level": resistance,
                    "status": "CONFIRMED_SIGNAL",
                    "reason": "No rejection; retracement closed as weak bullish candle.",
                })

    return setups



# ============================================================
# NEWS SAFETY CIRCUIT BREAKER (WITH 60-SECOND CACHE)
# ============================================================

def get_forex_news():
    if not FINNHUB_API_KEY:
        return []

    now = time.time()
    if now - NEWS_CACHE["timestamp"] < NEWS_CACHE_TTL and NEWS_CACHE["data"]:
        return NEWS_CACHE["data"]

    try:
        response = requests.get(
            f"{FINNHUB_BASE_URL}/news",
            params={"category": "forex", "token": FINNHUB_API_KEY},
            timeout=10,
        )
        if response.status_code == 200:
            data = response.json()
            NEWS_CACHE["timestamp"] = now
            NEWS_CACHE["data"] = data
            return data
    except Exception as e:
        print("News fetch error:", e)
    return NEWS_CACHE.get("data", [])


def relevant_news_for_pair(pair):
    currencies = PAIR_CURRENCIES[pair]
    now = datetime.now(timezone.utc)
    news = get_forex_news()

    high_impact_words = {
        "rate", "interest", "central bank", "fed", "ecb", "boj", "boe", "rba", "boc",
        "cpi", "inflation", "employment", "payroll", "jobs", "gdp", "pmi", "retail sales",
        "unemployment", "fomc", "policy", "decision", "speech", "war", "tariff", "sanction"
    }

    for item in news[:100]:
        headline = str(item.get("headline", "")).lower()
        summary = str(item.get("summary", "")).lower()
        text = headline + " " + summary

        ts = item.get("datetime")
        if not ts:
            continue

        try:
            published = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        except Exception:
            continue

        age_minutes = (now - published).total_seconds() / 60.0
        if 0 <= age_minutes <= NEWS_LOOKBACK_MINUTES:
            if any(word in text for word in high_impact_words):
                if any(currency.lower() in text for currency in currencies):
                    return True, item

    return False, None


# ============================================================
# OUTPUT HANDLERS (TELEGRAM & FILE LOGGING)
# ============================================================

def send_telegram(message, document_path=None):
    """
    Dispatches trade alert to Telegram chat/channel.
    Optionally uploads and attaches an interactive HTML chart document.
    """
    if not TELEGRAM_BOT_TOKEN or not CHAT_ID or CHAT_ID == "dummy_chat_id":
        print("[TELEGRAM SKIPPED] TELEGRAM_BOT_TOKEN or CHAT_ID not configured.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        response = requests.post(
            url,
            data={"chat_id": CHAT_ID, "text": message},
            timeout=15,
        )
        response.raise_for_status()
        print("📨 [TELEGRAM] Signal text alert dispatched.")
    except Exception as e:
        print(f"⚠️ [TELEGRAM ERROR] Failed to send text alert: {e}")
        return False

    if document_path:
        return send_telegram_document(document_path, caption="📊 Interactive Verification Chart")
    return True


def send_telegram_document(file_path, caption=None):
    """
    Uploads and sends a document (e.g. interactive HTML chart file) to Telegram chat/channel.
    Uses Telegram's HTTP Bot API /sendDocument endpoint with multipart/form-data.
    """
    if not TELEGRAM_BOT_TOKEN or not CHAT_ID or CHAT_ID == "dummy_chat_id":
        print("[TELEGRAM SKIPPED] TELEGRAM_BOT_TOKEN or CHAT_ID not configured.")
        return False

    if not file_path or not os.path.exists(file_path):
        print(f"⚠️ [TELEGRAM ERROR] Chart file does not exist: {file_path}")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    file_name = os.path.basename(file_path)

    try:
        with open(file_path, "rb") as f:
            files = {
                "document": (file_name, f, "text/html")
            }
            data = {"chat_id": CHAT_ID}
            if caption:
                # Telegram caption maximum length is 1024 characters
                data["caption"] = str(caption)[:1024]

            print(f"📤 [TELEGRAM] Uploading chart document '{file_name}' to Telegram...")
            response = requests.post(url, data=data, files=files, timeout=30)
            response.raise_for_status()
            print(f"✅ [TELEGRAM] HTML chart file successfully delivered to Telegram!")
            return True
    except Exception as e:
        print(f"⚠️ [TELEGRAM ERROR] Failed to send chart document to Telegram: {e}")
        return False



LOG_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "signals_history.log")
TV_DATA_LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tv_market_data.log")


def log_signal_to_file(content, filename=None):
    """
    Independently appends whatever text or signal is given to it into a file,
    preserving all emojis and prepending the generation timestamp and 1-minute timeframe.
    Always saves to signals_history.log inside the bot's directory regardless of
    where the command was run from.
    """
    if filename is None:
        filename = LOG_FILE_PATH

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    now_local = datetime.now().strftime("%H:%M:%S Local")
    entry = (
        "================================================================================\n"
        f"🕒 LOG TIMESTAMP: {now_utc} ({now_local}) | TIMEFRAME: 1-Minute\n"
        "--------------------------------------------------------------------------------\n"
        f"{content}\n"
        "================================================================================\n\n"
    )
    with open(filename, "a", encoding="utf-8") as f:
        f.write(entry)
    print(f"💾 [LOGGED TO FILE] Signal output appended to {filename}")


def log_tv_data_to_file(pair_or_content, df=None, filename=None):
    """
    Independently appends TradingView market data to a dedicated log file (tv_market_data.log),
    preserving all emojis and recording timestamps, pair names, and OHLC data.
    Can be called with log_tv_data_to_file(pair, df) or with raw string text.
    """
    if filename is None:
        filename = TV_DATA_LOG_PATH

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    now_local = datetime.now().strftime("%H:%M:%S Local")

    if df is not None and isinstance(df, pd.DataFrame) and not df.empty:
        pair = str(pair_or_content)
        last_closed = df.iloc[-2] if len(df) >= 2 else df.iloc[-1]
        forming = df.iloc[-1]

        # Format recent 3 closed bars
        recent_bars = []
        recent_slice = df.iloc[-4:-1] if len(df) >= 4 else df.iloc[:-1]
        for _, row in recent_slice.iterrows():
            t_str = str(row["time"])
            recent_bars.append(
                f"   • {t_str} | O: {row['open']:.5f} | H: {row['high']:.5f} | L: {row['low']:.5f} | C: {row['close']:.5f}"
            )
        recent_text = "\n".join(recent_bars) if recent_bars else "   (No prior bars)"

        content = (
            f"💱 PAIR: {pair} | 📡 SOURCE: TRADINGVIEW (FX_IDC)\n"
            f"📊 TOTAL BARS: {len(df)}\n\n"
            f"🕯 LATEST CLOSED BAR:\n"
            f"   Time:  {last_closed['time']}\n"
            f"   Open:  {last_closed['open']:.5f}\n"
            f"   High:  {last_closed['high']:.5f}\n"
            f"   Low:   {last_closed['low']:.5f}\n"
            f"   Close: {last_closed['close']:.5f}\n\n"
            f"⏳ IN-PROGRESS (FORMING) BAR:\n"
            f"   Time:  {forming['time']}\n"
            f"   Open:  {forming['open']:.5f} | Current: {forming['close']:.5f}\n\n"
            f"📋 RECENT CLOSED BARS:\n"
            f"{recent_text}"
        )
    else:
        content = str(pair_or_content)

    entry = (
        "================================================================================\n"
        f"🕒 LOG TIMESTAMP: {now_utc} ({now_local}) | TIMEFRAME: 1-Minute\n"
        "--------------------------------------------------------------------------------\n"
        f"{content}\n"
        "================================================================================\n\n"
    )

    with open(filename, "a", encoding="utf-8") as f:
        f.write(entry)
    print(f"📥 [TV DATA LOGGED] Market data appended to {filename}")


# ============================================================
# PERSISTENT MARKET DATA & IDEMPOTENT ANALYSIS CACHE (SQLITE)
# ============================================================

CACHE_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "market_cache.db")
CHARTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts")


def init_market_cache_db():
    """
    Initializes local SQLite database for historical market data and pre-computed pattern analysis.
    Guarantees that past candles are stored once and never re-evaluated.
    """
    os.makedirs(os.path.dirname(CACHE_DB_PATH), exist_ok=True)
    os.makedirs(CHARTS_DIR, exist_ok=True)
    with sqlite3.connect(CACHE_DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS candles (
                pair TEXT NOT NULL,
                time TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                PRIMARY KEY (pair, time)
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS candle_analysis (
                pair TEXT NOT NULL,
                time TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                body REAL NOT NULL,
                upper_wick REAL NOT NULL,
                lower_wick REAL NOT NULL,
                is_bullish INTEGER NOT NULL,
                is_bearish INTEGER NOT NULL,
                is_weak_bullish INTEGER NOT NULL,
                is_weak_bearish INTEGER NOT NULL,
                candle_type TEXT NOT NULL,
                support_20 REAL NOT NULL,
                resistance_20 REAL NOT NULL,
                PRIMARY KEY (pair, time)
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS detected_setups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pair TEXT NOT NULL,
                pattern_time TEXT NOT NULL,
                pattern_timestamp INTEGER NOT NULL,
                pattern_name TEXT NOT NULL,
                direction TEXT NOT NULL,
                key_level REAL NOT NULL,
                retracement_time TEXT,
                entry_time TEXT,
                status TEXT NOT NULL,
                reason TEXT NOT NULL,
                is_signal INTEGER NOT NULL,
                UNIQUE(pair, pattern_time, pattern_name)
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_candles_pt ON candles(pair, timestamp);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_analysis_pt ON candle_analysis(pair, timestamp);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_setups_pt ON detected_setups(pair, pattern_timestamp);")


def update_market_cache_and_analyze(pair, df):
    """
    Component: Historical Persistence & Idempotent Analysis Cache.
    
    1. Saves newly fetched candles to SQLite database.
    2. Identifies unanalyzed candles and computes anatomy, candle type, and rolling 20-bar S/R.
    3. Past analyzed data is NEVER re-evaluated.
    4. Evaluates setups and persists confirmed and pattern records.
    5. Returns (df, all_cached_setups).
    """
    if df is None or df.empty:
        return df, []

    init_market_cache_db()

    # 1. Identify already analyzed timestamps
    with sqlite3.connect(CACHE_DB_PATH) as conn:
        existing_analyzed = set(
            r[0] for r in conn.execute(
                "SELECT time FROM candle_analysis WHERE pair = ?", (pair,)
            ).fetchall()
        )

    # 2. Insert raw candles
    candle_records = []
    for _, row in df.iterrows():
        t_str = str(row["time"])
        ts = int(pd.to_datetime(row["time"]).timestamp())
        candle_records.append((
            pair, t_str, ts,
            float(row["open"]), float(row["high"]), float(row["low"]), float(row["close"])
        ))

    with sqlite3.connect(CACHE_DB_PATH) as conn:
        conn.executemany("""
            INSERT OR IGNORE INTO candles (pair, time, timestamp, open, high, low, close)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, candle_records)

    # 3. Analyze unanalyzed candles only
    new_analysis_records = []
    n = len(df)
    for i in range(n):
        row = df.iloc[i]
        t_str = str(row["time"])
        if t_str in existing_analyzed:
            continue  # Past data already evaluated; skip re-computation

        ts = int(pd.to_datetime(row["time"]).timestamp())
        clf = classify_candle(row)
        supp, res = key_levels(df, i) if i >= 20 else (float(row["low"]), float(row["high"]))

        new_analysis_records.append((
            pair, t_str, ts,
            clf["body"], clf["upper_wick"], clf["lower_wick"],
            1 if clf["bullish"] else 0,
            1 if clf["bearish"] else 0,
            1 if clf["is_weak_bullish"] else 0,
            1 if clf["is_weak_bearish"] else 0,
            clf["candle_type"],
            supp, res
        ))

    if new_analysis_records:
        with sqlite3.connect(CACHE_DB_PATH) as conn:
            conn.executemany("""
                INSERT OR REPLACE INTO candle_analysis
                (pair, time, timestamp, body, upper_wick, lower_wick, is_bullish, is_bearish,
                 is_weak_bullish, is_weak_bearish, candle_type, support_20, resistance_20)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, new_analysis_records)

    # 4. Detect and persist setups
    all_setups = find_all_setups(df)
    setup_records = []
    for s in all_setups:
        p_ts = int(s["pattern_timestamp"]) if "pattern_timestamp" in s else int(pd.to_datetime(s["pattern_time"]).timestamp())
        is_sig = 1 if s["status"] == "CONFIRMED_SIGNAL" else 0
        setup_records.append((
            pair, s["pattern_time"], p_ts, s["pattern"], s["direction"],
            float(s["level"]), s["retracement_time"], s["entry_time"],
            s["status"], s["reason"], is_sig
        ))

    if setup_records:
        with sqlite3.connect(CACHE_DB_PATH) as conn:
            conn.executemany("""
                INSERT OR IGNORE INTO detected_setups
                (pair, pattern_time, pattern_timestamp, pattern_name, direction, key_level,
                 retracement_time, entry_time, status, reason, is_signal)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, setup_records)

    # Retrieve all cached setups for this pair
    with sqlite3.connect(CACHE_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cached_setups = []
        for r in cur.execute(
            "SELECT * FROM detected_setups WHERE pair = ? ORDER BY pattern_timestamp ASC", (pair,)
        ).fetchall():
            d = dict(r)
            d["pattern"] = d.get("pattern_name", "")
            d["level"] = float(d.get("key_level", 0.0))
            cached_setups.append(d)

    return df, cached_setups


def get_cached_candles_and_analysis(pair, limit=300):
    """
    Loads historical candles and pre-computed analysis directly from SQLite cache.
    Zero network calls and zero re-evaluation required.
    """
    init_market_cache_db()
    with sqlite3.connect(CACHE_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        candle_rows = cur.execute(
            "SELECT time, open, high, low, close FROM candles WHERE pair = ? ORDER BY timestamp ASC LIMIT ?",
            (pair, limit)
        ).fetchall()

        setup_rows = cur.execute(
            "SELECT * FROM detected_setups WHERE pair = ? ORDER BY pattern_timestamp ASC",
            (pair,)
        ).fetchall()

    if not candle_rows:
        return None, []

    df = pd.DataFrame([dict(r) for r in candle_rows])
    df["time"] = pd.to_datetime(df["time"], utc=True)
    setups = []
    for r in setup_rows:
        d = dict(r)
        d["pattern"] = d.get("pattern_name", "")
        d["level"] = float(d.get("key_level", 0.0))
        setups.append(d)
    return df, setups


# ============================================================
# TRADINGVIEW CHART RECREATOR & VERIFICATION ENGINE
# ============================================================

def build_chart_html(pair, df, setups, highlight_setup=None):
    """
    Generates a standalone, dark-themed HTML report powered by TradingView Lightweight Charts (v4.2.1).
    Visualizes exact candlestick data, pattern markers, retracement points, S/R levels,
    live cursor inspection, and full pattern audit table.
    """
    n = len(df)
    is_jpy = "JPY" in pair
    precision = 3 if is_jpy else 5
    min_move = 0.001 if is_jpy else 0.00001

    candle_data = []
    analysis_map = {}
    support_series = []
    resistance_series = []

    for i in range(n):
        row = df.iloc[i]
        t = int(pd.to_datetime(row["time"]).timestamp())
        p = candle_parts(row)
        supp, res = key_levels(df, i) if i >= 20 else (float(row["low"]), float(row["high"]))
        wb = weak_bullish(row)
        wbear = weak_bearish(row)

        c_type = "Normal"
        if p["bullish"]:
            c_type = "Weak Bullish (Retracement)" if wb else "Strong Bullish"
        elif p["bearish"]:
            c_type = "Weak Bearish (Retracement)" if wbear else "Strong Bearish"

        max_wick = max(p["upper_wick"], p["lower_wick"])
        ratio = p["body"] / max(0.000001, max_wick)

        candle_data.append({
            "time": t,
            "open": round(float(row["open"]), precision),
            "high": round(float(row["high"]), precision),
            "low": round(float(row["low"]), precision),
            "close": round(float(row["close"]), precision),
        })

        analysis_map[t] = {
            "time_str": str(row["time"]),
            "open": f"{float(row['open']):.{precision}f}",
            "high": f"{float(row['high']):.{precision}f}",
            "low": f"{float(row['low']):.{precision}f}",
            "close": f"{float(row['close']):.{precision}f}",
            "body": f"{p['body']:.{precision}f}",
            "upper_wick": f"{p['upper_wick']:.{precision}f}",
            "lower_wick": f"{p['lower_wick']:.{precision}f}",
            "ratio": f"{ratio:.2f}",
            "type": c_type,
            "bullish": p["bullish"],
            "support": f"{supp:.{precision}f}",
            "resistance": f"{res:.{precision}f}",
        }

        support_series.append({"time": t, "value": round(supp, precision)})
        resistance_series.append({"time": t, "value": round(res, precision)})

    # Build markers for all setups
    markers = []
    for s in setups:
        p_t = int(s["pattern_timestamp"]) if "pattern_timestamp" in s else int(pd.to_datetime(s["pattern_time"]).timestamp())
        is_signal = s.get("status") == "CONFIRMED_SIGNAL"
        p_name = s.get("pattern") or s.get("pattern_name", "Pattern")

        # Pattern candle marker
        if p_name in ["Bullish Engulfing", "Piercing Line"]:
            markers.append({
                "time": p_t,
                "position": "belowBar",
                "color": "#10b981" if is_signal else "#059669",
                "shape": "arrowUp",
                "text": f"🟢 {p_name}" + (" (SIGNAL)" if is_signal else "")
            })
        else:
            markers.append({
                "time": p_t,
                "position": "aboveBar",
                "color": "#ef4444" if is_signal else "#dc2626",
                "shape": "arrowDown",
                "text": f"🔴 {p_name}" + (" (SIGNAL)" if is_signal else "")
            })

        # Retracement rejection marker
        if is_signal and s.get("retracement_time"):
            ret_t = int(pd.to_datetime(s["retracement_time"]).timestamp())
            markers.append({
                "time": ret_t,
                "position": "belowBar" if s["direction"] == "CALL" else "aboveBar",
                "color": "#f59e0b",
                "shape": "circle",
                "text": "🟡 Retracement Rejection"
            })

        # Entry marker
        if is_signal and s.get("entry_time"):
            entry_t = int(pd.to_datetime(s["entry_time"]).timestamp())
            markers.append({
                "time": entry_t,
                "position": "belowBar" if s["direction"] == "CALL" else "aboveBar",
                "color": "#3b82f6",
                "shape": "square",
                "text": f"🎯 {s['direction']} ENTRY"
            })

    markers.sort(key=lambda m: m["time"])

    highlight_json = "null"
    if highlight_setup:
        h_name = highlight_setup.get("pattern") or highlight_setup.get("pattern_name", "Pattern")
        highlight_json = json.dumps({
            "level": float(highlight_setup["level"]),
            "direction": highlight_setup["direction"],
            "pattern": h_name,
            "time": int(pd.to_datetime(highlight_setup["candle_time"]).timestamp()) if "candle_time" in highlight_setup else None
        })

    confirmed_count = sum(1 for s in setups if s.get("status") == "CONFIRMED_SIGNAL")
    latest_close = f"{float(candle_data[-1]['close']):.{precision}f}" if candle_data else "-"

    table_rows = []
    for idx, s in enumerate(setups, 1):
        status = s.get("status", "PATTERN_ONLY")
        p_name = s.get("pattern") or s.get("pattern_name", "Pattern")
        badge_cls = "badge-confirmed" if status == "CONFIRMED_SIGNAL" else "badge-pattern"
        dir_cls = "badge-call" if s["direction"] == "CALL" else "badge-put"
        p_ts = int(s["pattern_timestamp"]) if "pattern_timestamp" in s else int(pd.to_datetime(s["pattern_time"]).timestamp())
        table_rows.append(f"""
                <tr>
                    <td>{idx}</td>
                    <td>{s['pattern_time']}</td>
                    <td><b>{p_name}</b></td>
                    <td><span class="badge {dir_cls}">{s['direction']}</span></td>
                    <td>{float(s['level']):.{precision}f}</td>
                    <td><span class="badge {badge_cls}">{status}</span></td>
                    <td style="color: var(--text-muted);">{s['reason']}</td>
                    <td><button onclick="zoomToTimestamp({p_ts})">🔍 Zoom</button></td>
                </tr>
        """)

    table_body = "".join(table_rows) if table_rows else """
                <tr>
                    <td colspan="8" style="text-align: center; color: var(--text-muted); padding: 20px;">
                        No price action patterns detected in the fetched historical window.
                    </td>
                </tr>
    """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TradingView Recreated Chart - {pair} (Bot V3)</title>
    <script src="https://unpkg.com/lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        :root {{
            --bg-primary: #131722;
            --bg-secondary: #1e222d;
            --bg-card: #2a2e39;
            --text-primary: #d1d4dc;
            --text-muted: #787b86;
            --border-color: #363a45;
            --bullish: #26a69a;
            --bearish: #ef5350;
            --accent: #2962ff;
            --warning: #f59e0b;
        }}
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
        }}
        body {{
            background-color: var(--bg-primary);
            color: var(--text-primary);
            padding: 16px;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--bg-secondary);
            padding: 14px 20px;
            border-radius: 8px;
            border: 1px solid var(--border-color);
            margin-bottom: 12px;
            flex-wrap: wrap;
            gap: 12px;
        }}
        .title-group {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .pair-badge {{
            font-size: 20px;
            font-weight: 700;
            color: #fff;
        }}
        .tag {{
            background: rgba(41, 98, 255, 0.15);
            color: #2962ff;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
            border: 1px solid rgba(41, 98, 255, 0.3);
        }}
        .stats-group {{
            display: flex;
            gap: 16px;
        }}
        .stat-item {{
            display: flex;
            flex-direction: column;
            align-items: flex-end;
        }}
        .stat-label {{
            font-size: 11px;
            color: var(--text-muted);
            text-transform: uppercase;
        }}
        .stat-value {{
            font-size: 14px;
            font-weight: 600;
        }}
        .toolbar {{
            display: flex;
            gap: 8px;
            margin-bottom: 12px;
            flex-wrap: wrap;
        }}
        button {{
            background: var(--bg-secondary);
            color: var(--text-primary);
            border: 1px solid var(--border-color);
            padding: 6px 14px;
            border-radius: 6px;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.2s;
        }}
        button:hover {{
            background: var(--bg-card);
            border-color: #505664;
        }}
        button.active {{
            background: var(--accent);
            color: #fff;
            border-color: var(--accent);
        }}
        #chart-container {{
            width: 100%;
            height: 520px;
            background: var(--bg-secondary);
            border-radius: 8px;
            border: 1px solid var(--border-color);
            position: relative;
        }}
        .chart-legend {{
            position: absolute;
            top: 12px;
            left: 14px;
            z-index: 10;
            pointer-events: none;
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 12px;
            background: rgba(19, 23, 34, 0.88);
            padding: 8px 14px;
            border-radius: 6px;
            border: 1px solid rgba(255, 255, 255, 0.12);
            font-size: 13px;
            backdrop-filter: blur(6px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        }}
        .legend-pair {{
            font-weight: 700;
            color: #fff;
            margin-right: 4px;
        }}
        .legend-ohlc, .legend-extra {{
            display: flex;
            gap: 10px;
        }}
        .legend-ohlc span, .legend-extra span {{
            color: var(--text-muted);
        }}
        .leg-val {{
            font-weight: 600;
            color: var(--text-primary);
        }}
        .leg-val.bullish, .val.bullish {{ color: var(--bullish) !important; }}
        .leg-val.bearish, .val.bearish {{ color: var(--bearish) !important; }}
        .inspector-panel {{
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 12px 18px;
            margin-top: 12px;
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            font-size: 13px;
        }}
        .inspector-item {{
            display: flex;
            flex-direction: column;
            gap: 2px;
        }}
        .inspector-item .lbl {{
            font-size: 11px;
            color: var(--text-muted);
            text-transform: uppercase;
        }}
        .inspector-item .val {{
            font-weight: 600;
        }}
        .section-title {{
            font-size: 16px;
            font-weight: 600;
            margin: 20px 0 10px 0;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .table-container {{
            background: var(--bg-secondary);
            border-radius: 8px;
            border: 1px solid var(--border-color);
            overflow-x: auto;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            text-align: left;
        }}
        th {{
            background: var(--bg-card);
            color: var(--text-muted);
            padding: 10px 14px;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 11px;
            border-bottom: 1px solid var(--border-color);
        }}
        td {{
            padding: 10px 14px;
            border-bottom: 1px solid var(--border-color);
        }}
        tr:hover td {{
            background: rgba(255, 255, 255, 0.02);
        }}
        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
        }}
        .badge-call {{ background: rgba(38, 166, 154, 0.2); color: var(--bullish); }}
        .badge-put {{ background: rgba(239, 83, 80, 0.2); color: var(--bearish); }}
        .badge-confirmed {{ background: rgba(16, 185, 129, 0.2); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.4); }}
        .badge-pattern {{ background: rgba(245, 158, 11, 0.2); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.4); }}
    </style>
</head>
<body>
    <div class="header">
        <div class="title-group">
            <span class="pair-badge">{pair}</span>
            <span class="tag">1-Minute</span>
            <span class="tag">TradingView Feed (FX_IDC)</span>
            <span class="tag">PDF Price Action V3</span>
        </div>
        <div class="stats-group">
            <div class="stat-item">
                <span class="stat-label">Total Bars</span>
                <span class="stat-value">{len(candle_data)}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Patterns Found</span>
                <span class="stat-value">{len(setups)}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Confirmed Signals</span>
                <span class="stat-value" style="color: #10b981;">{confirmed_count}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Latest Close</span>
                <span class="stat-value">{latest_close}</span>
            </div>
        </div>
    </div>

    <div class="toolbar">
        <button onclick="chart.timeScale().fitContent()">🔄 Fit All Candles</button>
        <button onclick="zoomRecent(30)">🔍 Zoom Last 30 Bars</button>
        <button id="btn-sr" onclick="toggleSR()">📏 Toggle S/R Lines</button>
        <button id="btn-markers" onclick="toggleMarkers()">🎯 Toggle Markers</button>
    </div>

    <div id="chart-container">
        <div id="chart-legend" class="chart-legend">
            <span class="legend-pair">{pair} · 1m</span>
            <span class="legend-ohlc">
                <span>O: <span id="leg-open" class="leg-val">-</span></span>
                <span>H: <span id="leg-high" class="leg-val">-</span></span>
                <span>L: <span id="leg-low" class="leg-val">-</span></span>
                <span>C: <span id="leg-close" class="leg-val">-</span></span>
                <span id="leg-change" class="leg-val">-</span>
            </span>
            <span class="legend-extra">
                <span>Type: <span id="leg-type" class="leg-val">-</span></span>
                <span style="color: #10b981;">Supp: <span id="leg-supp" class="leg-val">-</span></span>
                <span style="color: #ef4444;">Res: <span id="leg-res" class="leg-val">-</span></span>
            </span>
        </div>
    </div>

    <div class="inspector-panel" id="inspector">
        <div class="inspector-item"><span class="lbl">Candle Time (UTC)</span><span class="val" id="ins-time">-</span></div>
        <div class="inspector-item"><span class="lbl">Open</span><span class="val" id="ins-open">-</span></div>
        <div class="inspector-item"><span class="lbl">High</span><span class="val" id="ins-high">-</span></div>
        <div class="inspector-item"><span class="lbl">Low</span><span class="val" id="ins-low">-</span></div>
        <div class="inspector-item"><span class="lbl">Close</span><span class="val" id="ins-close">-</span></div>
        <div class="inspector-item"><span class="lbl">Change</span><span class="val" id="ins-change">-</span></div>
        <div class="inspector-item"><span class="lbl">Body</span><span class="val" id="ins-body">-</span></div>
        <div class="inspector-item"><span class="lbl">Upper Wick</span><span class="val" id="ins-uw">-</span></div>
        <div class="inspector-item"><span class="lbl">Lower Wick</span><span class="val" id="ins-lw">-</span></div>
        <div class="inspector-item"><span class="lbl">Candle Type</span><span class="val" id="ins-type">-</span></div>
        <div class="inspector-item"><span class="lbl">20-Bar Support</span><span class="val" style="color: var(--bullish);" id="ins-supp">-</span></div>
        <div class="inspector-item"><span class="lbl">20-Bar Resistance</span><span class="val" style="color: var(--bearish);" id="ins-res">-</span></div>
    </div>

    <div class="section-title">
        📋 Pattern Analysis & Verification Audit Table
    </div>

    <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Pattern Time (UTC)</th>
                    <th>Pattern Name</th>
                    <th>Direction</th>
                    <th>Key Level</th>
                    <th>Audit Status</th>
                    <th>Rule Verification Breakdown</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
{table_body}
            </tbody>
        </table>
    </div>

    <script>
        const candleData = {json.dumps(candle_data)};
        const markersData = {json.dumps(markers)};
        const analysisData = {json.dumps(analysis_map)};
        const supportSeriesData = {json.dumps(support_series)};
        const resistanceSeriesData = {json.dumps(resistance_series)};
        const highlightSetup = {highlight_json};

        const pricePrecision = {precision};
        const priceMinMove = {min_move};
        const priceFormatConfig = {{
            type: 'price',
            precision: pricePrecision,
            minMove: priceMinMove,
        }};

        const container = document.getElementById('chart-container');
        const chart = LightweightCharts.createChart(container, {{
            width: container.clientWidth,
            height: 520,
            layout: {{
                background: {{ color: '#131722' }},
                textColor: '#d1d4dc',
            }},
            localization: {{
                priceFormatter: (p) => Number(p).toFixed(pricePrecision),
            }},
            grid: {{
                vertLines: {{ color: '#1f2937' }},
                horzLines: {{ color: '#1f2937' }},
            }},
            crosshair: {{
                mode: LightweightCharts.CrosshairMode.Normal,
            }},
            rightPriceScale: {{
                borderColor: '#363a45',
            }},
            timeScale: {{
                borderColor: '#363a45',
                timeVisible: true,
                secondsVisible: false,
            }},
        }});

        window.addEventListener('resize', () => {{
            chart.applyOptions({{ width: container.clientWidth }});
        }});

        const candleSeries = chart.addCandlestickSeries({{
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderVisible: false,
            wickUpColor: '#26a69a',
            wickDownColor: '#ef5350',
            priceFormat: priceFormatConfig,
        }});
        candleSeries.setData(candleData);
        candleSeries.setMarkers(markersData);

        const supportSeries = chart.addLineSeries({{
            color: '#10b981',
            lineWidth: 1,
            lineStyle: LightweightCharts.LineStyle.Dashed,
            title: '20-Bar Support',
            priceFormat: priceFormatConfig,
        }});
        supportSeries.setData(supportSeriesData);

        const resistanceSeries = chart.addLineSeries({{
            color: '#ef4444',
            lineWidth: 1,
            lineStyle: LightweightCharts.LineStyle.Dashed,
            title: '20-Bar Resistance',
            priceFormat: priceFormatConfig,
        }});
        resistanceSeries.setData(resistanceSeriesData);

        if (highlightSetup && highlightSetup.level) {{
            const isCall = highlightSetup.direction === 'CALL';
            const formattedLevel = Number(highlightSetup.level).toFixed(pricePrecision);
            candleSeries.createPriceLine({{
                price: highlightSetup.level,
                color: isCall ? '#10b981' : '#ef4444',
                lineWidth: 2,
                lineStyle: LightweightCharts.LineStyle.Dashed,
                title: 'Key ' + (isCall ? 'Support' : 'Resistance') + ': ' + formattedLevel,
            }});
        }}

        let showSR = true;
        function toggleSR() {{
            showSR = !showSR;
            supportSeries.applyOptions({{ visible: showSR }});
            resistanceSeries.applyOptions({{ visible: showSR }});
            document.getElementById('btn-sr').classList.toggle('active', showSR);
        }}

        let showMarkers = true;
        function toggleMarkers() {{
            showMarkers = !showMarkers;
            candleSeries.setMarkers(showMarkers ? markersData : []);
            document.getElementById('btn-markers').classList.toggle('active', showMarkers);
        }}

        function zoomRecent(n) {{
            if (candleData.length <= n) {{
                chart.timeScale().fitContent();
                return;
            }}
            const from = candleData[candleData.length - n].time;
            const to = candleData[candleData.length - 1].time + 120;
            chart.timeScale().setVisibleRange({{ from, to }});
        }}

        function zoomToTimestamp(ts) {{
            chart.timeScale().setVisibleRange({{
                from: ts - (12 * 60),
                to: ts + (12 * 60),
            }});
        }}

        function formatPrice(val) {{
            return Number(val).toFixed(pricePrecision);
        }}

        function updateInspector(candle, data) {{
            if (!candle) return;
            const open = candle.open;
            const high = candle.high;
            const low = candle.low;
            const close = candle.close;
            const diff = close - open;
            const diffPct = open !== 0 ? (diff / open) * 100 : 0;
            const isBull = close >= open;
            const colorCls = isBull ? 'bullish' : 'bearish';
            const sign = diff >= 0 ? '+' : '';

            // Update In-Chart Legend (Top-Left overlay)
            document.getElementById('leg-open').innerText = formatPrice(open);
            document.getElementById('leg-high').innerText = formatPrice(high);
            document.getElementById('leg-low').innerText = formatPrice(low);
            document.getElementById('leg-close').innerText = formatPrice(close);
            
            const legChange = document.getElementById('leg-change');
            legChange.innerText = `${{sign}}${{formatPrice(diff)}} (${{sign}}${{diffPct.toFixed(2)}}%)`;
            legChange.className = 'leg-val ' + colorCls;

            const cType = data ? data.type : (isBull ? 'Bullish' : 'Bearish');
            const legType = document.getElementById('leg-type');
            legType.innerText = cType;
            legType.className = 'leg-val ' + colorCls;

            document.getElementById('leg-supp').innerText = data ? data.support : '-';
            document.getElementById('leg-res').innerText = data ? data.resistance : '-';

            // Update Bottom Inspector Panel
            const timeStr = data ? data.time_str : (new Date(candle.time * 1000).toISOString().replace('T', ' ').substring(0, 19) + ' UTC');
            document.getElementById('ins-time').innerText = timeStr;
            document.getElementById('ins-open').innerText = formatPrice(open);
            document.getElementById('ins-high').innerText = formatPrice(high);
            document.getElementById('ins-low').innerText = formatPrice(low);
            document.getElementById('ins-close').innerText = formatPrice(close);

            const insChange = document.getElementById('ins-change');
            insChange.innerText = `${{sign}}${{formatPrice(diff)}} (${{sign}}${{diffPct.toFixed(2)}}%)`;
            insChange.className = 'val ' + colorCls;

            const body = data ? data.body : formatPrice(Math.abs(diff));
            const uw = data ? data.upper_wick : formatPrice(high - Math.max(open, close));
            const lw = data ? data.lower_wick : formatPrice(Math.min(open, close) - low);

            document.getElementById('ins-body').innerText = body;
            document.getElementById('ins-uw').innerText = uw;
            document.getElementById('ins-lw').innerText = lw;

            const typeElem = document.getElementById('ins-type');
            typeElem.innerText = cType;
            typeElem.className = 'val ' + colorCls;

            document.getElementById('ins-supp').innerText = data ? data.support : '-';
            document.getElementById('ins-res').innerText = data ? data.resistance : '-';
        }}

        // Default to latest candle so values are never blank
        const latestCandle = candleData && candleData.length > 0 ? candleData[candleData.length - 1] : null;
        const latestAnalysis = latestCandle ? (analysisData[latestCandle.time] || analysisData[String(latestCandle.time)]) : null;

        // Initialize immediately on load!
        if (latestCandle) {{
            updateInspector(latestCandle, latestAnalysis);
        }}

        // Crosshair move inspection
        chart.subscribeCrosshairMove(param => {{
            if (
                param === undefined ||
                param.point === undefined ||
                !param.time ||
                param.point.x < 0 ||
                param.point.x > container.clientWidth ||
                param.point.y < 0 ||
                param.point.y > container.clientHeight
            ) {{
                if (latestCandle) {{
                    updateInspector(latestCandle, latestAnalysis);
                }}
                return;
            }}

            const candle = param.seriesData ? param.seriesData.get(candleSeries) : null;
            if (!candle) {{
                return;
            }}

            const t = typeof candle.time === 'number' ? candle.time : (candle.time && candle.time.timestamp ? candle.time.timestamp : param.time);
            const data = analysisData[t] || analysisData[String(t)] || null;

            updateInspector(candle, data);
        }});

        container.addEventListener('mouseleave', () => {{
            if (latestCandle) {{
                updateInspector(latestCandle, latestAnalysis);
            }}
        }});

        if (highlightSetup && highlightSetup.time) {{
            zoomToTimestamp(highlightSetup.time);
        }} else {{
            zoomRecent(60);
        }}
    </script>
</body>
</html>
"""
    return html


def recreate_tradingview_chart(pair, df=None, highlight_setup=None, from_cache=False, auto_open=True, n_bars=180, send_tg=False):
    """
    Component: Recreates the TradingView chart for visual verification of patterns,
    candle types, retracements, and S/R key levels.
    """
    pair_slug = pair.replace("/", "_")
    os.makedirs(CHARTS_DIR, exist_ok=True)

    if from_cache or df is None:
        if from_cache:
            print(f"📂 [CACHE] Loading candles for {pair} from SQLite cache (zero API calls)...")
            cached_df, cached_setups = get_cached_candles_and_analysis(pair, limit=n_bars)
            if cached_df is not None and not cached_df.empty:
                df = cached_df
                setups = cached_setups
            else:
                print(f"⚠️ No cached candles found for {pair} in SQLite. Falling back to TradingView fetch...")
                df = get_candles(pair)
                df, setups = update_market_cache_and_analyze(pair, df)
        else:
            df = get_candles(pair)
            df, setups = update_market_cache_and_analyze(pair, df)
    else:
        df, setups = update_market_cache_and_analyze(pair, df)

    if df is None or df.empty:
        print(f"❌ Cannot recreate chart for {pair}: No candlestick data available.")
        return None

    html_content = build_chart_html(pair, df, setups, highlight_setup=highlight_setup)

    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamped_file = os.path.join(CHARTS_DIR, f"chart_{pair_slug}_{now_str}.html")
    latest_file = os.path.join(CHARTS_DIR, f"latest_{pair_slug}.html")

    with open(timestamped_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    with open(latest_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"📊 [CHART CREATED] TradingView recreated chart saved to:")
    print(f"   • Latest:      {latest_file}")
    print(f"   • Timestamped: {timestamped_file}")

    if auto_open:
        try:
            webbrowser.open(f"file:///{os.path.abspath(latest_file)}")
            print(f"🌐 Opened chart in browser.")
        except Exception as e:
            print(f"⚠️ Could not open browser automatically: {e}")

    if send_tg:
        send_telegram_document(latest_file, caption=f"📊 TradingView Recreated Chart: {pair} (1m)")

    return latest_file


def recreate_signal_chart(result, df=None, auto_open=True, send_tg=False):
    """
    Output Handler: Generates and opens an interactive verification chart
    specifically highlighting a newly triggered signal.
    """
    pair = result["pair"]
    if isinstance(df, bool):
        auto_open = df
        df = None
    if df is None:
        df = result.get("df")
    return recreate_tradingview_chart(pair, df=df, highlight_setup=result, auto_open=auto_open, send_tg=send_tg)




def audit_pair_patterns(pair, from_cache=False, n_bars=180):
    """
    CLI Tool: Audits and prints all detected price action patterns and their
    confirmation breakdown for a given pair.
    """
    if from_cache:
        df, setups = get_cached_candles_and_analysis(pair, limit=n_bars)
    else:
        df = get_candles(pair)
        df, setups = update_market_cache_and_analyze(pair, df)

    if not setups:
        print(f"No patterns found for {pair}.")
        return

    print("=" * 80)
    print(f"PRICE ACTION PATTERN AUDIT REPORT: {pair}")
    print(f"TOTAL BARS: {len(df) if df is not None else 0} | TOTAL SETUPS: {len(setups)}")
    print("=" * 80)
    for idx, s in enumerate(setups, 1):
        status_icon = "✅" if s.get("status") == "CONFIRMED_SIGNAL" else "⚠️"
        p_name = s.get("pattern") or s.get("pattern_name", "Pattern")
        print(f"{idx}. {status_icon} [{s.get('status')}] {p_name} ({s['direction']})")
        print(f"   Time:      {s['pattern_time']}")
        print(f"   Key Level: {float(s['level']):.5f}")
        print(f"   Reason:    {s['reason']}\n")


# ============================================================
# DEDUPLICATION & SCANNING PIPELINE
# ============================================================

def prune_sent_keys():
    now = time.time()
    cutoff = now - 86400  # 24 hours ago
    keys_to_delete = [k for k, ts in SENT_KEYS_CACHE.items() if ts < cutoff]
    for k in keys_to_delete:
        del SENT_KEYS_CACHE[k]


def validate_entry(df, setup):
    """
    Confirms that the required retracement confirmation candle has just closed.
    The next candle to form (index == len(df)) is the entry candle.
    Prevents triggering on old, stale setups from previous minutes.
    """
    entry_index = setup["entry_index"]
    return entry_index == len(df) or entry_index == len(df) - 1


def scan_pair(pair):
    df = get_candles(pair)
    if df is None or len(df) < 5:
        return None

    # ================================================================
    # 1. TRADINGVIEW RAW MARKET DATA LOGGING (TEXT FILE)
    # (Comment the line below to turn OFF saving raw text log)
    # ================================================================
    log_tv_data_to_file(pair, df)

    # ================================================================
    # 2. PERSISTENT MARKET DATA & IDEMPOTENT ANALYSIS CACHE (SQLITE)
    # (Comment the line below to turn OFF SQLite caching & persistent analysis)
    # ================================================================
    update_market_cache_and_analyze(pair, df)

    # ================================================================
    # 3. AUTO CHART RECREATION ON EACH SCAN CYCLE (HTML VISUALIZATION)
    # (Uncomment the line below to turn ON chart generation on every scan)
    # ================================================================
    # recreate_tradingview_chart(pair, df, auto_open=False)

    # CRITICAL: Always slice off the last row (the in-progress forming candle)
    completed = df.iloc[:-1].copy()
    setup = find_recent_setup(completed)

    if not setup:
        return None

    if not validate_entry(completed, setup):
        return None

    news_block, news_item = relevant_news_for_pair(pair)
    if news_block:
        return {
            "blocked": True,
            "pair": pair,
            "reason": "Relevant recent high-impact forex news detected.",
            "news": news_item,
        }

    pattern_row = completed.iloc[setup["pattern_index"]]
    entry_row = completed.iloc[-1]
    return {
        "blocked": False,
        "pair": pair,
        "direction": setup["direction"],
        "pattern": setup["pattern"],
        "level": setup["level"],
        "price": float(entry_row["close"]),
        "candle_time": pattern_row["time"],
        "reason": setup["reason"],
        "df": df,
    }



def wait_for_candle_close():
    now = datetime.now(timezone.utc)
    seconds_to_wait = 60 - now.second + 2
    if seconds_to_wait > 60:
        seconds_to_wait -= 60

    print(f"⏳ Sleeping {seconds_to_wait:.1f}s until next 1-minute candle close (:02s)...")
    time.sleep(seconds_to_wait)


# ============================================================
# MAIN SERVICE LOOP
# ============================================================

def main():
    check_settings()

    print("=" * 70)
    print("PDF PRICE ACTION LIVE SIGNAL BOT (V3 - TRADINGVIEW FEED)")
    print("FEED PROVIDER:    TRADINGVIEW (FX_IDC)")
    print(f"CANDLE SYNC:      {'ENABLED (triggers at :02s of each minute)' if CANDLE_SYNC else 'DISABLED'}")
    print(f"INTER-PAIR DELAY: {PAIR_REQUEST_DELAY}s (Rate-limit pacing)")
    print("19 FX PAIRS | 1-MINUTE CANDLES | PURE PRICE ACTION (NO INDICATORS)")
    print("=" * 70)

    while True:
        if CANDLE_SYNC:
            wait_for_candle_close()

        cycle_start = time.time()
        prune_sent_keys()

        for pair in PAIRS:
            try:
                result = scan_pair(pair)

                if result is None:
                    time.sleep(PAIR_REQUEST_DELAY)
                    continue

                if result.get("blocked"):
                    print(f"{pair}: SIGNAL BLOCKED - High Impact News in progress")
                    time.sleep(PAIR_REQUEST_DELAY)
                    continue

                key = (
                    result["pair"],
                    result["pattern"],
                    str(result["candle_time"]),
                )

                if key in SENT_KEYS_CACHE:
                    time.sleep(PAIR_REQUEST_DELAY)
                    continue

                # Construct Alert Message (with all emojis & formatted values)
                message = (
                    "🚨 PDF PRICE ACTION SIGNAL (V3 - TRADINGVIEW) 🚨\n\n"
                    f"💱 Pair: {result['pair']}\n"
                    f"⏱ Timeframe: 1 Minute\n"
                    f"📊 Signal: {result['direction']}\n"
                    f"🕯 Pattern: {result['pattern']}\n"
                    f"💰 Price: {result['price']}\n"
                    f"📍 Key Level: {result['level']}\n\n"
                    f"📌 PDF Rule:\n{result['reason']}\n\n"
                    "📡 Provider: TRADINGVIEW (FX_IDC)\n"
                    "📰 News filter: CLEAR\n"
                    "⚠️ Demo/backtest before live money."
                )

                # ================================================================
                # BOT OUTPUT HANDLERS
                # (Comment or uncomment any line below to toggle!)
                # ================================================================

                # 1. FILE LOGGING: Comment the line below to turn OFF saving to file
                print(f"💾 Logging signal to file...", message)
                log_signal_to_file(message)

                # 2. TELEGRAM TEXT ALERT: Comment the line below to turn OFF Telegram text alerts
                send_telegram(message)

                # 3. RECREATE SIGNAL CHART: Comment the line below to turn OFF chart generation/popup
                chart_file = recreate_signal_chart(result, auto_open=True)

                # 4. SEND CHART HTML TO TELEGRAM: Comment the line below to turn OFF sending HTML chart file to Telegram
                send_telegram_document(chart_file, caption=f"📊 Interactive Verification Chart: {result['pair']} ({result['direction']})")


                SENT_KEYS_CACHE[key] = time.time()

                print(
                    f"SIGNAL | {pair} | "
                    f"{result['direction']} | "
                    f"{result['pattern']} | Key Level: {result['level']}"
                )

                time.sleep(PAIR_REQUEST_DELAY)

            except requests.HTTPError as e:
                print(f"{pair}: API HTTP error: {e}")
                time.sleep(PAIR_REQUEST_DELAY)

            except Exception as e:
                print(f"{pair}: ERROR: {e}")
                time.sleep(PAIR_REQUEST_DELAY)

        elapsed = time.time() - cycle_start
        print(f"✅ Completed scan cycle across 19 pairs in {elapsed:.1f}s.")

        if not CANDLE_SYNC:
            remaining_sleep = max(1.0, SCAN_INTERVAL_SECONDS - elapsed)
            time.sleep(remaining_sleep)


def run_test_signal(pair="GBP/USD"):
    """
    Test Utility: Injects an immediate test signal, executing all 4 output handlers:
      1. File logging (signals_history.log)
      2. Telegram text alert
      3. Recreate interactive HTML chart locally in charts/ and auto-open
      4. Upload and send the HTML chart file directly to Telegram
    Provides instant verification that the signal, local chart, and Telegram pipeline work.
    """
    print("=" * 70)
    print(f"🧪 [TEST SIGNAL] Triggering verification test signal for {pair}...")
    print("=" * 70)

    df, setups = get_cached_candles_and_analysis(pair, limit=180)
    if df is None or df.empty:
        df = get_candles(pair)
        df, setups = update_market_cache_and_analyze(pair, df)

    last_row = df.iloc[-1]
    supp, res = key_levels(df, len(df) - 1)
    
    mock_result = {
        "blocked": False,
        "pair": pair,
        "direction": "CALL",
        "pattern": "Bullish Engulfing",
        "level": supp,
        "price": float(last_row["close"]),
        "candle_time": str(last_row["time"]),
        "reason": "Retracement touched support, rejected and formed weak bearish candle.",
        "df": df,
    }

    message = (
        "🚨 PDF PRICE ACTION SIGNAL (V3 - TRADINGVIEW) 🚨\n\n"
        f"💱 Pair: {mock_result['pair']}\n"
        f"⏱ Timeframe: 1 Minute\n"
        f"📊 Signal: {mock_result['direction']}\n"
        f"🕯 Pattern: {mock_result['pattern']}\n"
        f"💰 Price: {mock_result['price']}\n"
        f"📍 Key Level: {mock_result['level']}\n\n"
        f"📌 PDF Rule:\n{mock_result['reason']}\n\n"
        "📡 Provider: TRADINGVIEW (FX_IDC)\n"
        "📰 News filter: CLEAR\n"
        "⚠️ Verification test signal."
    )

    print("1. 💾 Logging signal to file...")
    log_signal_to_file(message)

    print("2. 📨 Dispatching Telegram text alert...")
    send_telegram(message)

    print("3. 📊 Generating local interactive verification chart...")
    chart_file = recreate_signal_chart(mock_result, auto_open=True)
    print(f"   • Local chart file: {chart_file}")

    print("4. 📤 Dispatching chart HTML file to Telegram...")
    send_telegram_document(chart_file, caption=f"📊 Interactive Verification Chart: {mock_result['pair']} ({mock_result['direction']})")

    print("=" * 70)
    print("✅ [TEST COMPLETE] Local chart created and all signal handlers executed!")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PDF Price Action Bot V3 & TradingView Chart Recreator")
    parser.add_argument("--chart", type=str, default=None, help="Recreate chart for pair (e.g. EUR/USD)")
    parser.add_argument("--from-cache", action="store_true", help="Load candles from local SQLite cache instead of TradingView")
    parser.add_argument("--audit", type=str, default=None, help="Print pattern audit report for pair")
    parser.add_argument("--bars", type=int, default=180, help="Bars to fetch (default: 180)")
    parser.add_argument("--no-open", action="store_true", help="Do not auto-open browser")
    parser.add_argument("--send-telegram", action="store_true", help="Send generated HTML chart file to Telegram")
    parser.add_argument("--test-signal", action="store_true", help="Run end-to-end verification signal with local chart & Telegram dispatch")
    args = parser.parse_args()

    if args.test_signal:
        test_pair = args.chart if args.chart else "GBP/USD"
        run_test_signal(test_pair)
    elif args.chart:
        recreate_tradingview_chart(
            args.chart,
            from_cache=args.from_cache,
            auto_open=not args.no_open,
            n_bars=args.bars,
            send_tg=args.send_telegram
        )
    elif args.audit:
        audit_pair_patterns(args.audit, from_cache=args.from_cache, n_bars=args.bars)
    else:
        main()

