"""
config.settings
~~~~~~~~~~~~~~~
Unified environment and asset configuration loader.
Reads settings from .env with fallback defaults.
"""

import os
from typing import Dict, Set, List
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

# Telegram Alert Settings (Supports single or multiple comma/space separated chat IDs)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
raw_chat_ids = os.getenv("CHAT_IDS", os.getenv("CHAT_ID", ""))
CHAT_IDS = [cid.strip() for cid in raw_chat_ids.replace(";", ",").split(",") if cid.strip()]
CHAT_ID = CHAT_IDS[0] if CHAT_IDS else ""

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

# =========================================================================
# Indian Market Configurations (NSE / BSE Equities & Indices)
# =========================================================================
INDIAN_MARKET_TIMEZONE = os.getenv("INDIAN_MARKET_TIMEZONE", "Asia/Kolkata")
INDIAN_TIMEZONE = INDIAN_MARKET_TIMEZONE
INDIAN_DEFAULT_EXCHANGE = os.getenv("INDIAN_DEFAULT_EXCHANGE", "NSE")

# Market Session Timing
INDIAN_PRE_MARKET_OPEN = (9, 0)
INDIAN_PRE_MARKET_CLOSE = (9, 15)
INDIAN_NORMAL_MARKET_OPEN = (9, 15)
INDIAN_NORMAL_MARKET_CLOSE = (15, 30)
INDIAN_POST_MARKET_CLOSE = (16, 0)

# Major Indian Benchmark and Sectoral Indices
# Maps canonical index key -> Symbol, Exchange, Name, TradingView symbol
INDIAN_INDEXES: Dict[str, Dict[str, str]] = {
    # Major Benchmarks
    "NIFTY": {
        "symbol": "NIFTY",
        "exchange": "NSE",
        "name": "NIFTY 50",
        "tv_symbol": "NIFTY",
        "description": "NSE Flagship 50 Index",
    },
    "NIFTY50": {
        "symbol": "NIFTY",
        "exchange": "NSE",
        "name": "NIFTY 50",
        "tv_symbol": "NIFTY",
        "description": "NSE Flagship 50 Index",
    },
    "BANKNIFTY": {
        "symbol": "BANKNIFTY",
        "exchange": "NSE",
        "name": "NIFTY BANK",
        "tv_symbol": "BANKNIFTY",
        "description": "Banking Sector Index",
    },
    "FINNIFTY": {
        "symbol": "FINNIFTY",
        "exchange": "NSE",
        "name": "NIFTY FINANCIAL SERVICES",
        "tv_symbol": "FINNIFTY",
        "description": "Financial Services Index",
    },
    "MIDCPNIFTY": {
        "symbol": "MIDCPNIFTY",
        "exchange": "NSE",
        "name": "NIFTY MIDCAP SELECT",
        "tv_symbol": "MIDCPNIFTY",
        "description": "Midcap Select Index",
    },
    "NIFTYNXT50": {
        "symbol": "NIFTYNXT50",
        "exchange": "NSE",
        "name": "NIFTY NEXT 50",
        "tv_symbol": "NIFTYNXT50",
        "description": "Junior Nifty 50 Index",
    },
    "SENSEX": {
        "symbol": "SENSEX",
        "exchange": "BSE",
        "name": "S&P BSE SENSEX",
        "tv_symbol": "SENSEX",
        "description": "BSE 30 Benchmark Index",
    },
    "INDIAVIX": {
        "symbol": "INDIAVIX",
        "exchange": "NSE",
        "name": "INDIA VIX",
        "tv_symbol": "INDIAVIX",
        "description": "Indian Volatility Index (Fear Gauge)",
    },

    # Sectoral Indices
    "NIFTYIT": {
        "symbol": "CNXIT",
        "exchange": "NSE",
        "name": "NIFTY IT",
        "tv_symbol": "CNXIT",
        "description": "Information Technology Sector",
    },
    "NIFTYAUTO": {
        "symbol": "CNXAUTO",
        "exchange": "NSE",
        "name": "NIFTY AUTO",
        "tv_symbol": "CNXAUTO",
        "description": "Automobiles Sector",
    },
    "NIFTYFMCG": {
        "symbol": "CNXFMCG",
        "exchange": "NSE",
        "name": "NIFTY FMCG",
        "tv_symbol": "CNXFMCG",
        "description": "Fast Moving Consumer Goods Sector",
    },
    "NIFTYMETAL": {
        "symbol": "CNXMETAL",
        "exchange": "NSE",
        "name": "NIFTY METAL",
        "tv_symbol": "CNXMETAL",
        "description": "Metals & Mining Sector",
    },
    "NIFTYPHARMA": {
        "symbol": "CNXPHARMA",
        "exchange": "NSE",
        "name": "NIFTY PHARMA",
        "tv_symbol": "CNXPHARMA",
        "description": "Pharmaceuticals & Healthcare Sector",
    },
    "NIFTYREALTY": {
        "symbol": "CNXREALTY",
        "exchange": "NSE",
        "name": "NIFTY REALTY",
        "tv_symbol": "CNXREALTY",
        "description": "Real Estate Sector",
    },
    "NIFTYENERGY": {
        "symbol": "CNXENERGY",
        "exchange": "NSE",
        "name": "NIFTY ENERGY",
        "tv_symbol": "CNXENERGY",
        "description": "Oil, Gas & Power Sector",
    },
    "NIFTYINFRA": {
        "symbol": "CNXINFRA",
        "exchange": "NSE",
        "name": "NIFTY INFRASTRUCTURE",
        "tv_symbol": "CNXINFRA",
        "description": "Infrastructure Sector",
    },
    "NIFTYPSUBANK": {
        "symbol": "CNXPSUBANK",
        "exchange": "NSE",
        "name": "NIFTY PSU BANK",
        "tv_symbol": "CNXPSUBANK",
        "description": "Public Sector Banks",
    },
    "NIFTYPVTBANK": {
        "symbol": "CNXPVTBANK",
        "exchange": "NSE",
        "name": "NIFTY PRIVATE BANK",
        "tv_symbol": "CNXPVTBANK",
        "description": "Private Sector Banks",
    },
}

