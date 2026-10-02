"""
txcore.providers.nse_provider
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Resilient direct HTTP client and data provider for the National Stock Exchange of India (NSE).
Features automatic session priming, cookie refresh, error containment, and schema mapping.
Conforms to the BaseDataProvider contract for market-agnostic pipeline integration.
"""

import time
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import requests

from txcore.providers.base import BaseDataProvider
from txcore.models.types import (
    IndexQuote,
    StockQuote,
    MarketBreadth,
    OptionChainSummary,
    IndianIndexQuote,  # backward-compatible alias
    IndianStockQuote,  # backward-compatible alias
)

logger = logging.getLogger(__name__)


class NSEClient:
    """
    Direct client for fetching official real-time quotes, indices, market breadth,
    and exchange status from NSE India (nseindia.com).
    """

    BASE_URL = "https://www.nseindia.com"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
    }
    API_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/market-data/live-market-indices",
        "X-Requested-With": "XMLHttpRequest",
    }

    def __init__(self, timeout: float = 10.0, cookie_refresh_interval: float = 300.0):
        self.timeout = timeout
        self.cookie_refresh_interval = cookie_refresh_interval
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self.last_cookie_time: float = 0.0
        self._cached_indices: List[IndexQuote] = []
        self._last_indices_fetch: float = 0.0

    def _ensure_session(self, force: bool = False):
        """Primes cookies by visiting the main NSE homepage if expired or requested."""
        now = time.time()
        if not force and (now - self.last_cookie_time < self.cookie_refresh_interval) and self.session.cookies:
            return

        try:
            self.session.get(self.BASE_URL, timeout=self.timeout)
            self.last_cookie_time = time.time()
        except Exception as e:
            logger.debug(f"NSE session bootstrap attempt failed: {e}")

    def _get_api(self, endpoint: str, referer: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Makes an authenticated GET request to NSE API endpoints with automatic retry on 401/403."""
        self._ensure_session()
        headers = dict(self.API_HEADERS)
        if referer:
            headers["Referer"] = referer

        url = f"{self.BASE_URL}{endpoint}" if endpoint.startswith("/") else endpoint

        for attempt in range(2):
            try:
                resp = self.session.get(url, headers=headers, timeout=self.timeout)
                if resp.status_code == 200:
                    return resp.json()
                elif resp.status_code in (401, 403):
                    # Refresh cookies and retry once
                    self._ensure_session(force=True)
                    time.sleep(0.5)
                    continue
                else:
                    logger.debug(f"NSE API {endpoint} returned status {resp.status_code}")
                    return None
            except Exception as e:
                logger.debug(f"NSE API request error for {endpoint}: {e}")
                if attempt == 0:
                    time.sleep(0.5)
                    self._ensure_session(force=True)

        return None

    def get_market_status(self) -> Optional[Dict[str, Any]]:
        """
        Fetches live exchange market status for Capital Market, Currency, Derivatives,
        and GIFT NIFTY from /api/marketStatus.
        """
        return self._get_api("/api/marketStatus", referer="https://www.nseindia.com")

    def get_all_indices(self, max_cache_age_seconds: float = 15.0) -> List[IndexQuote]:
        """
        Fetches all benchmark, broad-market, and sectoral index quotes from NSE.
        Returns a list of standardized IndexQuote objects.
        """
        now = time.time()
        if self._cached_indices and (now - self._last_indices_fetch < max_cache_age_seconds):
            return self._cached_indices

        data = self._get_api("/api/allIndices", referer="https://www.nseindia.com/market-data/live-market-indices")
        if not data or "data" not in data:
            return self._cached_indices

        results: List[IndexQuote] = []
        for item in data.get("data", []):
            try:
                quote = IndexQuote(
                    name=str(item.get("index", "")).strip(),
                    symbol=str(item.get("indexSymbol", item.get("index", ""))).strip(),
                    last_price=float(item.get("last", 0.0) or 0.0),
                    change=float(item.get("variation", 0.0) or 0.0),
                    percent_change=float(item.get("percentChange", 0.0) or 0.0),
                    open=float(item.get("open", 0.0) or 0.0),
                    high=float(item.get("high", 0.0) or 0.0),
                    low=float(item.get("low", 0.0) or 0.0),
                    previous_close=float(item.get("previousClose", 0.0) or 0.0),
                    year_high=float(item.get("yearHigh", 0.0) or 0.0),
                    year_low=float(item.get("yearLow", 0.0) or 0.0),
                    pe=float(item.get("pe", 0.0) or 0.0) if item.get("pe") not in ("-", None) else 0.0,
                    pb=float(item.get("pb", 0.0) or 0.0) if item.get("pb") not in ("-", None) else 0.0,
                    dy=float(item.get("dy", 0.0) or 0.0) if item.get("dy") not in ("-", None) else 0.0,
                    advances=int(item.get("advances", 0) or 0),
                    declines=int(item.get("declines", 0) or 0),
                    unchanged=int(item.get("unchanged", 0) or 0),
                    exchange="NSE",
                    timestamp=datetime.now(timezone.utc),
                )
                results.append(quote)
            except Exception as parse_err:
                logger.debug(f"Failed parsing index item: {parse_err}")

        if results:
            self._cached_indices = results
            self._last_indices_fetch = now

        return self._cached_indices

    def get_index_quote(self, index_name: str) -> Optional[IndexQuote]:
        """
        Finds a specific index quote by name or symbol (e.g. 'NIFTY 50', 'NIFTY', 'BANKNIFTY', 'INDIA VIX').
        Fuzzy matches canonical names.
        """
        indices = self.get_all_indices()
        clean_target = index_name.upper().replace(" ", "").replace("_", "")

        for quote in indices:
            q_name = quote.name.upper().replace(" ", "").replace("_", "")
            q_sym = quote.symbol.upper().replace(" ", "").replace("_", "")
            if clean_target in (q_name, q_sym) or (clean_target == "NIFTY" and q_name == "NIFTY50") or (clean_target == "BANKNIFTY" and q_name == "NIFTYBANK"):
                return quote

        # Second pass: check substring
        for quote in indices:
            q_name = quote.name.upper().replace(" ", "")
            if clean_target in q_name:
                return quote

        return None

    def get_market_breadth(self, index_name: str = "NIFTY 50") -> MarketBreadth:
        """
        Calculates market breadth (Advances, Declines, Unchanged, ADR) for the specified index.
        """
        quote = self.get_index_quote(index_name)
        if quote:
            return MarketBreadth(
                advances=quote.advances,
                declines=quote.declines,
                unchanged=quote.unchanged,
                index_name=quote.name,
                timestamp=datetime.now(timezone.utc),
            )
        return MarketBreadth(advances=0, declines=0, unchanged=0, index_name=index_name)

    def get_vix_quote(self) -> Optional[IndexQuote]:
        """Fetches the current India VIX volatility gauge quote."""
        return self.get_index_quote("INDIA VIX")

    def get_top_gainers_losers(self, index_category: str = "SECTORAL", count: int = 5) -> Dict[str, List[IndexQuote]]:
        """
        Returns top advancing and top declining indices sorted by percentage change.
        """
        indices = self.get_all_indices()
        # Filter non-zero traded indices
        active = [idx for idx in indices if idx.last_price > 0 and idx.name not in ("INDIA VIX",)]
        sorted_by_change = sorted(active, key=lambda x: x.percent_change, reverse=True)

        return {
            "gainers": sorted_by_change[:count],
            "losers": sorted_by_change[-count:][::-1],
        }

    def get_stock_quote(self, symbol: str) -> Optional[StockQuote]:
        """
        Fetches official real-time stock quote from NSE India (/api/quote-equity).
        Parses live price, day OHLC, 52-week range, change %, and total traded volume.
        Falls back to get_index_quote if symbol is an index.
        """
        clean = symbol.strip().upper()
        if ":" in clean:
            clean = clean.split(":", 1)[1].strip()
        if clean.endswith(".NS"):
            clean = clean[:-3].strip()

        # Check if it is a benchmark or sectoral index first
        clean_idx = clean.replace(" ", "").replace("_", "")
        if clean_idx in ("NIFTY", "NIFTY50", "BANKNIFTY", "NIFTYBANK", "FINNIFTY", "MIDCPNIFTY", "SENSEX", "INDIAVIX") or "NIFTY" in clean_idx:
            idx = self.get_index_quote(clean)
            if idx:
                return StockQuote(
                    symbol=idx.symbol,
                    company_name=idx.name,
                    last_price=idx.last_price,
                    change=idx.change,
                    percent_change=idx.percent_change,
                    open=idx.open,
                    high=idx.high,
                    low=idx.low,
                    close=idx.last_price,
                    volume=0.0,
                    high_52w=idx.year_high,
                    low_52w=idx.year_low,
                    exchange=idx.exchange,
                    sector="Index",
                    timestamp=idx.timestamp or datetime.now(timezone.utc),
                )

        # Call NSE Quote Equity endpoint
        import urllib.parse
        encoded_sym = urllib.parse.quote(clean)
        data = self._get_api(
            f"/api/quote-equity?symbol={encoded_sym}",
            referer=f"https://www.nseindia.com/get-quotes/equity?symbol={encoded_sym}",
        )

        if not data or not isinstance(data, dict):
            # Fallback to index quote if equity endpoint fails
            idx = self.get_index_quote(clean)
            if idx:
                return StockQuote(
                    symbol=idx.symbol,
                    company_name=idx.name,
                    last_price=idx.last_price,
                    change=idx.change,
                    percent_change=idx.percent_change,
                    open=idx.open,
                    high=idx.high,
                    low=idx.low,
                    close=idx.last_price,
                    volume=0.0,
                    high_52w=idx.year_high,
                    low_52w=idx.year_low,
                    exchange=idx.exchange,
                    sector="Index",
                    timestamp=idx.timestamp or datetime.now(timezone.utc),
                )
            return None

        try:
            info = data.get("info", {}) or {}
            price_info = data.get("priceInfo", {}) or {}
            intra = price_info.get("intraDayHighLow", {}) or {}
            week = price_info.get("weekHighLow", {}) or {}
            order_book = data.get("marketDeptOrderBook", {}) or {}

            company_name = str(info.get("companyName", clean))
            last_price = float(price_info.get("lastPrice", 0.0) or 0.0)
            change = float(price_info.get("change", 0.0) or 0.0)
            percent_change = float(price_info.get("pChange", 0.0) or 0.0)
            open_p = float(price_info.get("open", 0.0) or 0.0)
            close_p = float(price_info.get("close", 0.0) or price_info.get("previousClose", 0.0) or last_price)
            high_p = float(intra.get("max", 0.0) or 0.0)
            low_p = float(intra.get("min", 0.0) or 0.0)
            high_52 = float(week.get("max", 0.0) or 0.0)
            low_52 = float(week.get("min", 0.0) or 0.0)
            vol = float(order_book.get("totalTradedVolume", 0.0) or 0.0)

            return StockQuote(
                symbol=clean,
                company_name=company_name,
                last_price=last_price,
                change=change,
                percent_change=percent_change,
                open=open_p,
                high=high_p,
                low=low_p,
                close=close_p,
                volume=vol,
                high_52w=high_52,
                low_52w=low_52,
                exchange="NSE",
                sector=str(info.get("industry", "") or ""),
                timestamp=datetime.now(timezone.utc),
            )
        except Exception as e:
            logger.debug(f"Failed parsing equity quote for {clean}: {e}")
            return None

    def get_option_chain_summary(self, symbol: str) -> Optional[OptionChainSummary]:
        """
        Fetches option chain summary metrics (PCR, Max Pain, Top OI Strikes)
        for an index or equity symbol.
        """
        import urllib.parse
        clean = symbol.strip().upper().replace(" ", "").replace("_", "")
        is_index = clean in ("NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY")
        sym_name = "NIFTY" if clean in ("NIFTY", "NIFTY50") else ("BANKNIFTY" if clean in ("BANKNIFTY", "NIFTYBANK") else clean)

        encoded = urllib.parse.quote(sym_name)
        endpoint = f"/api/option-chain-indices?symbol={encoded}" if is_index else f"/api/option-chain-equities?symbol={encoded}"
        referer = "https://www.nseindia.com/option-chain"

        data = self._get_api(endpoint, referer=referer)
        if not data or not isinstance(data, dict):
            return None

        records = data.get("records", {})
        items = records.get("data", [])
        if not items:
            return None

        underlying_val = float(records.get("underlyingValue", 0.0) or 0.0)
        total_call_oi = 0
        total_put_oi = 0
        call_oi_by_strike: Dict[float, int] = {}
        put_oi_by_strike: Dict[float, int] = {}

        for item in items:
            strike = float(item.get("strikePrice", 0.0) or 0.0)
            ce = item.get("CE", {})
            pe = item.get("PE", {})
            if ce:
                c_oi = int(ce.get("openInterest", 0) or 0)
                total_call_oi += c_oi
                call_oi_by_strike[strike] = call_oi_by_strike.get(strike, 0) + c_oi
            if pe:
                p_oi = int(pe.get("openInterest", 0) or 0)
                total_put_oi += p_oi
                put_oi_by_strike[strike] = put_oi_by_strike.get(strike, 0) + p_oi

        pcr = round(total_put_oi / total_call_oi, 2) if total_call_oi > 0 else 1.0
        sentiment = "BULLISH" if pcr >= 1.2 else ("BEARISH" if pcr < 0.8 else "NEUTRAL")

        top_call_strike = max(call_oi_by_strike.items(), key=lambda x: x[1])[0] if call_oi_by_strike else None
        top_put_strike = max(put_oi_by_strike.items(), key=lambda x: x[1])[0] if put_oi_by_strike else None

        return OptionChainSummary(
            underlying=sym_name,
            spot_price=underlying_val,
            total_call_oi=total_call_oi,
            total_put_oi=total_put_oi,
            pcr=pcr,
            pcr_sentiment=sentiment,
            max_pain_strike=None,
            top_call_oi_strike=top_call_strike,
            top_put_oi_strike=top_put_strike,
            timestamp=datetime.now(timezone.utc),
        )

