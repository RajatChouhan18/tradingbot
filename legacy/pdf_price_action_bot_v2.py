"""
PDF-BASED PRICE ACTION BOT (VERSION 2.0)
Source: BO Price Action Book by Ishaq's Binary Academy

===============================================================================
A NON-TRADING DEVELOPER'S GUIDE TO THIS BOT
===============================================================================

1. WHAT DOES THIS BOT DO?
   This program continuously analyzes live foreign exchange (Forex) price charts
   across 19 currency pairs (like EUR/USD, GBP/JPY). It looks for specific
   visual candlestick patterns and sends a Telegram alert whenever a high-probability
   setup forms.

2. TRADING CONCEPTS EXPLAINED IN SOFTWARE TERMS:
   - Candlestick (OHLC):
     Every 1-minute time window is summarized by 4 numbers:
       * Open:  The price at the start of the minute (:00s).
       * High:  The highest price reached during the minute.
       * Low:   The lowest price reached during the minute.
       * Close: The price at the end of the minute (:59s).
   - Bullish (Green / Up):
     When Close > Open (price went up during that minute).
   - Bearish (Red / Down):
     When Close < Open (price went down during that minute).
   - Candle Body:
     The rectangle between Open and Close. Represents the primary price movement.
   - Candle Wicks (or Shadows):
     The thin vertical lines extending above and below the body.
     They represent price extremes that were tested and rejected by market participants.
   - CALL vs. PUT:
     * CALL = We predict price will go UP on the next candle (Buy / Long).
     * PUT  = We predict price will go DOWN on the next candle (Sell / Short).
   - Support (Floor):
     The lowest price level seen in the recent lookback window (last 20 candles).
     Traders expect buyers to step in and prevent the price from dropping further.
   - Resistance (Ceiling):
     The highest price level seen in the recent lookback window (last 20 candles).
     Traders expect sellers to step in and prevent the price from rising further.
   - Retracement (Pullback):
     After a strong directional move, price often temporarily pulls back like a
     stretched rubber band before resuming. The strategy requires waiting for
     this pullback candle rather than chasing the initial move.
   - Level Rejection:
     A candle's wick touches or crosses the Support/Resistance level, but the
     candle's body closes back on the safe side. This proves market participants
     defended that price level.

3. WHY NO TECHNICAL INDICATORS (NO RSI, EMA, MACD)?
   Mathematical indicators (like moving averages) calculate historical averages
   and therefore lag behind real-time market movements. This bot relies purely
   on "Price Action" (raw price geometry and volume psychology directly from
   candlestick shapes).

4. WHY DISCARD THE LAST CANDLE (df.iloc[:-1])?
   The candle currently forming in real-time is mutable—its close and wicks can
   change until the exact 60th second. Using in-progress candles causes "repainting"
   (false signals that disappear). We only analyze 100% finalized, closed candles.
"""

import os
import sys
import time
import math
import random
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
import requests
import pandas as pd

# Ensure UTF-8 output encoding on Windows consoles to prevent UnicodeEncodeError
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Load sensitive keys (.env file) into environment variables
load_dotenv()

# ============================================================
# CONFIGURATION & SETTINGS
# ============================================================

# Data source selector: 'finnhub', 'twelvedata', 'oanda', 'mt5', or 'mock'
DATA_PROVIDER = os.getenv("DATA_PROVIDER", "finnhub").lower().strip()

# API Keys & Authentication Credentials
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY", "")
OANDA_API_KEY = os.getenv("OANDA_API_KEY", "")
OANDA_ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID", "")
OANDA_ENVIRONMENT = os.getenv("OANDA_ENVIRONMENT", "practice")  # 'practice' (demo) or 'live'

# Telegram Notification Settings
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")

# Execution Schedule & Rate Limiting
CANDLE_SYNC = os.getenv("CANDLE_SYNC", "true").lower() == "true"
PAIR_REQUEST_DELAY = float(os.getenv("PAIR_REQUEST_DELAY", "1.2"))  # Delay in seconds between scanning pairs
SCAN_INTERVAL_SECONDS = int(os.getenv("SCAN_INTERVAL_SECONDS", "60"))  # Fallback sleep if CANDLE_SYNC is disabled
LOOKBACK_MINUTES = 180       # Download 3 hours of historical 1-minute data for context
NEWS_LOOKBACK_MINUTES = 10   # How recent a news event must be to trigger a safety block
NEWS_CACHE_TTL = 60          # Cache news API responses for 60 seconds to conserve API credits

