"""
txcore.database
~~~~~~~~~~~~~~~
Prisma ORM Client lifecycle, connection manager, and market catalog seeding engine.
Stores Stocks, Indexes, Forexs, Cryptos, and Commodities with their Short Names,
Full Names, Markets, and Index/Exchange groupings for dynamic frontend selection.
"""

import os
import asyncio
import logging
from typing import Optional, List, Dict, Any
from prisma import Prisma

logger = logging.getLogger("txcore.database")

# Global Prisma Client Instance
db = Prisma(auto_register=True)
_db_loop: Optional[asyncio.AbstractEventLoop] = None


async def connect_db():
    """Connects to the database via Prisma ORM, reconnecting if the event loop changed."""
    global _db_loop
    current_loop = asyncio.get_running_loop()

    if db.is_connected():
        if _db_loop is not None and (_db_loop != current_loop or _db_loop.is_closed()):
            try:
                await db.disconnect()
            except Exception:
                pass
            await db.connect()
            _db_loop = current_loop
            logger.info("Prisma database reconnected to new active event loop.")
            return
        return

    logger.info("Connecting to database via Prisma ORM...")
    await db.connect()
    _db_loop = current_loop
    logger.info("Prisma database connection established.")


async def disconnect_db():
    """Gracefully disconnects Prisma ORM client."""
    global _db_loop
    if db.is_connected():
        logger.info("Disconnecting Prisma database client...")
        try:
            await db.disconnect()
        except Exception:
            pass
        _db_loop = None
        logger.info("Prisma database client disconnected.")


# =========================================================================
# 1. SEEDED MARKET GROUPS / BENCHMARK INDEXES
# =========================================================================

SEEDED_MARKET_GROUPS: List[Dict[str, Any]] = [
    {
        "groupId": "NSE",
        "name": "National Stock Exchange of India (NSE)",
        "market": "INDIAN_EQUITY",
        "description": "India's premier exchange covering NIFTY 50, NIFTY Bank, and top bluechips.",
    },
    {
        "groupId": "BSE",
        "name": "Bombay Stock Exchange (BSE)",
        "market": "INDIAN_EQUITY",
        "description": "Asia's oldest exchange home to the S&P BSE SENSEX index.",
    },
    {
        "groupId": "DOW_JONES",
        "name": "Dow Jones Industrial Average (DJIA)",
        "market": "US_EQUITY",
        "description": "The 30 most prominent publicly owned companies trading in the United States.",
    },
    {
        "groupId": "NASDAQ",
        "name": "Nasdaq 100 & Composite",
        "market": "US_EQUITY",
        "description": "Top 100 non-financial companies and global technology leaders.",
    },
    {
        "groupId": "SP500",
        "name": "S&P 500 Index",
        "market": "US_EQUITY",
        "description": "500 leading publicly traded companies in the U.S. market.",
    },
    {
        "groupId": "FOREX",
        "name": "Forex Currency Exchange",
        "market": "FOREX",
        "description": "Global decentralized marketplace for foreign currencies and crosses.",
    },
    {
        "groupId": "CRYPTO",
        "name": "Cryptocurrency Markets",
        "market": "CRYPTO",
        "description": "Leading liquid digital assets and perpetual contract pairs.",
    },
    {
        "groupId": "MCX",
        "name": "Multi Commodity Exchange (MCX)",
        "market": "COMMODITY",
        "description": "India's largest commodity derivatives exchange (Crude Oil, Gold, Silver).",
    },
]


# =========================================================================
# 2. SEEDED STOCKS, INDEXES, CURRENCIES & COMMODITIES
# =========================================================================

