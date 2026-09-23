"""
txcore.audit.cache
~~~~~~~~~~~~~~~~~~
Generic in-memory TTL cache with expiration and eviction support.
"""

import time
from typing import Any, Optional, Dict, Tuple


class MemoryCache:
    """
    Key-value cache with per-item or default Time-To-Live (TTL).
    """

    def __init__(self, default_ttl_seconds: float = 60.0):
        self.default_ttl = default_ttl_seconds
        self._store: Dict[str, Tuple[Any, float]] = {}

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        expiry = time.time() + (ttl if ttl is not None else self.default_ttl)
        self._store[key] = (value, expiry)

    def get(self, key: str, default: Any = None) -> Any:
        if key not in self._store:
            return default
        val, expiry = self._store[key]
        if time.time() > expiry:
            del self._store[key]
            return default
        return val

    def clear(self) -> None:
        self._store.clear()