# API Endpoint Base URLs
FINNHUB_BASE_URL = "https://finnhub.io/api/v1"
TWELVEDATA_BASE_URL = "https://api.twelvedata.com"
OANDA_BASE_URL = (
    "https://api-fxtrade.oanda.com/v3"
    if OANDA_ENVIRONMENT == "live"
    else "https://api-fxpractice.oanda.com/v3"
)

# 19 Monitored Currency Pairs and their platform-specific ticker symbols
PAIRS = {
    "EUR/JPY": {"finnhub": "OANDA:EUR_JPY", "twelvedata": "EUR/JPY", "oanda": "EUR_JPY", "mt5": "EURJPY"},
    "CAD/JPY": {"finnhub": "OANDA:CAD_JPY", "twelvedata": "CAD/JPY", "oanda": "CAD_JPY", "mt5": "CADJPY"},
    "EUR/USD": {"finnhub": "OANDA:EUR_USD", "twelvedata": "EUR/USD", "oanda": "EUR_USD", "mt5": "EURUSD"},
    "USD/JPY": {"finnhub": "OANDA:USD_JPY", "twelvedata": "USD/JPY", "oanda": "USD_JPY", "mt5": "USDJPY"},
    "AUD/JPY": {"finnhub": "OANDA:AUD_JPY", "twelvedata": "AUD/JPY", "oanda": "AUD_JPY", "mt5": "AUDJPY"},
    "AUD/USD": {"finnhub": "OANDA:AUD_USD", "twelvedata": "AUD/USD", "oanda": "AUD_USD", "mt5": "AUDUSD"},
    "AUD/CAD": {"finnhub": "OANDA:AUD_CAD", "twelvedata": "AUD/CAD", "oanda": "AUD_CAD", "mt5": "AUDCAD"},
    "GBP/USD": {"finnhub": "OANDA:GBP_USD", "twelvedata": "GBP/USD", "oanda": "GBP_USD", "mt5": "GBPUSD"},
    "GBP/AUD": {"finnhub": "OANDA:GBP_AUD", "twelvedata": "GBP/AUD", "oanda": "GBP_AUD", "mt5": "GBPAUD"},
    "GBP/CAD": {"finnhub": "OANDA:GBP_CAD", "twelvedata": "GBP/CAD", "oanda": "GBP_CAD", "mt5": "GBPCAD"},
    "GBP/CHF": {"finnhub": "OANDA:GBP_CHF", "twelvedata": "GBP/CHF", "oanda": "GBP_CHF", "mt5": "GBPCHF"},
    "GBP/JPY": {"finnhub": "OANDA:GBP_JPY", "twelvedata": "GBP/JPY", "oanda": "GBP_JPY", "mt5": "GBPJPY"},
    "USD/CAD": {"finnhub": "OANDA:USD_CAD", "twelvedata": "USD/CAD", "oanda": "USD_CAD", "mt5": "USDCAD"},
    "USD/CHF": {"finnhub": "OANDA:USD_CHF", "twelvedata": "USD/CHF", "oanda": "USD_CHF", "mt5": "USDCHF"},
    "EUR/GBP": {"finnhub": "OANDA:EUR_GBP", "twelvedata": "EUR/GBP", "oanda": "EUR_GBP", "mt5": "EURGBP"},
    "CHF/JPY": {"finnhub": "OANDA:CHF_JPY", "twelvedata": "CHF/JPY", "oanda": "CHF_JPY", "mt5": "CHFJPY"},
    "EUR/AUD": {"finnhub": "OANDA:EUR_AUD", "twelvedata": "EUR/AUD", "oanda": "EUR_AUD", "mt5": "EURAUD"},
    "EUR/CAD": {"finnhub": "OANDA:EUR_CAD", "twelvedata": "EUR/CAD", "oanda": "EUR_CAD", "mt5": "EURCAD"},
    "EUR/CHF": {"finnhub": "OANDA:EUR_CHF", "twelvedata": "EUR/CHF", "oanda": "EUR_CHF", "mt5": "EURCHF"},
}

# Lookup set to quickly check which individual fiat currencies belong to each pair
# e.g., "EUR/USD" -> {"EUR", "USD"}
PAIR_CURRENCIES = {pair: set(pair.split("/")) for pair in PAIRS}

# In-memory runtime state:
# NEWS_CACHE stores news headline data to prevent hitting the news API for every single pair.
NEWS_CACHE = {"timestamp": 0, "data": []}

# SENT_KEYS_CACHE maps (pair, pattern, candle_timestamp) -> emission_timestamp.
# Prevents duplicate alert messages for the exact same candle.
SENT_KEYS_CACHE = {}


