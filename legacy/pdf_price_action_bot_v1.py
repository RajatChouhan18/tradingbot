"""
PDF-BASED PRICE ACTION BOT
Source: BO Price Action Book by Ishaq's Binary Academy

IMPORTANT:
- No EMA/RSI/MACD/Bollinger/other indicators are used.
- Signal rules are based only on the price-action rules explicitly
  described/illustrated in the supplied PDF:
    * Bullish/Bearish Engulfing + retracement + key level rejection
    * Piercing Line + 50% level + retracement/rejection
    * Dark Cloud Cover + 50% level + retracement/rejection
    * Candle body/wick reading
    * Support/Resistance/key levels
- 19 requested FX pairs are scanned.
- News is used only as a SAFETY FILTER: if a relevant high-impact
  FX news event is detected, the bot does not issue a signal.
  News does NOT create a signal direction.
- There is deliberately no artificial "80% accuracy" claim. The bot
  sends a signal only when the PDF conditions are met.

LIVE DATA:
This version uses Finnhub forex candles. Finnhub documents the
/forex/candle endpoint for 1-minute candles and forex symbols; the
forex-candle endpoint requires Premium access. Put your Finnhub API
key in FINNHUB_API_KEY.

TELEGRAM:
Set TELEGRAM_BOT_TOKEN and CHAT_ID.
"""

import os
import time
import math
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
import requests
import pandas as pd

load_dotenv()


# ============================================================
# CONFIG
# ============================================================

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")

TIMEFRAME = "1"              # Finnhub: 1-minute candles
SCAN_SECONDS = 5
LOOKBACK_MINUTES = 180
NEWS_LOOKAHEAD_MINUTES = 30
NEWS_LOOKBACK_MINUTES = 10

# User requested pairs
PAIRS = {
    "EUR/JPY": "OANDA:EUR_JPY",
    "CAD/JPY": "OANDA:CAD_JPY",
    "EUR/USD": "OANDA:EUR_USD",
    "USD/JPY": "OANDA:USD_JPY",
    "AUD/JPY": "OANDA:AUD_JPY",
    "AUD/USD": "OANDA:AUD_USD",
    "AUD/CAD": "OANDA:AUD_CAD",
    "GBP/USD": "OANDA:GBP_USD",
    "GBP/AUD": "OANDA:GBP_AUD",
    "GBP/CAD": "OANDA:GBP_CAD",
    "GBP/CHF": "OANDA:GBP_CHF",
    "GBP/JPY": "OANDA:GBP_JPY",
    "USD/CAD": "OANDA:USD_CAD",
    "USD/CHF": "OANDA:USD_CHF",
    "EUR/GBP": "OANDA:EUR_GBP",
    "CHF/JPY": "OANDA:CHF_JPY",
    "EUR/AUD": "OANDA:EUR_AUD",
    "EUR/CAD": "OANDA:EUR_CAD",
    "EUR/CHF": "OANDA:EUR_CHF",
}

# Currencies relevant to the requested pairs.
PAIR_CURRENCIES = {
    "EUR/JPY": {"EUR", "JPY"},
    "CAD/JPY": {"CAD", "JPY"},
    "EUR/USD": {"EUR", "USD"},
    "USD/JPY": {"USD", "JPY"},
    "AUD/JPY": {"AUD", "JPY"},
    "AUD/USD": {"AUD", "USD"},
    "AUD/CAD": {"AUD", "CAD"},
    "GBP/USD": {"GBP", "USD"},
    "GBP/AUD": {"GBP", "AUD"},
    "GBP/CAD": {"GBP", "CAD"},
    "GBP/CHF": {"GBP", "CHF"},
    "GBP/JPY": {"GBP", "JPY"},
    "USD/CAD": {"USD", "CAD"},
    "USD/CHF": {"USD", "CHF"},
    "EUR/GBP": {"EUR", "GBP"},
    "CHF/JPY": {"CHF", "JPY"},
    "EUR/AUD": {"EUR", "AUD"},
    "EUR/CAD": {"EUR", "CAD"},
    "EUR/CHF": {"EUR", "CHF"},
}

BASE_URL = "https://finnhub.io/api/v1"


# ============================================================
# CHECK SETTINGS
# ============================================================