SEEDED_MARKET_SYMBOLS: List[Dict[str, Any]] = [
    # -------------------------------------------------------------------------
    # INDIAN BENCHMARK & SECTORAL INDICES (assetType: INDEX)
    # -------------------------------------------------------------------------
    {
        "symbol": "NIFTY",
        "shortName": "NIFTY",
        "fullName": "NIFTY 50 Benchmark Index",
        "market": "INDIAN_FNO",
        "exchange": "NSE",
        "assetType": "INDEX",
        "sector": "INDEX",
        "indexGroup": "NIFTY 50",
        "groupId": "NSE",
        "lotSize": 50,
        "tickSize": 0.05,
        "tvSymbol": "NIFTY",
    },
    {
        "symbol": "BANKNIFTY",
        "shortName": "BANKNIFTY",
        "fullName": "NIFTY Bank Sectoral Index",
        "market": "INDIAN_FNO",
        "exchange": "NSE",
        "assetType": "INDEX",
        "sector": "BANKING",
        "indexGroup": "NIFTY BANK",
        "groupId": "NSE",
        "lotSize": 15,
        "tickSize": 0.05,
        "tvSymbol": "BANKNIFTY",
    },
    {
        "symbol": "FINNIFTY",
        "shortName": "FINNIFTY",
        "fullName": "NIFTY Financial Services Index",
        "market": "INDIAN_FNO",
        "exchange": "NSE",
        "assetType": "INDEX",
        "sector": "FINANCIAL",
        "indexGroup": "FINNIFTY",
        "groupId": "NSE",
        "lotSize": 40,
        "tickSize": 0.05,
        "tvSymbol": "FINNIFTY",
    },
    {
        "symbol": "MIDCPNIFTY",
        "shortName": "MIDCPNIFTY",
        "fullName": "NIFTY Midcap Select Index",
        "market": "INDIAN_FNO",
        "exchange": "NSE",
        "assetType": "INDEX",
        "sector": "INDEX",
        "indexGroup": "MIDCAP",
        "groupId": "NSE",
        "lotSize": 75,
        "tickSize": 0.05,
        "tvSymbol": "MIDCPNIFTY",
    },
    {
        "symbol": "NIFTYIT",
        "shortName": "NIFTYIT",
        "fullName": "NIFTY IT Sectoral Index",
        "market": "INDIAN_FNO",
        "exchange": "NSE",
        "assetType": "INDEX",
        "sector": "IT",
        "indexGroup": "NIFTY IT",
        "groupId": "NSE",
        "lotSize": 25,
        "tickSize": 0.05,
        "tvSymbol": "CNXIT",
    },
    {
        "symbol": "SENSEX",
        "shortName": "SENSEX",
        "fullName": "S&P BSE SENSEX 30 Index",
        "market": "INDIAN_EQUITY",
        "exchange": "BSE",
        "assetType": "INDEX",
        "sector": "INDEX",
        "indexGroup": "SENSEX",
        "groupId": "BSE",
        "lotSize": 10,
        "tickSize": 0.05,
        "tvSymbol": "SENSEX",
    },

    # -------------------------------------------------------------------------
    # INDIAN EQUITIES (NSE Top Constituents)
    # -------------------------------------------------------------------------
    {
        "symbol": "RELIANCE",
        "shortName": "RELIANCE",
        "fullName": "Reliance Industries Limited",
        "market": "INDIAN_EQUITY",
        "exchange": "NSE",
        "assetType": "STOCK",
        "sector": "ENERGY",
        "indexGroup": "NIFTY 50",
        "groupId": "NSE",
        "lotSize": 250,
        "tickSize": 0.05,
        "tvSymbol": "RELIANCE",
    },
    {
        "symbol": "TCS",
        "shortName": "TCS",
        "fullName": "Tata Consultancy Services Limited",
        "market": "INDIAN_EQUITY",
        "exchange": "NSE",
        "assetType": "STOCK",
        "sector": "IT",
        "indexGroup": "NIFTY 50",
        "groupId": "NSE",
        "lotSize": 175,
        "tickSize": 0.05,
        "tvSymbol": "TCS",
    },
    {
        "symbol": "HDFCBANK",
        "shortName": "HDFCBANK",
        "fullName": "HDFC Bank Limited",
        "market": "INDIAN_EQUITY",
        "exchange": "NSE",
        "assetType": "STOCK",
        "sector": "BANKING",
        "indexGroup": "NIFTY 50",
        "groupId": "NSE",
        "lotSize": 550,
        "tickSize": 0.05,
        "tvSymbol": "HDFCBANK",
    },
    {
        "symbol": "INFY",
        "shortName": "INFY",
        "fullName": "Infosys Limited",
        "market": "INDIAN_EQUITY",
        "exchange": "NSE",
        "assetType": "STOCK",
        "sector": "IT",
        "indexGroup": "NIFTY 50",
        "groupId": "NSE",
        "lotSize": 400,
        "tickSize": 0.05,
        "tvSymbol": "INFY",
    },
    {
        "symbol": "ICICIBANK",
        "shortName": "ICICIBANK",
        "fullName": "ICICI Bank Limited",
        "market": "INDIAN_EQUITY",
        "exchange": "NSE",
        "assetType": "STOCK",
        "sector": "BANKING",
        "indexGroup": "NIFTY 50",
        "groupId": "NSE",
        "lotSize": 700,
        "tickSize": 0.05,
        "tvSymbol": "ICICIBANK",
    },
    {
        "symbol": "SBIN",
        "shortName": "SBIN",
        "fullName": "State Bank of India",
        "market": "INDIAN_EQUITY",
        "exchange": "NSE",
        "assetType": "STOCK",
        "sector": "BANKING",
        "indexGroup": "NIFTY 50",
        "groupId": "NSE",
        "lotSize": 750,
        "tickSize": 0.05,
        "tvSymbol": "SBIN",
    },
    {
        "symbol": "BHARTIARTL",
        "shortName": "BHARTIARTL",
        "fullName": "Bharti Airtel Limited",
        "market": "INDIAN_EQUITY",
        "exchange": "NSE",
        "assetType": "STOCK",
        "sector": "TELECOM",
        "indexGroup": "NIFTY 50",
        "groupId": "NSE",
        "lotSize": 475,
        "tickSize": 0.05,
        "tvSymbol": "BHARTIARTL",
    },
    {
        "symbol": "ITC",
        "shortName": "ITC",
        "fullName": "ITC Limited",
        "market": "INDIAN_EQUITY",
        "exchange": "NSE",
        "assetType": "STOCK",
        "sector": "FMCG",
        "indexGroup": "NIFTY 50",
        "groupId": "NSE",
        "lotSize": 1600,
        "tickSize": 0.05,
        "tvSymbol": "ITC",
    },
    {
        "symbol": "LT",
        "shortName": "LT",
        "fullName": "Larsen & Toubro Limited",
        "market": "INDIAN_EQUITY",
        "exchange": "NSE",
        "assetType": "STOCK",
        "sector": "INFRASTRUCTURE",
        "indexGroup": "NIFTY 50",
        "groupId": "NSE",
        "lotSize": 175,
        "tickSize": 0.05,
        "tvSymbol": "LT",
    },
    {
        "symbol": "TATAMOTORS",
        "shortName": "TATAMOTORS",
        "fullName": "Tata Motors Limited",
        "market": "INDIAN_EQUITY",
        "exchange": "NSE",
        "assetType": "STOCK",
        "sector": "AUTO",
        "indexGroup": "NIFTY 50",
        "groupId": "NSE",
        "lotSize": 1425,
        "tickSize": 0.05,
        "tvSymbol": "TATAMOTORS",
    },
    {
        "symbol": "KOTAKBANK",
        "shortName": "KOTAKBANK",
        "fullName": "Kotak Mahindra Bank Limited",
        "market": "INDIAN_EQUITY",
        "exchange": "NSE",
        "assetType": "STOCK",
        "sector": "BANKING",
        "indexGroup": "NIFTY 50",
        "groupId": "NSE",
        "lotSize": 400,
        "tickSize": 0.05,
        "tvSymbol": "KOTAKBANK",
    },
    {
        "symbol": "AXISBANK",
        "shortName": "AXISBANK",
        "fullName": "Axis Bank Limited",
        "market": "INDIAN_EQUITY",
        "exchange": "NSE",
        "assetType": "STOCK",
        "sector": "BANKING",
        "indexGroup": "NIFTY 50",
        "groupId": "NSE",
        "lotSize": 625,
        "tickSize": 0.05,
        "tvSymbol": "AXISBANK",
    },
    {
        "symbol": "MARUTI",
        "shortName": "MARUTI",
        "fullName": "Maruti Suzuki India Limited",
        "market": "INDIAN_EQUITY",
        "exchange": "NSE",
        "assetType": "STOCK",
        "sector": "AUTO",
        "indexGroup": "NIFTY 50",
        "groupId": "NSE",
        "lotSize": 50,
        "tickSize": 0.05,
        "tvSymbol": "MARUTI",
    },
    {
        "symbol": "SUNPHARMA",
        "shortName": "SUNPHARMA",
        "fullName": "Sun Pharmaceutical Industries Limited",
        "market": "INDIAN_EQUITY",
        "exchange": "NSE",
        "assetType": "STOCK",
        "sector": "PHARMA",
        "indexGroup": "NIFTY 50",
        "groupId": "NSE",
        "lotSize": 700,
        "tickSize": 0.05,
        "tvSymbol": "SUNPHARMA",
    },
    {
        "symbol": "BAJFINANCE",
        "shortName": "BAJFINANCE",
        "fullName": "Bajaj Finance Limited",
        "market": "INDIAN_EQUITY",
        "exchange": "NSE",
        "assetType": "STOCK",
        "sector": "FINANCIAL",
        "indexGroup": "NIFTY 50",
        "groupId": "NSE",
        "lotSize": 125,
        "tickSize": 0.05,
        "tvSymbol": "BAJFINANCE",
    },
    {
        "symbol": "TITAN",
        "shortName": "TITAN",
        "fullName": "Titan Company Limited",
        "market": "INDIAN_EQUITY",
        "exchange": "NSE",
        "assetType": "STOCK",
        "sector": "CONSUMER",
        "indexGroup": "NIFTY 50",
        "groupId": "NSE",
        "lotSize": 175,
        "tickSize": 0.05,
        "tvSymbol": "TITAN",
    },
    {
        "symbol": "ASIANPAINT",
        "shortName": "ASIANPAINT",
        "fullName": "Asian Paints Limited",
        "market": "INDIAN_EQUITY",
        "exchange": "NSE",
        "assetType": "STOCK",
        "sector": "CONSUMER",
        "indexGroup": "NIFTY 50",
        "groupId": "NSE",
        "lotSize": 200,
        "tickSize": 0.05,
        "tvSymbol": "ASIANPAINT",
    },

    # -------------------------------------------------------------------------
    # US BENCHMARK INDICES (assetType: INDEX)
    # -------------------------------------------------------------------------
    {
        "symbol": "DJI",
        "shortName": "DJI",
        "fullName": "Dow Jones Industrial Average",
        "market": "US_EQUITY",
        "exchange": "DJI",
        "assetType": "INDEX",
        "sector": "INDEX",
        "indexGroup": "DOW JONES",
        "groupId": "DOW_JONES",
        "lotSize": 1,
        "tickSize": 0.01,
        "tvSymbol": "DJI",
    },
    {
        "symbol": "IXIC",
        "shortName": "NASDAQ",
        "fullName": "Nasdaq Composite Index",
        "market": "US_EQUITY",
        "exchange": "NASDAQ",
        "assetType": "INDEX",
        "sector": "INDEX",
        "indexGroup": "NASDAQ 100",
        "groupId": "NASDAQ",
        "lotSize": 1,
        "tickSize": 0.01,
        "tvSymbol": "IXIC",
    },
    {
        "symbol": "GSPC",
        "shortName": "SP500",
        "fullName": "S&P 500 Benchmark Index",
        "market": "US_EQUITY",
        "exchange": "SPX",
        "assetType": "INDEX",
        "sector": "INDEX",
        "indexGroup": "S&P 500",
        "groupId": "SP500",
        "lotSize": 1,
        "tickSize": 0.01,
        "tvSymbol": "SPX",
    },

    # -------------------------------------------------------------------------
    # US EQUITIES (Dow Jones & Nasdaq Constituents)
    # -------------------------------------------------------------------------
    {
        "symbol": "AAPL",
        "shortName": "AAPL",
        "fullName": "Apple Inc.",
        "market": "US_EQUITY",
        "exchange": "NASDAQ",
        "assetType": "STOCK",
        "sector": "TECHNOLOGY",
        "indexGroup": "DOW JONES",
        "groupId": "DOW_JONES",
        "lotSize": 1,
        "tickSize": 0.01,
        "tvSymbol": "AAPL",
    },
    {
        "symbol": "MSFT",
        "shortName": "MSFT",
        "fullName": "Microsoft Corporation",
        "market": "US_EQUITY",
        "exchange": "NASDAQ",
        "assetType": "STOCK",
        "sector": "TECHNOLOGY",
        "indexGroup": "DOW JONES",
        "groupId": "DOW_JONES",
        "lotSize": 1,
        "tickSize": 0.01,
        "tvSymbol": "MSFT",
    },
    {
        "symbol": "BA",
        "shortName": "BA",
        "fullName": "The Boeing Company",
        "market": "US_EQUITY",
        "exchange": "NYSE",
        "assetType": "STOCK",
        "sector": "AEROSPACE",
        "indexGroup": "DOW JONES",
        "groupId": "DOW_JONES",
        "lotSize": 1,
        "tickSize": 0.01,
        "tvSymbol": "BA",
    },
    {
        "symbol": "GS",
        "shortName": "GS",
        "fullName": "The Goldman Sachs Group, Inc.",
        "market": "US_EQUITY",
        "exchange": "NYSE",
        "assetType": "STOCK",
        "sector": "FINANCIAL",
        "indexGroup": "DOW JONES",
        "groupId": "DOW_JONES",
        "lotSize": 1,
        "tickSize": 0.01,
        "tvSymbol": "GS",
    },
    {
        "symbol": "MCD",
        "shortName": "MCD",
        "fullName": "McDonald's Corporation",
        "market": "US_EQUITY",
        "exchange": "NYSE",
        "assetType": "STOCK",
        "sector": "CONSUMER",
        "indexGroup": "DOW JONES",
        "groupId": "DOW_JONES",
        "lotSize": 1,
        "tickSize": 0.01,
        "tvSymbol": "MCD",
    },
    {
        "symbol": "KO",
        "shortName": "KO",
        "fullName": "The Coca-Cola Company",
        "market": "US_EQUITY",
        "exchange": "NYSE",
        "assetType": "STOCK",
        "sector": "BEVERAGES",
        "indexGroup": "DOW JONES",
        "groupId": "DOW_JONES",
        "lotSize": 1,
        "tickSize": 0.01,
        "tvSymbol": "KO",
    },
    {
        "symbol": "JPM",
        "shortName": "JPM",
        "fullName": "JPMorgan Chase & Co.",
        "market": "US_EQUITY",
        "exchange": "NYSE",
        "assetType": "STOCK",
        "sector": "FINANCIAL",
        "indexGroup": "DOW JONES",
        "groupId": "DOW_JONES",
        "lotSize": 1,
        "tickSize": 0.01,
        "tvSymbol": "JPM",
    },
    {
        "symbol": "NVDA",
        "shortName": "NVDA",
        "fullName": "NVIDIA Corporation",
        "market": "US_EQUITY",
        "exchange": "NASDAQ",
        "assetType": "STOCK",
        "sector": "SEMICONDUCTORS",
        "indexGroup": "NASDAQ 100",
        "groupId": "NASDAQ",
        "lotSize": 1,
        "tickSize": 0.01,
        "tvSymbol": "NVDA",
    },
    {
        "symbol": "AMZN",
        "shortName": "AMZN",
        "fullName": "Amazon.com, Inc.",
        "market": "US_EQUITY",
        "exchange": "NASDAQ",
        "assetType": "STOCK",
        "sector": "CONSUMER_TECH",
        "indexGroup": "NASDAQ 100",
        "groupId": "NASDAQ",
        "lotSize": 1,
        "tickSize": 0.01,
        "tvSymbol": "AMZN",
    },
    {
        "symbol": "GOOGL",
        "shortName": "GOOGL",
        "fullName": "Alphabet Inc. (Google)",
        "market": "US_EQUITY",
        "exchange": "NASDAQ",
        "assetType": "STOCK",
        "sector": "COMMUNICATION",
        "indexGroup": "NASDAQ 100",
        "groupId": "NASDAQ",
        "lotSize": 1,
        "tickSize": 0.01,
        "tvSymbol": "GOOGL",
    },
    {
        "symbol": "META",
        "shortName": "META",
        "fullName": "Meta Platforms, Inc.",
        "market": "US_EQUITY",
        "exchange": "NASDAQ",
        "assetType": "STOCK",
        "sector": "COMMUNICATION",
        "indexGroup": "NASDAQ 100",
        "groupId": "NASDAQ",
        "lotSize": 1,
        "tickSize": 0.01,
        "tvSymbol": "META",
    },
    {
        "symbol": "TSLA",
        "shortName": "TSLA",
        "fullName": "Tesla, Inc.",
        "market": "US_EQUITY",
        "exchange": "NASDAQ",
        "assetType": "STOCK",
        "sector": "AUTO",
        "indexGroup": "NASDAQ 100",
        "groupId": "NASDAQ",
        "lotSize": 1,
        "tickSize": 0.01,
        "tvSymbol": "TSLA",
    },
    {
        "symbol": "AMD",
        "shortName": "AMD",
        "fullName": "Advanced Micro Devices, Inc.",
        "market": "US_EQUITY",
        "exchange": "NASDAQ",
        "assetType": "STOCK",
        "sector": "SEMICONDUCTORS",
        "indexGroup": "NASDAQ 100",
        "groupId": "NASDAQ",
        "lotSize": 1,
        "tickSize": 0.01,
        "tvSymbol": "AMD",
    },
    {
        "symbol": "NFLX",
        "shortName": "NFLX",
        "fullName": "Netflix, Inc.",
        "market": "US_EQUITY",
        "exchange": "NASDAQ",
        "assetType": "STOCK",
        "sector": "ENTERTAINMENT",
        "indexGroup": "NASDAQ 100",
        "groupId": "NASDAQ",
        "lotSize": 1,
        "tickSize": 0.01,
        "tvSymbol": "NFLX",
    },

    # -------------------------------------------------------------------------
    # FOREX CURRENCY PAIRS (assetType: CURRENCY)
    # -------------------------------------------------------------------------
    {
        "symbol": "EUR/USD",
        "shortName": "EURUSD",
        "fullName": "Euro / US Dollar",
        "market": "FOREX",
        "exchange": "FX_IDC",
        "assetType": "CURRENCY",
        "sector": "MAJORS",
        "indexGroup": "FOREX MAJORS",
        "groupId": "FOREX",
        "lotSize": 100000,
        "tickSize": 0.00001,
        "tvSymbol": "EURUSD",
    },
    {
        "symbol": "GBP/USD",
        "shortName": "GBPUSD",
        "fullName": "British Pound / US Dollar",
        "market": "FOREX",
        "exchange": "FX_IDC",
        "assetType": "CURRENCY",
        "sector": "MAJORS",
        "indexGroup": "FOREX MAJORS",
        "groupId": "FOREX",
        "lotSize": 100000,
        "tickSize": 0.00001,
        "tvSymbol": "GBPUSD",
    },
    {
        "symbol": "USD/JPY",
        "shortName": "USDJPY",
        "fullName": "US Dollar / Japanese Yen",
        "market": "FOREX",
        "exchange": "FX_IDC",
        "assetType": "CURRENCY",
        "sector": "MAJORS",
        "indexGroup": "FOREX MAJORS",
        "groupId": "FOREX",
        "lotSize": 100000,
        "tickSize": 0.001,
        "tvSymbol": "USDJPY",
    },
    {
        "symbol": "USD/CAD",
        "shortName": "USDCAD",
        "fullName": "US Dollar / Canadian Dollar",
        "market": "FOREX",
        "exchange": "FX_IDC",
        "assetType": "CURRENCY",
        "sector": "MAJORS",
        "indexGroup": "FOREX MAJORS",
        "groupId": "FOREX",
        "lotSize": 100000,
        "tickSize": 0.00001,
        "tvSymbol": "USDCAD",
    },
    {
        "symbol": "AUD/USD",
        "shortName": "AUDUSD",
        "fullName": "Australian Dollar / US Dollar",
        "market": "FOREX",
        "exchange": "FX_IDC",
        "assetType": "CURRENCY",
        "sector": "MAJORS",
        "indexGroup": "FOREX MAJORS",
        "groupId": "FOREX",
        "lotSize": 100000,
        "tickSize": 0.00001,
        "tvSymbol": "AUDUSD",
    },
    {
        "symbol": "USD/CHF",
        "shortName": "USDCHF",
        "fullName": "US Dollar / Swiss Franc",
        "market": "FOREX",
        "exchange": "FX_IDC",
        "assetType": "CURRENCY",
        "sector": "MAJORS",
        "indexGroup": "FOREX MAJORS",
        "groupId": "FOREX",
        "lotSize": 100000,
        "tickSize": 0.00001,
        "tvSymbol": "USDCHF",
    },
    {
        "symbol": "EUR/GBP",
        "shortName": "EURGBP",
        "fullName": "Euro / British Pound",
        "market": "FOREX",
        "exchange": "FX_IDC",
        "assetType": "CURRENCY",
        "sector": "CROSSES",
        "indexGroup": "FOREX CROSSES",
        "groupId": "FOREX",
        "lotSize": 100000,
        "tickSize": 0.00001,
        "tvSymbol": "EURGBP",
    },
    {
        "symbol": "EUR/JPY",
        "shortName": "EURJPY",
        "fullName": "Euro / Japanese Yen",
        "market": "FOREX",
        "exchange": "FX_IDC",
        "assetType": "CURRENCY",
        "sector": "CROSSES",
        "indexGroup": "FOREX CROSSES",
        "groupId": "FOREX",
        "lotSize": 100000,
        "tickSize": 0.001,
        "tvSymbol": "EURJPY",
    },
    {
        "symbol": "GBP/JPY",
        "shortName": "GBPJPY",
        "fullName": "British Pound / Japanese Yen",
        "market": "FOREX",
        "exchange": "FX_IDC",
        "assetType": "CURRENCY",
        "sector": "CROSSES",
        "indexGroup": "FOREX CROSSES",
        "groupId": "FOREX",
        "lotSize": 100000,
        "tickSize": 0.001,
        "tvSymbol": "GBPJPY",
    },
    {
        "symbol": "CAD/JPY",
        "shortName": "CADJPY",
        "fullName": "Canadian Dollar / Japanese Yen",
        "market": "FOREX",
        "exchange": "FX_IDC",
        "assetType": "CURRENCY",
        "sector": "CROSSES",
        "indexGroup": "FOREX CROSSES",
        "groupId": "FOREX",
        "lotSize": 100000,
        "tickSize": 0.001,
        "tvSymbol": "CADJPY",
    },

    # -------------------------------------------------------------------------
    # CRYPTOCURRENCY ASSETS (assetType: CRYPTO)
    # -------------------------------------------------------------------------
    {
        "symbol": "BTC/USDT",
        "shortName": "BTCUSDT",
        "fullName": "Bitcoin / Tether USD",
        "market": "CRYPTO",
        "exchange": "BINANCE",
        "assetType": "CRYPTO",
        "sector": "LAYER_1",
        "indexGroup": "CRYPTO TOP",
        "groupId": "CRYPTO",
        "lotSize": 1,
        "tickSize": 0.01,
        "tvSymbol": "BTCUSDT",
    },
    {
        "symbol": "ETH/USDT",
        "shortName": "ETHUSDT",
        "fullName": "Ethereum / Tether USD",
        "market": "CRYPTO",
        "exchange": "BINANCE",
        "assetType": "CRYPTO",
        "sector": "SMART_CONTRACTS",
        "indexGroup": "CRYPTO TOP",
        "groupId": "CRYPTO",
        "lotSize": 1,
        "tickSize": 0.01,
        "tvSymbol": "ETHUSDT",
    },
    {
        "symbol": "SOL/USDT",
        "shortName": "SOLUSDT",
        "fullName": "Solana / Tether USD",
        "market": "CRYPTO",
        "exchange": "BINANCE",
        "assetType": "CRYPTO",
        "sector": "HIGH_SPEED_L1",
        "indexGroup": "CRYPTO TOP",
        "groupId": "CRYPTO",
        "lotSize": 1,
        "tickSize": 0.01,
        "tvSymbol": "SOLUSDT",
    },
    {
        "symbol": "BNB/USDT",
        "shortName": "BNBUSDT",
        "fullName": "BNB / Tether USD",
        "market": "CRYPTO",
        "exchange": "BINANCE",
        "assetType": "CRYPTO",
        "sector": "EXCHANGE_TOKEN",
        "indexGroup": "CRYPTO TOP",
        "groupId": "CRYPTO",
        "lotSize": 1,
        "tickSize": 0.01,
        "tvSymbol": "BNBUSDT",
    },
    {
        "symbol": "XRP/USDT",
        "shortName": "XRPUSDT",
        "fullName": "Ripple / Tether USD",
        "market": "CRYPTO",
        "exchange": "BINANCE",
        "assetType": "CRYPTO",
        "sector": "PAYMENTS",
        "indexGroup": "CRYPTO TOP",
        "groupId": "CRYPTO",
        "lotSize": 1,
        "tickSize": 0.0001,
        "tvSymbol": "XRPUSDT",
    },

    # -------------------------------------------------------------------------
    # COMMODITIES (assetType: COMMODITY)
    # -------------------------------------------------------------------------
    {
        "symbol": "CRUDEOIL",
        "shortName": "CRUDEOIL",
        "fullName": "Crude Oil Futures",
        "market": "COMMODITY",
        "exchange": "MCX",
        "assetType": "COMMODITY",
        "sector": "ENERGY",
        "indexGroup": "MCX ENERGY",
        "groupId": "MCX",
        "lotSize": 100,
        "tickSize": 1.0,
        "tvSymbol": "CRUDEOIL",
    },
    {
        "symbol": "GOLD",
        "shortName": "GOLD",
        "fullName": "Gold 1KG Futures",
        "market": "COMMODITY",
        "exchange": "MCX",
        "assetType": "COMMODITY",
        "sector": "PRECIOUS_METALS",
        "indexGroup": "MCX METALS",
        "groupId": "MCX",
        "lotSize": 1,
        "tickSize": 1.0,
        "tvSymbol": "GOLD",
    },
    {
        "symbol": "SILVER",
        "shortName": "SILVER",
        "fullName": "Silver 30KG Futures",
        "market": "COMMODITY",
        "exchange": "MCX",
        "assetType": "COMMODITY",
        "sector": "PRECIOUS_METALS",
        "indexGroup": "MCX METALS",
        "groupId": "MCX",
        "lotSize": 1,
        "tickSize": 1.0,
        "tvSymbol": "SILVER",
    },
    {
        "symbol": "NATURALGAS",
        "shortName": "NATURALGAS",
        "fullName": "Natural Gas Futures",
        "market": "COMMODITY",
        "exchange": "MCX",
        "assetType": "COMMODITY",
        "sector": "ENERGY",
        "indexGroup": "MCX ENERGY",
        "groupId": "MCX",
        "lotSize": 1250,
        "tickSize": 0.1,
        "tvSymbol": "NATURALGAS",
    },
]


