"""
txcore.filters.base
~~~~~~~~~~~~~~~~~~~
Abstract base class for all risk, news, volatility, and trading session filters.
"""

from abc import ABC, abstractmethod
from typing import Tuple, Optional, Any


class BaseFilter(ABC):
    """
    Standard interface for all safety and circuit breaker filters.
    Returns (is_allowed: bool, reason_if_blocked: Optional[str]).
    """

    @abstractmethod
    def is_allowed(self, symbol: str, **kwargs) -> Tuple[bool, Optional[str]]:
        """
        Evaluates whether a trade setup is permitted under current market conditions.
        """
        pass
