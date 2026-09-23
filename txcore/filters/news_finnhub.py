"""
txcore.filters.news_finnhub
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Macroeconomic news safety filter using Finnhub API.
Features automatic response caching (TTL) to prevent API rate-limit exhaustion.
"""

import time
from datetime import datetime, timezone
from typing import Tuple, Optional, Dict, Set, List
import requests
from txcore.filters.base import BaseFilter


class FinnhubNewsFilter(BaseFilter):
    """
    Blocks signals when high-impact forex macroeconomic headlines occur within the lookback window.
    """

    HIGH_IMPACT_WORDS = {
        "rate", "interest", "central bank", "fed", "ecb", "boj", "boe", "rba", "boc",
        "cpi", "inflation", "employment", "payroll", "jobs", "gdp", "pmi", "retail sales",
        "unemployment", "fomc", "policy", "decision", "speech", "war", "tariff", "sanction"
    }

    def __init__(
        self,
        api_key: str = "",
        lookback_minutes: int = 10,
        cache_ttl_seconds: int = 60,
        base_url: str = "https://finnhub.io/api/v1",
        pair_currencies: Optional[Dict[str, Set[str]]] = None,
    ):
        self.api_key = api_key
        self.lookback_minutes = lookback_minutes
        self.cache_ttl_seconds = cache_ttl_seconds
        self.base_url = base_url
        self.pair_currencies = pair_currencies or {}
        self._cache = {"timestamp": 0.0, "data": []}

    def _fetch_news(self) -> List[Dict]:
        if not self.api_key:
            return []

        now = time.time()
        if now - self._cache["timestamp"] < self.cache_ttl_seconds and self._cache["data"]:
            return self._cache["data"]

        try:
            url = f"{self.base_url}/news"
            response = requests.get(
                url,
                params={"category": "forex", "token": self.api_key},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            self._cache["timestamp"] = now
            self._cache["data"] = data
            return data
        except Exception as e:
            # Fallback to existing cached data on network error
            return self._cache.get("data", [])

    def is_allowed(self, symbol: str, **kwargs) -> Tuple[bool, Optional[str]]:
        if not self.api_key:
            return True, None

        news = self._fetch_news()
        if not news:
            return True, None

        now = datetime.now(timezone.utc)
        currencies = self.pair_currencies.get(symbol, set(symbol.replace("/", "").replace("_", "")))

        for item in news[:100]:
            headline = str(item.get("headline", "")).lower()
            summary = str(item.get("summary", "")).lower()
            text = f"{headline} {summary}"

            ts = item.get("datetime")
            if not ts:
                continue

            try:
                published = datetime.fromtimestamp(int(ts), tz=timezone.utc)
            except Exception:
                continue

            age_minutes = (now - published).total_seconds() / 60.0
            if 0 <= age_minutes <= self.lookback_minutes:
                if any(word in text for word in self.HIGH_IMPACT_WORDS):
                    if any(curr.lower() in text for curr in currencies):
                        return False, f"Relevant high-impact forex news detected: {item.get('headline')}"

        return True, None