# Major Liquid Indian Stocks (Top NIFTY 50 Constituents & High-Volume F&O Equities)
INDIAN_STOCKS: Dict[str, Dict[str, str]] = {
    "RELIANCE": {"symbol": "RELIANCE", "exchange": "NSE", "name": "Reliance Industries Ltd", "sector": "Energy"},
    "TCS": {"symbol": "TCS", "exchange": "NSE", "name": "Tata Consultancy Services Ltd", "sector": "IT"},
    "HDFCBANK": {"symbol": "HDFCBANK", "exchange": "NSE", "name": "HDFC Bank Ltd", "sector": "Banking"},
    "INFY": {"symbol": "INFY", "exchange": "NSE", "name": "Infosys Ltd", "sector": "IT"},
    "ICICIBANK": {"symbol": "ICICIBANK", "exchange": "NSE", "name": "ICICI Bank Ltd", "sector": "Banking"},
    "SBIN": {"symbol": "SBIN", "exchange": "NSE", "name": "State Bank of India", "sector": "PSU Banking"},
    "BHARTIARTL": {"symbol": "BHARTIARTL", "exchange": "NSE", "name": "Bharti Airtel Ltd", "sector": "Telecom"},
    "ITC": {"symbol": "ITC", "exchange": "NSE", "name": "ITC Ltd", "sector": "FMCG"},
    "KOTAKBANK": {"symbol": "KOTAKBANK", "exchange": "NSE", "name": "Kotak Mahindra Bank Ltd", "sector": "Banking"},
    "LT": {"symbol": "LT", "exchange": "NSE", "name": "Larsen & Toubro Ltd", "sector": "Infrastructure"},
    "AXISBANK": {"symbol": "AXISBANK", "exchange": "NSE", "name": "Axis Bank Ltd", "sector": "Banking"},
    "HINDUNILVR": {"symbol": "HINDUNILVR", "exchange": "NSE", "name": "Hindustan Unilever Ltd", "sector": "FMCG"},
    "BAJFINANCE": {"symbol": "BAJFINANCE", "exchange": "NSE", "name": "Bajaj Finance Ltd", "sector": "Finance"},
    "MARUTI": {"symbol": "MARUTI", "exchange": "NSE", "name": "Maruti Suzuki India Ltd", "sector": "Automobile"},
    "TATAMOTORS": {"symbol": "TATAMOTORS", "exchange": "NSE", "name": "Tata Motors Ltd", "sector": "Automobile"},
    "SUNPHARMA": {"symbol": "SUNPHARMA", "exchange": "NSE", "name": "Sun Pharmaceutical Industries Ltd", "sector": "Pharma"},
    "TITAN": {"symbol": "TITAN", "exchange": "NSE", "name": "Titan Company Ltd", "sector": "Consumer Durables"},
    "TATASTEEL": {"symbol": "TATASTEEL", "exchange": "NSE", "name": "Tata Steel Ltd", "sector": "Metals"},
    "WIPRO": {"symbol": "WIPRO", "exchange": "NSE", "name": "Wipro Ltd", "sector": "IT"},
    "NTPC": {"symbol": "NTPC", "exchange": "NSE", "name": "NTPC Ltd", "sector": "Power"},
    "ONGC": {"symbol": "ONGC", "exchange": "NSE", "name": "Oil & Natural Gas Corp Ltd", "sector": "Energy"},
    "POWERGRID": {"symbol": "POWERGRID", "exchange": "NSE", "name": "Power Grid Corp of India Ltd", "sector": "Power"},
    "ADANIENT": {"symbol": "ADANIENT", "exchange": "NSE", "name": "Adani Enterprises Ltd", "sector": "Conglomerate"},
    "ADANIPORTS": {"symbol": "ADANIPORTS", "exchange": "NSE", "name": "Adani Ports and SEZ Ltd", "sector": "Infrastructure"},
    "ASIANPAINT": {"symbol": "ASIANPAINT", "exchange": "NSE", "name": "Asian Paints Ltd", "sector": "Paints"},
    "M&M": {"symbol": "M&M", "exchange": "NSE", "name": "Mahindra & Mahindra Ltd", "sector": "Automobile"},
    "BAJAJFINSV": {"symbol": "BAJAJFINSV", "exchange": "NSE", "name": "Bajaj Finserv Ltd", "sector": "Finance"},
    "COALINDIA": {"symbol": "COALINDIA", "exchange": "NSE", "name": "Coal India Ltd", "sector": "Mining"},
    "JSWSTEEL": {"symbol": "JSWSTEEL", "exchange": "NSE", "name": "JSW Steel Ltd", "sector": "Metals"},
    "ULTRACEMCO": {"symbol": "ULTRACEMCO", "exchange": "NSE", "name": "UltraTech Cement Ltd", "sector": "Cement"},
}

