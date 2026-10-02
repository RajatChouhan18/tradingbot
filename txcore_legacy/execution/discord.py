"""
txcore.execution.discord
~~~~~~~~~~~~~~~~~~~~~~~~
Discord Webhook notification dispatcher.
Renders high-fidelity rich embed alerts formatted with institutional color tags,
multi-factor metadata fields (SL, TP, ATR, MTF trend), and optional chart document attachments.
"""

import os
import json
import logging
from typing import Optional, Dict, Any
import requests

from txcore.execution.base import BaseNotifier
from txcore.models.types import Signal, Direction
from txcore.audit.delivery_tracker import DeliveryTracker

logger = logging.getLogger("txcore.execution.discord")


class DiscordNotifier(BaseNotifier):
    """
    Dispatches signals to Discord channels via Webhook API.
    """

    def __init__(
        self,
        webhook_url: str = "",
        tracker: Optional[DeliveryTracker] = None,
    ):
        self.webhook_url = webhook_url.strip()
        self.tracker = tracker or DeliveryTracker()

    @property
    def is_configured(self) -> bool:
        return bool(self.webhook_url and self.webhook_url.startswith("http"))

    def send(
        self,
        message: str,
        signal: Optional[Signal] = None,
        chart_path: Optional[str] = None,
    ) -> bool:
        """
        Formats signal into rich Discord embed and posts to webhook URL.
        """
        if not self.is_configured:
            logger.debug("[DiscordNotifier] Webhook URL not configured, skipping.")
            return False

        # Determine embed color: Emerald Green (0x10B981) for CALL, Crimson (0xEF4444) for PUT
        is_call = signal and signal.direction == Direction.CALL
        embed_color = 0x10B981 if is_call else 0xEF4444

        symbol = (signal.symbol or signal.pair) if signal else "Trading Signal"
        direction_str = signal.direction.value if signal else "ALERT"

        fields = []
        if signal:
            fields.extend([
                {"name": "Direction", "value": f"**{direction_str}**", "inline": True},
                {"name": "Price", "value": f"`{signal.price:.4f}`", "inline": True},
                {"name": "Timeframe", "value": f"`{signal.timeframe}`", "inline": True},
                {"name": "Pattern", "value": signal.pattern, "inline": True},
                {"name": "Key Level", "value": f"`{signal.level:.4f}`", "inline": True},
            ])
            if signal.stop_loss:
                fields.append({"name": "Stop Loss", "value": f"🛑 `{signal.stop_loss:.4f}`", "inline": True})
            if signal.target:
                fields.append({"name": "Target", "value": f"🎯 `{signal.target:.4f}`", "inline": True})
            if hasattr(signal, "metadata") and signal.metadata:
                if "mtf_trend" in signal.metadata:
                    fields.append({"name": "MTF Trend", "value": f"📈 {signal.metadata['mtf_trend']}", "inline": True})
                if "atr" in signal.metadata and signal.metadata["atr"]:
                    fields.append({"name": "ATR (Volatility)", "value": f"📏 `{signal.metadata['atr']:.4f}`", "inline": True})

        embed = {
            "title": f"🚨 {direction_str} Signal: {symbol}",
            "description": message[:1000] if not fields else (signal.reason if signal else message),
            "color": embed_color,
            "fields": fields,
            "footer": {"text": f"TxBot Quantitative Engine • ID: {signal.signal_id if signal else 'MANUAL'}"},
        }

        payload: Dict[str, Any] = {"embeds": [embed]}

        success = False
        try:
            if chart_path and os.path.exists(chart_path):
                with open(chart_path, "rb") as f:
                    files = {
                        "payload_json": (None, json.dumps(payload)),
                        "file": (os.path.basename(chart_path), f, "text/html"),
                    }
                    resp = requests.post(self.webhook_url, files=files, timeout=12)
            else:
                resp = requests.post(self.webhook_url, json=payload, timeout=8)

            success = resp.status_code in (200, 204)
            if not success:
                logger.warning(f"[DiscordNotifier] Webhook response failed: {resp.status_code} - {resp.text}")
        except Exception as e:
            logger.error(f"[DiscordNotifier] Error sending to webhook: {e}")
            success = False

        if signal and hasattr(self.tracker, "record_dispatch"):
            try:
                self.tracker.record_dispatch(
                    signal_id=signal.signal_id,
                    pair=signal.symbol or signal.pair,
                    direction=signal.direction.value,
                    pattern=signal.pattern,
                    price=float(signal.price),
                    chat_id=self.webhook_url[:30] + "...",
                    status="SENT" if success else "FAILED",
                )
            except Exception as trk_err:
                logger.debug(f"[DiscordNotifier] Tracker record error: {trk_err}")

        return success
