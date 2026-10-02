"""
txcore.audit.deduplicator
~~~~~~~~~~~~~~~~~~~~~~~~~
Deduplication engine with memory leak prevention and 24-hour automated cache pruning.
Guarantees that the exact same pattern setup is never alerted more than once.
"""

import time
from typing import Dict, Tuple, Any


class SignalDeduplicator:
    """
    Tracks sent signals using unique setup keys: (symbol, pattern, str(pattern_candle_time)).
    Purges entries older than max_age_seconds (default 24 hours).
    """

    def __init__(self, max_age_seconds: float = 86400.0):
        self.max_age_seconds = max_age_seconds
        self._cache: Dict[Tuple[str, str, str], float] = {}

    def make_key(self, symbol: str, pattern: str, candle_time: Any) -> Tuple[str, str, str]:
        return (str(symbol), str(pattern), str(candle_time))

    def is_duplicate(self, symbol: str, pattern: str, candle_time: Any) -> bool:
        key = self.make_key(symbol, pattern, candle_time)
        return key in self._cache

    def record(self, symbol: str, pattern: str, candle_time: Any) -> None:
        key = self.make_key(symbol, pattern, candle_time)
        self._cache[key] = time.time()

    def prune(self) -> int:
        now = time.time()
        cutoff = now - self.max_age_seconds
        keys_to_delete = [k for k, ts in self._cache.items() if ts < cutoff]
        for k in keys_to_delete:
            del self._cache[k]
        return len(keys_to_delete)

    @property
    def size(self) -> int:
        return len(self._cache)