# ============================================================
# SYSTEM & ENVIRONMENT VERIFICATION
# ============================================================

def check_settings():
    """
    Validates that required configuration and secrets exist.
    Raises RuntimeError on missing mandatory variables and warns if Telegram
    chat ID is invalid or unconfigured.
    """
    missing = []

    if DATA_PROVIDER in ["mock", "demo", "sim"]:
        pass  # Mock provider generates synthetic candles for end-to-end testing
    elif DATA_PROVIDER == "finnhub" and not FINNHUB_API_KEY:
        missing.append("FINNHUB_API_KEY")
    elif DATA_PROVIDER == "twelvedata" and not TWELVEDATA_API_KEY:
        missing.append("TWELVEDATA_API_KEY")
    elif DATA_PROVIDER == "oanda" and not OANDA_API_KEY:
        missing.append("OANDA_API_KEY")

    if not CHAT_ID or CHAT_ID == "dummy_chat_id":
        print("⚠️ [WARNING] CHAT_ID is empty or set to 'dummy_chat_id'. If Telegram alert is uncommented, it will be skipped.")

    if missing:
        raise RuntimeError("Missing required environment variables: " + ", ".join(missing))


# ============================================================
# DATA PROVIDER IMPLEMENTATIONS
# ============================================================

def api_get_finnhub(path, params=None):
    """
    Low-level HTTP GET client for Finnhub.
    Handles authentication query parameters, timeouts, and HTTP 429 rate limit backoff.
    """
    params = dict(params or {})
    params["token"] = FINNHUB_API_KEY

    response = requests.get(
        FINNHUB_BASE_URL + path,
        params=params,
        timeout=15,
    )

    # HTTP 429 indicates we exceeded the provider's allowed requests-per-minute.
    if response.status_code == 429:
        print("⚠️ [RATE LIMIT] Finnhub returned 429 (Too Many Requests). Cooling down for 30s...")
        time.sleep(30)
        response.raise_for_status()

    if response.status_code == 403:
        if not getattr(api_get_finnhub, "_warned_403", False):
            print("\n❌ [FINNHUB 403 FORBIDDEN] Finnhub's /forex/candle endpoint requires a paid subscription.")
            print("   💡 Options for testing or live trading:")
            print("   1. Set DATA_PROVIDER=mock in .env for simulated price action testing.")
            print("   2. Set DATA_PROVIDER=twelvedata in .env with a free Twelve Data API key.")
            print("   3. Set DATA_PROVIDER=oanda in .env with a free OANDA practice account token.")
            print("   4. Set DATA_PROVIDER=mt5 in .env if using MetaTrader 5 on Windows.\n")
            api_get_finnhub._warned_403 = True
        return None

    response.raise_for_status()
    return response.json()


def get_candles_finnhub(symbol):
    """
    Downloads 1-minute candlestick data from Finnhub's /forex/candle endpoint.
    
    Data Schema Returned by Finnhub:
      t: List of Unix timestamps (in seconds)
      o: List of Open prices
      h: List of High prices
      l: List of Low prices
      c: List of Close prices
      s: Status string ('ok' or 'no_data')
    """
    now = int(time.time())
    start = now - LOOKBACK_MINUTES * 60

    data = api_get_finnhub(
        "/forex/candle",
        {
            "symbol": symbol,
            "resolution": "1",
            "from": start,
            "to": now,
        },
    )

    if not data or data.get("s") != "ok":
        return None

    required = ["t", "o", "h", "l", "c"]
    if any(k not in data for k in required):
        return None

    df = pd.DataFrame(
        {
            "time": pd.to_datetime(data["t"], unit="s", utc=True),
            "open": data["o"],
            "high": data["h"],
            "low": data["l"],
            "close": data["c"],
        }
    )

    # Sanitize and sort time series chronologically (oldest -> newest)
    df = df.dropna().drop_duplicates("time")
    df = df.sort_values("time").reset_index(drop=True)
    return df if len(df) >= 20 else None


def get_candles_twelvedata(symbol):
    """
    Alternative Provider: Twelve Data REST API.
    Used if user switches DATA_PROVIDER="twelvedata" in .env.
    """
    params = {
        "symbol": symbol,
        "interval": "1min",
        "outputsize": LOOKBACK_MINUTES,
        "apikey": TWELVEDATA_API_KEY,
    }
    response = requests.get(f"{TWELVEDATA_BASE_URL}/time_series", params=params, timeout=15)
    response.raise_for_status()
    data = response.json()

    if "values" not in data:
        return None

    # Twelve Data returns newest first; reverse so oldest is at index 0
    df = pd.DataFrame(data["values"])
    df = df.rename(columns={"datetime": "time"})
    df["time"] = pd.to_datetime(df["time"], utc=True)
    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna().drop_duplicates("time")
    df = df.sort_values("time").reset_index(drop=True)
    return df if len(df) >= 20 else None


