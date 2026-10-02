"""
txcore.execution.webhook
~~~~~~~~~~~~~~~~~~~~~~~~
Custom Webhook notification and automated webhook order relay dispatcher.
Posts standard JSON payloads to arbitrary endpoints (TradingView webhooks, Zapier, Make, internal servers).
"""

import logging
from typing import Optional, Dict, Any
import requests

from txcore.execution.base import BaseNotifier
from txcore.models.types import Signal
from txcore.audit.delivery_tracker import DeliveryTracker

logger = logging.getLogger("txcore.execution.webhook")


class WebhookNotifier(BaseNotifier):
    """
    Dispatches signals to any external HTTP/REST endpoint via JSON POST.
    """

    def __init__(
        self,
        endpoint_url: str = "",
        auth_token: Optional[str] = None,
        custom_headers: Optional[Dict[str, str]] = None,
        tracker: Optional[DeliveryTracker] = None,
    ):
        self.endpoint_url = endpoint_url.strip()
        self.auth_token = auth_token
        self.custom_headers = custom_headers or {}
        self.tracker = tracker or DeliveryTracker()

    @property
    def is_configured(self) -> bool:
        return bool(self.endpoint_url and self.endpoint_url.startswith("http"))

    def send(
        self,
        message: str,
        signal: Optional[Signal] = None,
        chart_path: Optional[str] = None,
    ) -> bool:
        """
        Sends JSON payload to endpoint_url.
        """
        if not self.is_configured:
            return False

        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        headers.update(self.custom_headers)

        payload: Dict[str, Any] = {
            "message": message,
            "has_chart": bool(chart_path),
        }

        if signal:
            payload.update({
                "signal_id": signal.signal_id,
                "symbol": signal.symbol or signal.pair,
                "direction": signal.direction.value,
                "price": float(signal.price),
                "level": float(signal.level),
                "pattern": signal.pattern,
                "timeframe": signal.timeframe,
                "stop_loss": float(signal.stop_loss) if signal.stop_loss else None,
                "target": float(signal.target) if signal.target else None,
                "candle_time": str(signal.candle_time),
                "provider": signal.provider,
                "metadata": signal.metadata,
            })

        success = False
        try:
            resp = requests.post(self.endpoint_url, json=payload, headers=headers, timeout=8)
            success = 200 <= resp.status_code < 300
            if not success:
                logger.warning(f"[WebhookNotifier] Endpoint returned error {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"[WebhookNotifier] Request failed: {e}")
            success = False

        if signal and hasattr(self.tracker, "record_dispatch"):
            try:
                self.tracker.record_dispatch(
                    signal_id=signal.signal_id,
                    pair=signal.symbol or signal.pair,
                    direction=signal.direction.value,
                    pattern=signal.pattern,
                    price=float(signal.price),
                    chat_id=self.endpoint_url[:30] + "...",
                    status="SENT" if success else "FAILED",
                )
            except Exception as trk_err:
                logger.debug(f"[WebhookNotifier] Tracker record error: {trk_err}")

        return success