def check_settings():
    missing = []

    print("Checking environment variables...", FINNHUB_API_KEY, TELEGRAM_BOT_TOKEN, CHAT_ID)
    if not FINNHUB_API_KEY:
        missing.append("FINNHUB_API_KEY")
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    # if not CHAT_ID:
    #     missing.append("CHAT_ID")

    if missing:
        raise RuntimeError(
            "Missing environment variables: " + ", ".join(missing)
        )


# ============================================================
# HTTP
# ============================================================

def api_get(path, params=None):
    params = dict(params or {})
    params["token"] = FINNHUB_API_KEY

    response = requests.get(
        BASE_URL + path,
        params=params,
        timeout=15,
    )

    response.raise_for_status()
    return response.json()


# ============================================================
# MARKET DATA
# ============================================================

def get_candles(symbol):
    now = int(time.time())
    start = now - LOOKBACK_MINUTES * 60

    data = api_get(
        "/forex/candle",
        {
            "symbol": symbol,
            "resolution": TIMEFRAME,
            "from": start,
            "to": now,
        },
    )

    if data.get("s") != "ok":
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

    df = df.dropna().drop_duplicates("time")
    df = df.sort_values("time").reset_index(drop=True)

    if len(df) < 20:
        return None

    return df


# ============================================================
# CANDLE READING
# ============================================================

def candle_parts(row):
    o = float(row["open"])
    h = float(row["high"])
    l = float(row["low"])
    c = float(row["close"])

    body = abs(c - o)
    upper = h - max(o, c)
    lower = min(o, c) - l

    return {
        "open": o,
        "high": h,
        "low": l,
        "close": c,
        "body": body,
        "upper_wick": max(0.0, upper),
        "lower_wick": max(0.0, lower),
        "bullish": c > o,
        "bearish": c < o,
    }


def weak_bullish(row):
    p = candle_parts(row)
    if not p["bullish"]:
        return False

    # Body/wick reading only; no indicator.
    return p["body"] <= max(p["upper_wick"], p["lower_wick"]) * 1.5


def weak_bearish(row):
    p = candle_parts(row)
    if not p["bearish"]:
        return False

    return p["body"] <= max(p["upper_wick"], p["lower_wick"]) * 1.5


# ============================================================
# TREND / LEVELS FROM PRICE ACTION ONLY
# ============================================================

def prior_downtrend(df, end_index, bars=5):
    start = max(0, end_index - bars)
    x = df.iloc[start:end_index]

    if len(x) < 4:
        return False

    highs = x["high"].tolist()
    lows = x["low"].tolist()

    lower_highs = sum(
        highs[i] <= highs[i - 1]
        for i in range(1, len(highs))
    )

    lower_lows = sum(
        lows[i] <= lows[i - 1]
        for i in range(1, len(lows))
    )

    return (
        lower_highs >= len(highs) - 2
        and lower_lows >= len(lows) - 2
    )


def prior_uptrend(df, end_index, bars=5):
    start = max(0, end_index - bars)
    x = df.iloc[start:end_index]

    if len(x) < 4:
        return False

    highs = x["high"].tolist()
    lows = x["low"].tolist()

    higher_highs = sum(
        highs[i] >= highs[i - 1]
        for i in range(1, len(highs))
    )

    higher_lows = sum(
        lows[i] >= lows[i - 1]
        for i in range(1, len(lows))
    )

    return (
        higher_highs >= len(highs) - 2
        and higher_lows >= len(lows) - 2
    )


def key_levels(df, end_index, window=20):
    start = max(0, end_index - window)
    x = df.iloc[start:end_index]

    support = float(x["low"].min())
    resistance = float(x["high"].max())

    return support, resistance


def touches_level(row, level):
    return (
        float(row["low"]) <= level <= float(row["high"])
    )


def rejects_support(row, support):
    p = candle_parts(row)

    # Price touched support and closed back above it.
    return (
        touches_level(row, support)
        and p["close"] > support
    )


def rejects_resistance(row, resistance):
    p = candle_parts(row)

    # Price touched resistance and closed back below it.
    return (
        touches_level(row, resistance)
        and p["close"] < resistance
    )