def get_candles_oanda(instrument):
    """
    Alternative Provider: OANDA v20 Broker REST API.
    Fetches mid-price M1 candles directly from a demo or live OANDA account.
    """
    headers = {"Authorization": f"Bearer {OANDA_API_KEY}"}
    params = {"granularity": "M1", "count": LOOKBACK_MINUTES, "price": "M"}
    url = f"{OANDA_BASE_URL}/instruments/{instrument}/candles"

    response = requests.get(url, headers=headers, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()

    candles = data.get("candles", [])
    if not candles:
        return None

    rows = []
    for c in candles:
        if not c.get("complete", False):
            continue
        mid = c.get("mid", {})
        rows.append(
            {
                "time": pd.to_datetime(c["time"]),
                "open": float(mid["o"]),
                "high": float(mid["h"]),
                "low": float(mid["l"]),
                "close": float(mid["c"]),
            }
        )

    df = pd.DataFrame(rows)
    df = df.dropna().drop_duplicates("time")
    df = df.sort_values("time").reset_index(drop=True)
    return df if len(df) >= 20 else None


def get_candles_mt5(symbol):
    """
    Alternative Provider: MetaTrader 5 Desktop Terminal.
    Pulls data with zero external HTTP latency directly from the running MT5 terminal.
    Requires: pip install MetaTrader5 (Windows only).
    """
    try:
        import MetaTrader5 as mt5
    except ImportError:
        print("MetaTrader5 package not installed. Run 'pip install MetaTrader5' to use MT5.")
        return None

    if not mt5.initialize():
        print("MT5 initialization failed:", mt5.last_error())
        return None

    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, LOOKBACK_MINUTES)
    if rates is None or len(rates) < 20:
        return None

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df = df.rename(columns={"open": "open", "high": "high", "low": "low", "close": "close"})
    return df[["time", "open", "high", "low", "close"]]


def get_candles_mock(pair):
    """
    Simulation / Mock Data Provider:
    Generates realistic synthetic 1-minute candlestick data.
    Allows developers and users to test the entire bot lifecycle (candle synchronization,
    state machine, pattern detection, and Telegram alerts) immediately without a paid
    market data subscription.
    """
    now = datetime.now(timezone.utc)
    base = 150.0 if "JPY" in pair else (0.85 if "GBP" in pair else 1.08)
    candles = []

    price = base
    for m in range(50, 0, -1):
        c_time = now - timedelta(minutes=m)
        delta = (random.random() - 0.49) * 0.0004
        c_open = price
        c_close = price + delta
        c_high = max(c_open, c_close) + random.random() * 0.0002
        c_low = min(c_open, c_close) - random.random() * 0.0002
        candles.append(
            {
                "time": c_time,
                "open": round(c_open, 5),
                "high": round(c_high, 5),
                "low": round(c_low, 5),
                "close": round(c_close, 5),
            }
        )
        price = c_close

    # On EUR/USD, inject a textbook Bullish Engulfing + Retracement pattern into recent bars for testing!
    if pair == "EUR/USD" and len(candles) >= 6:
        # Calculate support dynamically from the 20 bars preceding the pattern
        support = min(c["low"] for c in candles[-24:-4])
        # Bar -5: Normal bearish candle
        candles[-5]["open"] = round(support + 0.0008, 5)
        candles[-5]["close"] = round(support + 0.0001, 5)
        candles[-5]["low"] = round(support, 5)
        candles[-5]["high"] = round(support + 0.0009, 5)
        # Bar -4: Bullish Engulfing candle (wraps around Bar -5)
        candles[-4]["open"] = round(support, 5)
        candles[-4]["close"] = round(support + 0.0015, 5)
        candles[-4]["low"] = round(support - 0.0001, 5)
        candles[-4]["high"] = round(support + 0.0016, 5)
        # Bar -3: Retracement candle (weak bearish, touches support and closes above it)
        candles[-3]["open"] = round(support + 0.0010, 5)
        candles[-3]["close"] = round(support + 0.0006, 5)
        candles[-3]["low"] = round(support - 0.0001, 5)  # touches support
        candles[-3]["high"] = round(support + 0.0011, 5)
        # Bar -2: Entry candle closed
        candles[-2]["open"] = round(support + 0.0007, 5)
        candles[-2]["close"] = round(support + 0.0013, 5)
        candles[-2]["low"] = round(support + 0.0006, 5)
        candles[-2]["high"] = round(support + 0.0014, 5)
        # Bar -1: In-progress currently forming candle (will be dropped by iloc[:-1])
        candles[-1]["open"] = round(support + 0.0013, 5)
        candles[-1]["close"] = round(support + 0.0014, 5)
        candles[-1]["low"] = round(support + 0.0012, 5)
        candles[-1]["high"] = round(support + 0.0015, 5)

    return pd.DataFrame(candles)


