"""
txcore.execution.base
~~~~~~~~~~~~~~~~~~~~~
Abstract base class for all alert dispatchers, execution brokers, and notifiers.
Extensible for Telegram, Discord, Webhooks, Paper Brokers, and Live Broker APIs.
"""

from abc import ABC, abstractmethod
from typing import Optional
from txcore.models.types import Signal


class BaseNotifier(ABC):
    """
    Standard interface for all signal dispatchers and execution channels.
    """

    @abstractmethod
    def send(self, message: str, signal: Optional[Signal] = None) -> bool:
        """
        Dispatches signal text or order execution command.
        """
        pass
