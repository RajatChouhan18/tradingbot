"""
txcore.catalog.verifier
~~~~~~~~~~~~~~~~~~~~~~~
Real-time live market search and verification engine using TradingView Symbol Search API.
Supports discovery and verification across:
- Indian Equities & Indices (NSE / BSE)
- US Equities & Indices (NASDAQ / NYSE / AMEX)
- Crypto Pairs (Binance / Spot)
- Forex Pairs (FX_IDC)
- MCX Commodities (MCX)

Enforces strict precision rules:
- Stocks & Indices: Exactly 4 decimal places
- Crypto, Forex, Commodities: Exactly 6 decimal places
"""

import re
import urllib.parse
import logging
from typing import List, Optional, Dict, Any
import httpx

from txcore.catalog.models import TradingViewSearchResult, AssetVerificationResponse

logger = logging.getLogger("auratrade.catalog.verifier")

TRADINGVIEW_SEARCH_URL = "https://symbol-search.tradingview.com/symbol_search/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Origin": "https://www.tradingview.com",
    "Referer": "https://www.tradingview.com/",
    "Accept": "*/*",
}

# Mapping between target market and expected exchanges / types
MARKET_EXCHANGE_MAP = {
    "INDIAN_EQUITY": ["NSE", "BSE"],
    "US_EQUITY": ["NASDAQ", "NYSE", "AMEX", "BATS", "ARCA"],
    "CRYPTO": ["BINANCE", "COINBASE", "BYBIT", "KRAKEN", "BITSTAMP"],
    "FOREX": ["FX_IDC", "OANDA", "FOREXCOM", "SAXO", "IDC"],
    "MCX": ["MCX"],
}


def _strip_html(text: str) -> str:
    """Removes HTML highlight tags (e.g. <em>...</em>) from TradingView results."""
    return re.sub(r"<[^>]+>", "", text).strip() if text else ""


def _normalize_asset_type(tv_type: str, exchange: str) -> str:
    """Normalizes TradingView type string to AuraTrade asset type."""
    t = (tv_type or "").lower()
    exch = (exchange or "").upper()

    if exch in ["BINANCE", "BYBIT", "COINBASE"] or t in ["crypto", "spot"]:
        return "CRYPTO"
    if exch in ["FX_IDC", "OANDA", "FOREXCOM"] or t in ["forex"]:
        return "FOREX"
    if exch in ["MCX"] or t in ["commodity"]:
        return "COMMODITY"
    if t in ["index"]:
        return "INDEX"
    return "STOCK"


def _determine_market_and_precision(normalized_type: str, exchange: str) -> tuple[str, int]:
    """Determines market classification and strict decimal places (4 vs 6)."""
    exch = (exchange or "").upper()

    if normalized_type == "CRYPTO":
        return "CRYPTO", 6
    if normalized_type == "FOREX":
        return "FOREX", 6
    if normalized_type == "COMMODITY":
        return "MCX" if exch == "MCX" else "COMMODITY", 6
    if exch in ["NSE", "BSE"]:
        return "INDIAN_EQUITY", 4
    if exch in ["NASDAQ", "NYSE", "AMEX", "BATS", "ARCA"]:
        return "US_EQUITY", 4

    # Default fallback based on asset type
    if normalized_type in ["STOCK", "INDEX"]:
        return "INDIAN_EQUITY" if exch in ["NSE", "BSE"] else "US_EQUITY", 4
    return "FOREX", 6


async def search_tradingview(
    query: str,
    market: Optional[str] = None,
    exchange: Optional[str] = None,
    limit: int = 20,
) -> List[TradingViewSearchResult]:
    """
    Queries TradingView Symbol Search API and returns cleaned, normalized search results.
    """
    clean_query = query.strip()
    if not clean_query:
        return []

    encoded_query = urllib.parse.quote(clean_query)
    url = f"{TRADINGVIEW_SEARCH_URL}?text={encoded_query}&hl=1"
    if exchange:
        url += f"&exchange={urllib.parse.quote(exchange.upper())}"

    results: List[TradingViewSearchResult] = []

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, headers=HEADERS)
            if resp.status_code != 200:
                logger.warning(f"TradingView search API returned status {resp.status_code} for query: {clean_query}")
                return []

            data = resp.json()
            if not isinstance(data, list):
                return []

            for item in data:
                raw_symbol = _strip_html(item.get("symbol", ""))
                raw_desc = _strip_html(item.get("description", "")) or raw_symbol
                raw_exch = _strip_html(item.get("exchange", "")).upper()
                raw_type = _strip_html(item.get("type", "")).lower()

                if not raw_symbol or not raw_exch:
                    continue

                normalized_type = _normalize_asset_type(raw_type, raw_exch)
                detected_market, decimals = _determine_market_and_precision(normalized_type, raw_exch)

                # Filter by market if market was specified
                if market:
                    target_market = market.upper()
                    expected_exchanges = MARKET_EXCHANGE_MAP.get(target_market)
                    if expected_exchanges and raw_exch not in expected_exchanges:
                        # Skip symbols not in the target market's exchanges
                        if target_market in ["INDIAN_EQUITY", "US_EQUITY", "CRYPTO", "FOREX", "MCX"]:
                            continue

                tv_symbol_str = f"{raw_exch}:{raw_symbol}"

                results.append(
                    TradingViewSearchResult(
                        symbol=raw_symbol,
                        name=raw_desc,
                        exchange=raw_exch,
                        assetType=normalized_type,
                        market=detected_market,
                        tvSymbol=tv_symbol_str,
                        decimalPlaces=decimals,
                        country=item.get("country", ""),
                        currency=item.get("currency_code", ""),
                    )
                )

                if len(results) >= limit:
                    break

    except Exception as e:
        logger.error(f"Error executing TradingView search for query '{clean_query}': {e}")
        return []

    return results


async def verify_asset(
    query: str,
    market: Optional[str] = "INDIAN_EQUITY",
    exchange: Optional[str] = None,
) -> AssetVerificationResponse:
    """
    Verifies that a company name or ticker exists on TradingView for the specified market.
    Returns AssetVerificationResponse with verified status and error message on failure.
    """
    clean_query = query.strip()
    target_market = (market or "INDIAN_EQUITY").upper()

    results = await search_tradingview(
        query=clean_query,
        market=target_market,
        exchange=exchange,
        limit=10,
    )

    if not results:
        # User-directed explicit error format
        error_msg = (
            f"Asset '{clean_query}' could not be found or verified on TradingView for {target_market}. "
            "Please check the symbol or company name."
        )
        return AssetVerificationResponse(verified=False, error=error_msg)

    # Return top verified result
    return AssetVerificationResponse(verified=True, asset=results[0])