def get_candles(pair):
    """
    Unified Data Dispatcher.
    Routes the request to the configured data provider (Finnhub, TwelveData, OANDA, MT5, or Mock)
    and returns a standardized pandas DataFrame with columns: ['time', 'open', 'high', 'low', 'close'].
    """
    symbol_info = PAIRS[pair]

    try:
        if DATA_PROVIDER in ["mock", "demo", "sim"]:
            return get_candles_mock(pair)
        elif DATA_PROVIDER == "finnhub":
            return get_candles_finnhub(symbol_info["finnhub"])
        elif DATA_PROVIDER == "twelvedata":
            return get_candles_twelvedata(symbol_info["twelvedata"])
        elif DATA_PROVIDER == "oanda":
            return get_candles_oanda(symbol_info["oanda"])
        elif DATA_PROVIDER == "mt5":
            return get_candles_mt5(symbol_info["mt5"])
        else:
            raise ValueError(f"Unknown DATA_PROVIDER setting: {DATA_PROVIDER}")
    except Exception as e:
        print(f"{pair} [{DATA_PROVIDER}]: Candle fetch error: {e}")
        return None


# ============================================================
# CANDLE GEOMETRY & ANATOMY (NO INDICATORS)
# ============================================================

def candle_parts(row):
    """
    Breaks a single candlestick down into its geometric components.
    
    Structure:
                High ───┬─── Upper Wick (Shadow)
                        │
                Open ┌──┴──┐ (or Close if Bullish)
                     │     │
                     │Body │ = abs(Close - Open)
                     │     │
                Close└──┬──┘ (or Open if Bullish)
                        │
                 Low ───┴─── Lower Wick (Shadow)
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
        "bullish": c > o,  # Price rose
        "bearish": c < o,  # Price fell
    }


def weak_bullish(row):
    """
    Identifies an exhaustion or indecisive bullish candle.
    If the body is small relative to the wicks, buyers lacked strong conviction.
    Rule: Body <= 1.5 * max(upper_wick, lower_wick)
    """
    p = candle_parts(row)
    if not p["bullish"]:
        return False
    return p["body"] <= max(p["upper_wick"], p["lower_wick"]) * 1.5


def weak_bearish(row):
    """
    Identifies an exhaustion or indecisive bearish candle.
    If the body is small relative to the wicks, sellers lacked strong conviction.
    Rule: Body <= 1.5 * max(upper_wick, lower_wick)
    """
    p = candle_parts(row)
    if not p["bearish"]:
        return False
    return p["body"] <= max(p["upper_wick"], p["lower_wick"]) * 1.5


# ============================================================
# TREND & SUPPORT / RESISTANCE DETECTION
# ============================================================

def prior_downtrend(df, end_index, bars=5):
    """
    Tests if the previous N candles formed a downtrend without using moving averages.
    Pure price action definition of a downtrend:
    A sequence of Lower Highs and Lower Lows.
    """
    start = max(0, end_index - bars)
    x = df.iloc[start:end_index]
    if len(x) < 4:
        return False

    highs = x["high"].tolist()
    lows = x["low"].tolist()

    lower_highs = sum(highs[i] <= highs[i - 1] for i in range(1, len(highs)))
    lower_lows = sum(lows[i] <= lows[i - 1] for i in range(1, len(lows)))

    # Allow at most 1 minor counter-candle deviation
    return lower_highs >= len(highs) - 2 and lower_lows >= len(lows) - 2


def prior_uptrend(df, end_index, bars=5):
    """
    Tests if the previous N candles formed an uptrend without using moving averages.
    Pure price action definition of an uptrend:
    A sequence of Higher Highs and Higher Lows.
    """
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
    """
    Calculates dynamic Support and Resistance key levels over the past 20 bars.
    - Support (Floor) = Lowest price reached during the window.
    - Resistance (Ceiling) = Highest price reached during the window.
    """
    start = max(0, end_index - window)
    x = df.iloc[start:end_index]
    support = float(x["low"].min())
    resistance = float(x["high"].max())
    return support, resistance


def touches_level(row, level):
    """
    Checks if a candle's price range physically intersected a key price level.
    (i.e., Low <= Level <= High).
    """
    return float(row["low"]) <= level <= float(row["high"])


def rejects_support(row, support):
    """
    Bullish Rejection of Support (Floor):
    The candle dipped down to touch the support floor, but buyers pushed it back up,
    causing it to close ABOVE the support level.
    """
    p = candle_parts(row)
    return touches_level(row, support) and p["close"] > support


def rejects_resistance(row, resistance):
    """
    Bearish Rejection of Resistance (Ceiling):
    The candle poked up to touch the resistance ceiling, but sellers pushed it back down,
    causing it to close BELOW the resistance level.
    """
    p = candle_parts(row)
    return touches_level(row, resistance) and p["close"] < resistance


# ============================================================
# CANDLESTICK PATTERN RECOGNITION
# ============================================================

def bullish_engulfing(df, i):
    """
    Pattern 1: Bullish Engulfing (Reversal to the Upside).
    Candle i-1 is Bearish (red).
    Candle i is Bullish (green) and completely wraps around (engulfs)
    both the body and the extreme wicks of the previous candle.
    """
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
    """
    Pattern 2: Bearish Engulfing (Reversal to the Downside).
    Candle i-1 is Bullish (green).
    Candle i is Bearish (red) and completely wraps around (engulfs)
    both the body and the extreme wicks of the previous candle.
    """
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
    """
    Pattern 3: Piercing Line (Bullish Reversal Pattern).
    Requirements from PDF:
    - Candle i-1 is a strong Bearish candle.
    - Candle i opens with a gap DOWN below the previous close.
    - Candle i closes ABOVE the 50% midpoint of candle i-1's body, but below its open.
    """
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
    """
    Pattern 4: Dark Cloud Cover (Bearish Reversal Pattern).
    Requirements from PDF:
    - Candle i-1 is a strong Bullish candle.
    - Candle i opens with a gap UP above the previous high.
    - Candle i sinks down and closes BELOW the 50% midpoint of candle i-1's body.
    """
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
    The Core Trading Logic Engine.
    
    CRITICAL PDF RULE:
    Seeing a pattern (e.g. Bullish Engulfing) is NOT enough to trade.
    Novice traders trade immediately and lose to false breakouts.
    The PDF strategy mandates:
      1. Detect Pattern at candle index i.
      2. WAIT for Retracement candle at i+1.
      3. The Retracement candle must touch the Key Level (Support/Resistance)
         and visibly REJECT it.
      4. If the 1st retracement broke the level, wait for a 2nd confirmation candle (i+2).
      5. Issue trade signal for the entry candle only when confirmation closes.
    """
    n = len(df)

    # Search backwards through the last 8 closed bars
    for i in range(max(1, n - 8), n - 1):

        # ----------------------------------------------------
        # SETUP 1: BULLISH ENGULFING -> CALL (BUY)
        # ----------------------------------------------------
        if bullish_engulfing(df, i):
            support, _ = key_levels(df, i)
            retracement = df.iloc[i + 1]

            # Condition A: 1st Retracement is a weak pull-back and bounces off Support
            if weak_bearish(retracement) and rejects_support(retracement, support):
                return {
                    "direction": "CALL",
                    "pattern": "Bullish Engulfing",
                    "pattern_index": i,
                    "entry_index": i + 2,
                    "level": support,
                    "reason": "Retracement touched support, rejected and formed weak bearish candle.",
                }

            # Condition B: 1st candle penetrated support; check if 2nd candle bounced off it
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

        # ----------------------------------------------------
        # SETUP 2: BEARISH ENGULFING -> PUT (SELL)
        # ----------------------------------------------------
        if bearish_engulfing(df, i):
            _, resistance = key_levels(df, i)
            retracement = df.iloc[i + 1]

            # Condition A: 1st Retracement is weak bullish and bounces off Resistance
            if weak_bullish(retracement) and rejects_resistance(retracement, resistance):
                return {
                    "direction": "PUT",
                    "pattern": "Bearish Engulfing",
                    "pattern_index": i,
                    "entry_index": i + 2,
                    "level": resistance,
                    "reason": "Retracement touched resistance, rejected and formed weak bullish candle.",
                }

            # Condition B: 1st candle penetrated resistance; check if 2nd candle rejected it
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

        # ----------------------------------------------------
        # SETUP 3: PIERCING LINE -> CALL (BUY)
        # ----------------------------------------------------
        if piercing_line(df, i) and prior_downtrend(df, i):
            a = candle_parts(df.iloc[i - 1])
            pattern_50 = (a["open"] + a["close"]) / 2.0
            support, _ = key_levels(df, i)
            retracement = df.iloc[i + 1]

            # Retracement must hold above pattern's 50% midpoint and reject Support
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

                # Broken level fallback: wait for 2nd candle rejection
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

        # ----------------------------------------------------
        # SETUP 4: DARK CLOUD COVER -> PUT (SELL)
        # ----------------------------------------------------
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


