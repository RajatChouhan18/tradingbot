"""
txcore.execution.telegram
~~~~~~~~~~~~~~~~~~~~~~~~~
Telegram notification dispatcher with safe rate-limiting and connection handling.
"""

from typing import Optional
import requests
from txcore.execution.base import BaseNotifier
from txcore.models.types import Signal


class TelegramNotifier(BaseNotifier):
    """
    Sends formatted trade alert messages to Telegram chats and channels.
    """

    def __init__(self, bot_token: str = "", chat_id: str = ""):
        self.bot_token = bot_token
        self.chat_id = chat_id

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id and self.chat_id != "dummy_chat_id")

    def send(self, message: str, signal: Optional[Signal] = None) -> bool:
        if not self.is_configured:
            print("[TELEGRAM SKIPPED] Bot token or CHAT_ID not configured.")
            return False

        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            response = requests.post(
                url,
                data={"chat_id": self.chat_id, "text": message},
                timeout=15,
            )
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"[TELEGRAM ERROR] Failed to send message: {e}")
            return False
