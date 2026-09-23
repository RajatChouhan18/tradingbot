"""
txcore.strategies.base
~~~~~~~~~~~~~~~~~~~~~~
Abstract base class defining the contract for all trading strategies.
Extensible for Price Action, Order Flow, Mean Reversion, and Indian F&O Momentum strategies.
"""

from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd
from txcore.models.types import Signal, SetupResult


class BaseStrategy(ABC):
    """
    Standard interface for all market analysis strategies.
    Receives finalized candlestick data and evaluates whether an approved Signal exists.
    """

    @abstractmethod
    def find_setup(self, df: pd.DataFrame) -> Optional[SetupResult]:
        """
        Scans historical bars for a core pattern setup and retracement.
        """
        pass

    @abstractmethod
    def validate_entry(self, df: pd.DataFrame, setup: SetupResult) -> bool:
        """
        Confirms whether the entry candle is ready (e.g. required confirmation bar has just closed).
        """
        pass

    @abstractmethod
    def evaluate(self, df: pd.DataFrame, symbol: str) -> Optional[Signal]:
        """
        End-to-end evaluation returning an actionable Signal if approved, or None.
        """
        pass