# ============================================================
# NEWS SAFETY CIRCUIT BREAKER (WITH 60-SECOND CACHE)
# ============================================================

def get_forex_news():
    """
    Fetches global macroeconomic news headlines from Finnhub.
    Caching Optimization:
    Results are cached in-memory for 60 seconds (NEWS_CACHE_TTL).
    Without this cache, iterating over 19 pairs would issue 19 identical news
    requests every cycle, instantly exhausting API credits.
    """
    now = time.time()
    if now - NEWS_CACHE["timestamp"] < NEWS_CACHE_TTL and NEWS_CACHE["data"]:
        return NEWS_CACHE["data"]

    try:
        data = api_get_finnhub("/news", {"category": "forex"})
        NEWS_CACHE["timestamp"] = now
        NEWS_CACHE["data"] = data
        return data
    except Exception as e:
        print("News fetch error:", e)
        return NEWS_CACHE.get("data", [])


def relevant_news_for_pair(pair):
    """
    News Safety Filter.
    News is used strictly as a CIRCUIT BREAKER (inhibition filter).
    It NEVER generates buy/sell signals.
    
    If an unexpected macroeconomic news release (interest rates, inflation, FOMC)
    occurs within 10 minutes for either currency in the pair, the market becomes
    erratic and unpredictable. In this case, any active signal is BLOCKED.
    """
    currencies = PAIR_CURRENCIES[pair]
    now = datetime.now(timezone.utc)
    news = get_forex_news()

    # High-impact news keywords known to cause random market spikes
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

        # If published within the last 10 minutes:
        if 0 <= age_minutes <= NEWS_LOOKBACK_MINUTES:
            # Check if high-impact keywords match
            if any(word in text for word in high_impact_words):
                # Check if the news affects either currency of the pair
                if any(currency.lower() in text for currency in currencies):
                    return True, item

    return False, None


