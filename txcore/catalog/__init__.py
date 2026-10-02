"""
Module 2: Market Catalog & Asset Directory (txcore.catalog)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Pre-seeded benchmark symbols, TradingView live market search verification, error handling,
exchange routing, and strict decimal precision rules (4 for stocks, 6 for crypto/forex/commodities).
"""

from txcore.catalog.seeder import seed_benchmarks, BENCHMARK_GROUPS, BENCHMARK_SYMBOLS
from txcore.catalog.verifier import search_tradingview, verify_asset
from txcore.catalog.historical import (
    fetch_tradingview_bars,
    save_candles_to_database,
    seed_benchmark_historical_candles,
    query_market_candles,
)
from txcore.catalog.router import catalog_router

__all__ = [
    "seed_benchmarks",
    "BENCHMARK_GROUPS",
    "BENCHMARK_SYMBOLS",
    "search_tradingview",
    "verify_asset",
    "fetch_tradingview_bars",
    "save_candles_to_database",
    "seed_benchmark_historical_candles",
    "query_market_candles",
    "catalog_router",
]