# Volatility Index (India VIX) Regime Thresholds
VIX_REGIMES = {
    "LOW": (0.0, 13.0),
    "NORMAL": (13.0, 18.0),
    "ELEVATED": (18.0, 24.0),
    "EXTREME": (24.0, 100.0),
}

# Put-Call Ratio (PCR) Sentiment Ranges
PCR_THRESHOLDS = {
    "OVERSOLD": 0.70,       # Bullish reversal candidate (Short covering zone)
    "NEUTRAL_LOW": 0.70,
    "NEUTRAL_HIGH": 1.30,
    "OVERBOUGHT": 1.30,     # Bearish caution zone (Profit booking / Call writing zone)
    "EXTREME_OVERBOUGHT": 1.60,
}

# Standard Indian Trading Holidays (NSE/BSE for 2026/Calendar)
# Format: YYYY-MM-DD
INDIAN_HOLIDAYS_2026: List[str] = [
    "2026-01-26",  # Republic Day
    "2026-03-03",  # Holi
    "2026-03-20",  # Id-Ul-Fitr (Ramzan Id)
    "2026-04-03",  # Good Friday
    "2026-04-14",  # Dr. Baba Saheb Ambedkar Jayanti
    "2026-05-01",  # Maharashtra Day
    "2026-05-27",  # Bakri Id / Eid-Ul-Adha
    "2026-06-26",  # Muharram
    "2026-08-15",  # Independence Day
    "2026-10-02",  # Mahatma Gandhi Jayanti
    "2026-10-20",  # Dussehra
    "2026-11-08",  # Diwali Laxmi Pujan (Muhurat Trading only)
    "2026-11-10",  # Diwali Balipratipada
    "2026-11-24",  # Gurunanak Jayanti
    "2026-12-25",  # Christmas
]

# =========================================================================
# Backward-Compatible Aliases (for transitional code)
# =========================================================================
INDIAN_STOCKS_WATCHLIST = INDIAN_STOCKS  # Old name used by some modules
INDIAN_INDICES = {v["name"]: {"symbol": v["symbol"], "exchange": v["exchange"]} for k, v in INDIAN_INDEXES.items() if "name" in v}

# Unprefixed timing constants (used by session manager)
PRE_MARKET_OPEN = INDIAN_PRE_MARKET_OPEN
PRE_MARKET_CLOSE = INDIAN_PRE_MARKET_CLOSE
NORMAL_MARKET_OPEN = INDIAN_NORMAL_MARKET_OPEN
NORMAL_MARKET_CLOSE = INDIAN_NORMAL_MARKET_CLOSE
POST_MARKET_CLOSE = INDIAN_POST_MARKET_CLOSE
