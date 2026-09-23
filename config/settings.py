"""
config.settings
~~~~~~~~~~~~~~~
Unified environment and asset configuration loader.
Reads settings from .env with fallback defaults.
"""

import os
from typing import Dict, Set
from dotenv import load_dotenv

load_dotenv()

# TradingView Settings
TRADINGVIEW_USERNAME = os.getenv("TRADINGVIEW_USERNAME", "")
TRADINGVIEW_PASSWORD = os.getenv("TRADINGVIEW_PASSWORD", "")

# News Filter (Finnhub) Settings
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
FINNHUB_BASE_URL = os.getenv("FINNHUB_BASE_URL", "https://finnhub.io/api/v1")
NEWS_LOOKBACK_MINUTES = int(os.getenv("NEWS_LOOKBACK_MINUTES", "10"))
NEWS_CACHE_TTL = int(os.getenv("NEWS_CACHE_TTL", "60"))

# Telegram Alert Settings
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")

# Execution Schedule & Rate Limiting
CANDLE_SYNC = os.getenv("CANDLE_SYNC", "true").lower() == "true"
PAIR_REQUEST_DELAY = float(os.getenv("PAIR_REQUEST_DELAY", "0.8"))
SCAN_INTERVAL_SECONDS = int(os.getenv("SCAN_INTERVAL_SECONDS", "60"))
LOOKBACK_MINUTES = int(os.getenv("LOOKBACK_MINUTES", "180"))

# Monitored Currency Pairs (Forex on FX_IDC)
PAIRS: Dict[str, Dict[str, str]] = {
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

PAIR_CURRENCIES: Dict[str, Set[str]] = {pair: set(pair.split("/")) for pair in PAIRS}