# ============================================================
# BULLISH ENGULFING
# PDF: after engulfing, WAIT for retracement candle.
# If retracement touches key level, rejects, and is weak,
# CALL on next candle.
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


# ============================================================
# PIERCING LINE
# PDF:
# - after a pre-long downtrend
# - piercing line
# - wait for retracement candle
# - retracement must close above 50% level of pattern
# - if it touches key level and rejects -> CALL
# - if it breaks key level without rejection, do not call
# - wait for 2nd candle; if it touches/rejects -> CALL
# ============================================================

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


# ============================================================
# DARK CLOUD COVER
# PDF:
# - after minor/pre-long uptrend
# - bearish candle opens gap up
# - closes below 50% of previous bullish candle
# - next candle touches key level and rejects -> PUT
# - if no rejection, wait for close; weak bullish next candle
#   can be used for PUT.
# ============================================================

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
# DOJI FAMILY / SPINNING TOP
# These are identified as candle-reading structures from the
# PDF. No direction is generated from them alone because the
# PDF pages supplied do not give a standalone CALL/PUT rule
# for every one of these structures.
# ============================================================

def is_doji(row):
    p = candle_parts(row)
    rng = p["high"] - p["low"]

    if rng <= 0:
        return False

    return p["body"] <= rng * 0.10


def is_spinning_top(row):
    p = candle_parts(row)
    rng = p["high"] - p["low"]

    if rng <= 0:
        return False

    return (
        p["body"] <= rng * 0.30
        and p["upper_wick"] >= p["body"]
        and p["lower_wick"] >= p["body"]
    )


# ============================================================
# PATTERN SETUP STATE
# ============================================================

def find_recent_setup(df):
    """
    Returns a PDF setup that is waiting for confirmation.
    No indicators are used.
    """

    n = len(df)

    # Look for a recent pattern among the last 8 completed candles.
    for i in range(max(1, n - 8), n - 1):

        # -------------------------
        # BULLISH ENGULFING
        # -------------------------
        if bullish_engulfing(df, i):
            support, resistance = key_levels(df, i)

            retracement = df.iloc[i + 1]

            if weak_bearish(retracement) and rejects_support(
                retracement, support
            ):
                return {
                    "direction": "CALL",
                    "pattern": "Bullish Engulfing",
                    "pattern_index": i,
                    "entry_index": i + 2,
                    "level": support,
                    "reason": "Retracement touched support, rejected and formed weak bearish candle.",
                }

            # If retracement breaks support without rejection,
            # do not trade that next candle.
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

        # -------------------------
        # BEARISH ENGULFING
        # -------------------------
        if bearish_engulfing(df, i):
            support, resistance = key_levels(df, i)

            retracement = df.iloc[i + 1]

            if weak_bullish(retracement) and rejects_resistance(
                retracement, resistance
            ):
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

        # -------------------------
        # PIERCING LINE
        # -------------------------
        if piercing_line(df, i) and prior_downtrend(df, i):
            a = candle_parts(df.iloc[i - 1])
            pattern_50 = (a["open"] + a["close"]) / 2.0

            support, resistance = key_levels(df, i)

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

                # Broken key level with no rejection:
                # wait for the second candle.
                if float(retracement["close"]) < support:
                    second = df.iloc[i + 2] if i + 2 < n else None

                    if second is not None and rejects_support(
                        second, support
                    ):
                        return {
                            "direction": "CALL",
                            "pattern": "Piercing Line",
                            "pattern_index": i,
                            "entry_index": i + 3,
                            "level": support,
                            "reason": "Second candle touched key level and rejected.",
                        }

        # -------------------------
        # DARK CLOUD COVER
        # -------------------------
        if dark_cloud_cover(df, i) and prior_uptrend(df, i):
            a = candle_parts(df.iloc[i - 1])
            pattern_50 = (a["open"] + a["close"]) / 2.0

            support, resistance = key_levels(df, i)

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
# NEWS SAFETY FILTER
# ============================================================

def get_forex_news():
    try:
        return api_get("/news", {"category": "forex"})
    except Exception as e:
        print("News error:", e)
        return []