async def seed_market_symbols_catalog() -> Dict[str, int]:
    """
    Idempotently seeds all Market Groups and Market Symbols into the database.
    Guarantees rich, searchable dropdown data for frontend users.
    """
    await connect_db()

    # 1. Seed Groups / Benchmark Indexes
    group_count = 0
    for grp in SEEDED_MARKET_GROUPS:
        try:
            await db.marketgroup.upsert(
                where={"groupId": grp["groupId"]},
                data={
                    "create": grp,
                    "update": grp,
                },
            )
            group_count += 1
        except Exception as e:
            logger.error(f"Error seeding group {grp['groupId']}: {e}")

    # 2. Seed Symbols (Stocks, Indexes, Forexs, Cryptos, Commodities)
    symbol_count = 0
    for sym in SEEDED_MARKET_SYMBOLS:
        try:
            await db.marketsymbol.upsert(
                where={"symbol": sym["symbol"]},
                data={
                    "create": sym,
                    "update": sym,
                },
            )
            symbol_count += 1
        except Exception as e:
            logger.error(f"Error seeding symbol {sym['symbol']}: {e}")

    logger.info(f"Database catalog seeded: {group_count} groups, {symbol_count} symbols.")
    return {"groups": group_count, "symbols": symbol_count}


async def seed_default_user():
    """Seeds default admin user if none exists in database."""
    await connect_db()
    try:
        user_count = await db.user.count()
        if user_count == 0:
            import hashlib
            pwd_hash = hashlib.sha256("Admin@123".encode()).hexdigest()
            user = await db.user.create(
                data={
                    "username": "admin",
                    "email": "admin@txbot.local",
                    "passwordHash": pwd_hash,
                    "role": "ADMIN",
                }
            )
            logger.info(f"Default admin user seeded: {user.username} (id: {user.id})")
            return user
    except Exception as e:
        logger.error(f"Error seeding default user: {e}")
    return None