# ============================================================
# TELEGRAM DISPATCH & ALERT NOTIFIER
# ============================================================

def send_telegram(message):
    """
    Dispatches formatted trade alert messages to the user's Telegram channel or chat.
    Uses Telegram's HTTP Bot API sendMessage endpoint.
    """
    if not TELEGRAM_BOT_TOKEN or not CHAT_ID or CHAT_ID == "dummy_chat_id":
        print("[TELEGRAM SKIPPED] Valid TELEGRAM_BOT_TOKEN and CHAT_ID are required to send alerts.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    response = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": message,
        },
        timeout=15,
    )
    response.raise_for_status()


# ============================================================
# FILE LOGGING HELPER
# ============================================================

LOG_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "signals_history.log")


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


# ============================================================
# DEDUPLICATION & MEMORY MANAGEMENT
# ============================================================

def prune_sent_keys():
    """
    Memory leak prevention:
    The bot stores sent signals in SENT_KEYS_CACHE to prevent sending repeated
    alerts for the same minute candle. Over weeks of 24/7 uptime, this dictionary
    would grow indefinitely. This function purges entries older than 24 hours.
    """
    now = time.time()
    cutoff = now - 86400  # 24 hours ago
    keys_to_delete = [k for k, ts in SENT_KEYS_CACHE.items() if ts < cutoff]
    for k in keys_to_delete:
        del SENT_KEYS_CACHE[k]


# ============================================================
# SCANNING PIPELINE FOR A SINGLE PAIR
# ============================================================

def validate_entry(df, setup):
    """
    Confirms that the required confirmation candle has just closed.
    The next candle to form (index == len(df)) is the entry candle.
    Prevents triggering on old, stale setups from previous minutes.
    """
    entry_index = setup["entry_index"]
    return entry_index == len(df) or entry_index == len(df) - 1