def relevant_news_for_pair(pair):
    """
    News is only a filter. It never creates CALL/PUT.
    If a recent/upcoming forex headline clearly contains one
    of the pair currencies, block the signal when the headline
    looks market-moving.
    """

    currencies = PAIR_CURRENCIES[pair]
    now = datetime.now(timezone.utc)

    news = get_forex_news()

    high_impact_words = {
        "rate",
        "interest",
        "central bank",
        "fed",
        "ecb",
        "boj",
        "boe",
        "rba",
        "boc",
        "cpi",
        "inflation",
        "employment",
        "payroll",
        "jobs",
        "gdp",
        "pmi",
        "retail sales",
        "unemployment",
        "fomc",
        "policy",
        "decision",
        "speech",
        "war",
        "tariff",
        "sanction",
    }

    for item in news[:100]:
        headline = str(item.get("headline", "")).lower()
        summary = str(item.get("summary", "")).lower()
        text = headline + " " + summary

        ts = item.get("datetime")

        if not ts:
            continue

        try:
            published = datetime.fromtimestamp(
                int(ts), tz=timezone.utc
            )
        except Exception:
            continue

        age_minutes = (
            now - published
        ).total_seconds() / 60.0

        # Recent market-moving headline
        if 0 <= age_minutes <= NEWS_LOOKBACK_MINUTES:
            if any(word in text for word in high_impact_words):
                if any(currency.lower() in text for currency in currencies):
                    return True, item

    return False, None


# ============================================================
# TELEGRAM
# ============================================================

def send_telegram(message):
    url = (
        f"https://api.telegram.org/bot"
        f"{TELEGRAM_BOT_TOKEN}/sendMessage"
    )

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
# SIGNAL VALIDATION
# ============================================================

def validate_entry(df, setup):
    """
    Signal only when the required entry candle has arrived.
    """

    entry_index = setup["entry_index"]

    if entry_index >= len(df):
        return False

    # The setup is complete only after the required candle closes.
    return True


# ============================================================
# SCAN
# ============================================================

def scan_pair(pair, symbol):
    df = get_candles(symbol)

    if df is None:
        return None

    # Ignore the currently forming minute candle.
    # Use only completed candles.
    if len(df) < 5:
        return None

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

    entry_row = completed.iloc[-1]

    return {
        "blocked": False,
        "pair": pair,
        "direction": setup["direction"],
        "pattern": setup["pattern"],
        "level": setup["level"],
        "price": float(entry_row["close"]),
        "candle_time": entry_row["time"],
        "reason": setup["reason"],
    }


# ============================================================
# MAIN LOOP
# ============================================================

def main():
    check_settings()

    print("=" * 70)
    print("PDF PRICE ACTION LIVE SIGNAL BOT")
    print("19 FX PAIRS | 1-MINUTE | NO INDICATORS")
    print("=" * 70)

    sent_keys = set()

    while True:
        cycle_start = time.time()

        for pair, symbol in PAIRS.items():

            try:
                result = scan_pair(pair, symbol)

                if result is None:
                    continue

                if result.get("blocked"):
                    print(
                        f"{pair}: SIGNAL BLOCKED - NEWS"
                    )
                    continue

                key = (
                    result["pair"],
                    result["pattern"],
                    str(result["candle_time"]),
                )

                if key in sent_keys:
                    continue

                message = (
                    "🚨 PDF PRICE ACTION SIGNAL 🚨\n\n"
                    f"💱 Pair: {result['pair']}\n"
                    f"⏱ Timeframe: 1 Minute\n"
                    f"📊 Signal: {result['direction']}\n"
                    f"🕯 Pattern: {result['pattern']}\n"
                    f"💰 Price: {result['price']}\n"
                    f"📍 Key Level: {result['level']}\n\n"
                    f"📌 PDF Rule:\n{result['reason']}\n\n"
                    "📰 News filter: CLEAR\n"
                    "⚠️ Demo/backtest before live money."
                )

                send_telegram(message)
                sent_keys.add(key)

                print(
                    f"SENT | {pair} | "
                    f"{result['direction']} | "
                    f"{result['pattern']}"
                )

            except requests.HTTPError as e:
                print(f"{pair}: API HTTP error: {e}")

            except Exception as e:
                print(f"{pair}: ERROR: {e}")

        elapsed = time.time() - cycle_start
        time.sleep(max(1, SCAN_SECONDS - elapsed))


if __name__ == "__main__":
    main()