def scan_pair(pair):
    """
    Executes the full pipeline for a single currency pair:
      1. Download recent 1-minute candlestick data.
      2. Drop the unclosed, currently forming candle (df.iloc[:-1]).
      3. Scan historical candles for the 4 PDF price action setups.
      4. Verify that the entry confirmation candle has arrived.
      5. Check the Macro News circuit breaker.
      6. Return a signal dictionary or None.
    """
    df = get_candles(pair)
    if df is None or len(df) < 5:
        return None

    # CRITICAL: Always slice off the last row. The last row represents the
    # in-progress candle whose close price is still fluctuating.
    completed = df.iloc[:-1].copy()
    setup = find_recent_setup(completed)

    if not setup:
        return None

    if not validate_entry(completed, setup):
        return None

    # Check Macro News Filter
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
    }


def wait_for_candle_close():
    """
    Candle-Boundary Synchronization:
    1-minute candles close at exactly :00s of every minute.
    Brokers require 1-2 seconds to aggregate and serve that candle over REST APIs.
    This function sleeps until :02s of the upcoming minute so the bot only
    executes queries when fresh, finalized data is guaranteed to exist.
    """
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
    """
    The orchestrator process.
    Initializes configuration, verifies connectivity, and runs the continuous
    scanning cycle across all 19 pairs with pacing and deduplication.
    """
    check_settings()

    print("=" * 70)
    print("PDF PRICE ACTION LIVE SIGNAL BOT (V2.0)")
    print(f"FEED PROVIDER:    {DATA_PROVIDER.upper()}")
    print(f"CANDLE SYNC:      {'ENABLED (triggers at :02s of each minute)' if CANDLE_SYNC else 'DISABLED'}")
    print(f"INTER-PAIR DELAY: {PAIR_REQUEST_DELAY}s (Rate-limit shield)")
    print("19 FX PAIRS | 1-MINUTE CANDLES | PURE PRICE ACTION (NO INDICATORS)")
    print("=" * 70)

    while True:
        # Step 1: Wait until the minute boundary closes
        if CANDLE_SYNC:
            wait_for_candle_close()

        cycle_start = time.time()
        prune_sent_keys()

        # Step 2: Iterate through all 19 monitored Forex pairs
        for pair in PAIRS:
            try:
                result = scan_pair(pair)

                # No setup found on this pair
                if result is None:
                    time.sleep(PAIR_REQUEST_DELAY)
                    continue

                # Setup found, but inhibited by high-impact economic news
                if result.get("blocked"):
                    print(f"{pair}: SIGNAL BLOCKED - High Impact News in progress")
                    time.sleep(PAIR_REQUEST_DELAY)
                    continue

                # Deduplication check: Has an alert already been sent for this exact candle?
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
                    "🚨 PDF PRICE ACTION SIGNAL (V2) 🚨\n\n"
                    f"💱 Pair: {result['pair']}\n"
                    f"⏱ Timeframe: 1 Minute\n"
                    f"📊 Signal: {result['direction']}\n"
                    f"🕯 Pattern: {result['pattern']}\n"
                    f"💰 Price: {result['price']}\n"
                    f"📍 Key Level: {result['level']}\n\n"
                    f"📌 PDF Rule:\n{result['reason']}\n\n"
                    f"📡 Provider: {DATA_PROVIDER.upper()}\n"
                    "📰 News filter: CLEAR\n"
                    "⚠️ Demo/backtest before live money."
                )

                # ================================================================
                # BOT OUTPUT HANDLERS
                # (You can comment or uncomment either line to remove or add it!)
                # ================================================================

                # 1. FILE LOGGING: Comment the line below to turn OFF saving to file
                log_signal_to_file(message)

                # 2. TELEGRAM ALERT: Comment the line below to turn OFF Telegram alerts
                send_telegram(message)

                SENT_KEYS_CACHE[key] = time.time()

                print(
                    f"SIGNAL | {pair} | "
                    f"{result['direction']} | "
                    f"{result['pattern']} | Key Level: {result['level']}"
                )

                # Pacing delay between pair API calls to protect against rate limits
                time.sleep(PAIR_REQUEST_DELAY)

            except requests.HTTPError as e:
                print(f"{pair}: API HTTP error: {e}")
                time.sleep(PAIR_REQUEST_DELAY)

            except Exception as e:
                print(f"{pair}: ERROR: {e}")
                time.sleep(PAIR_REQUEST_DELAY)

        elapsed = time.time() - cycle_start
        print(f"✅ Completed scan cycle across 19 pairs in {elapsed:.1f}s.")

        # If candle synchronization is disabled, sleep for the remainder of the interval
        if not CANDLE_SYNC:
            remaining_sleep = max(1.0, SCAN_INTERVAL_SECONDS - elapsed)
            time.sleep(remaining_sleep)


if __name__ == "__main__":
    main()
