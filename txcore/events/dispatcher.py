"""
AuraTrade Multi-Channel Alert Dispatcher (txcore.events.dispatcher)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Dispatches real-time event trigger alerts to Telegram, WhatsApp, and Webhooks
with exponential backoff retries, institutional message cards, and ACID delivery tracking.
"""

import os
import time
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import httpx
from pydantic import BaseModel, Field

from txcore.database import db
from prisma import Json

logger = logging.getLogger("auratrade.events.dispatcher")


class AlertPayload(BaseModel):
    trigger_id: str
    trigger_name: str
    symbol: str
    market: str
    timeframe: str
    trigger_type: str
    trigger_price: float
    conditions_met: Dict[str, Any] = Field(default_factory=dict)
    evaluation_message: str
    candle_timestamp: datetime


class DispatchResult(BaseModel):
    channel: str
    target: str
    status: str  # SENT, FAILED, SKIPPED
    latency_ms: int = 0
    error_message: Optional[str] = None


def format_institutional_alert_text(payload: AlertPayload) -> str:
    """Formats an institutional-grade monospace alert card for messaging apps."""
    time_str = payload.candle_timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
    price_fmt = f"{payload.trigger_price:,.4f}" if payload.market in ["INDIAN_EQUITY", "US_EQUITY"] else f"{payload.trigger_price:,.6f}"

    lines = [
        f"🔔 *AURATRADE SIGNAL ALERT*",
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"• *Asset*: `{payload.symbol}` ({payload.timeframe})",
        f"• *Market*: `{payload.market}`",
        f"• *Trigger*: `{payload.trigger_type}`",
        f"• *Trigger Price*: `{price_fmt}`",
        f"• *Event Time*: `{time_str}`",
        f"• *Watcher*: {payload.trigger_name}",
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"• *Summary*: {payload.evaluation_message}",
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"⚠️ _Standalone Alert Watcher • No Trade Executed_",
    ]
    return "\n".join(lines)


class TelegramDispatcher:
    """Async Telegram Bot Dispatcher with retries."""

    def __init__(self, bot_token: Optional[str] = None):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN", "")

    async def dispatch(self, payload: AlertPayload, chat_id: str) -> DispatchResult:
        start_time = time.perf_counter()
        target = str(chat_id).strip()

        if not target or target.lower() in ["placeholder", "dummy_chat_id", "none", ""]:
            target = os.getenv("TELEGRAM_CHAT_ID", "")

        if not self.bot_token or not target:
            return DispatchResult(
                channel="TELEGRAM",
                target=target or "NOT_CONFIGURED",
                status="SKIPPED",
                latency_ms=0,
                error_message="Telegram bot token or chat ID is not configured.",
            )

        message_text = format_institutional_alert_text(payload)
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

        # Retry loop with exponential backoff
        max_retries = 3
        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        url,
                        json={
                            "chat_id": target,
                            "text": message_text,
                            "parse_mode": "Markdown",
                            "disable_web_page_preview": True,
                        },
                    )
                    elapsed_ms = int((time.perf_counter() - start_time) * 1000)

                    if resp.status_code == 200:
                        return DispatchResult(
                            channel="TELEGRAM",
                            target=target,
                            status="SENT",
                            latency_ms=elapsed_ms,
                        )
                    else:
                        last_error = f"HTTP {resp.status_code}: {resp.text}"
            except Exception as exc:
                last_error = str(exc)

            if attempt < max_retries:
                await asyncio.sleep(0.5 * (2 ** (attempt - 1)))

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        return DispatchResult(
            channel="TELEGRAM",
            target=target,
            status="FAILED",
            latency_ms=elapsed_ms,
            error_message=last_error,
        )


class WhatsAppDispatcher:
    """Async WhatsApp Alert Dispatcher (Webhook / Cloud API)."""

    def __init__(self, api_url: Optional[str] = None, api_token: Optional[str] = None):
        self.api_url = api_url or os.getenv("WHATSAPP_API_URL", "")
        self.api_token = api_token or os.getenv("WHATSAPP_API_TOKEN", "")

    async def dispatch(self, payload: AlertPayload, recipient: str) -> DispatchResult:
        start_time = time.perf_counter()
        target = str(recipient).strip()

        if not target or target.lower() in ["placeholder", "none", ""]:
            target = os.getenv("WHATSAPP_PHONE_NUMBER", "")

        if not self.api_url or not target:
            return DispatchResult(
                channel="WHATSAPP",
                target=target or "NOT_CONFIGURED",
                status="SKIPPED",
                latency_ms=0,
                error_message="WhatsApp API URL or recipient number is not configured.",
            )

        message_text = format_institutional_alert_text(payload)

        try:
            headers = {"Authorization": f"Bearer {self.api_token}"} if self.api_token else {}
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    self.api_url,
                    json={"to": target, "body": message_text},
                    headers=headers,
                )
                elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                if resp.status_code in [200, 201, 202]:
                    return DispatchResult(
                        channel="WHATSAPP",
                        target=target,
                        status="SENT",
                        latency_ms=elapsed_ms,
                    )
                else:
                    return DispatchResult(
                        channel="WHATSAPP",
                        target=target,
                        status="FAILED",
                        latency_ms=elapsed_ms,
                        error_message=f"HTTP {resp.status_code}: {resp.text}",
                    )
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            return DispatchResult(
                channel="WHATSAPP",
                target=target,
                status="FAILED",
                latency_ms=elapsed_ms,
                error_message=str(exc),
            )


class WebhookDispatcher:
    """Async Webhook Dispatcher for custom integration endpoints."""

    async def dispatch(self, payload: AlertPayload, webhook_url: str) -> DispatchResult:
        start_time = time.perf_counter()
        target = str(webhook_url).strip()

        if not target or not target.startswith("http"):
            return DispatchResult(
                channel="WEBHOOK",
                target=target or "NOT_CONFIGURED",
                status="SKIPPED",
                latency_ms=0,
                error_message="Valid Webhook URL not provided.",
            )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    target,
                    json=payload.model_dump(mode="json"),
                )
                elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                if resp.status_code in [200, 201, 202, 204]:
                    return DispatchResult(
                        channel="WEBHOOK",
                        target=target,
                        status="SENT",
                        latency_ms=elapsed_ms,
                    )
                else:
                    return DispatchResult(
                        channel="WEBHOOK",
                        target=target,
                        status="FAILED",
                        latency_ms=elapsed_ms,
                        error_message=f"HTTP {resp.status_code}: {resp.text}",
                    )
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            return DispatchResult(
                channel="WEBHOOK",
                target=target,
                status="FAILED",
                latency_ms=elapsed_ms,
                error_message=str(exc),
            )


class MultiChannelAlertDispatcher:
    """
    Coordinates concurrent multi-channel alert delivery and persists execution audit logs in PostgreSQL.
    """

    def __init__(self):
        self.telegram = TelegramDispatcher()
        self.whatsapp = WhatsAppDispatcher()
        self.webhook = WebhookDispatcher()

    async def dispatch_all(
        self,
        payload: AlertPayload,
        channels: List[str],
        channel_targets: Optional[Dict[str, Any]] = None,
        persist_audit: bool = True,
    ) -> List[DispatchResult]:
        targets = channel_targets or {}
        tasks = []

        for ch in channels:
            ch_upper = str(ch).upper().strip()
            if ch_upper == "TELEGRAM":
                t_chat = targets.get("telegram_chat_id", targets.get("telegram", ""))
                tasks.append(self.telegram.dispatch(payload, t_chat))
            elif ch_upper == "WHATSAPP":
                w_num = targets.get("whatsapp_number", targets.get("whatsapp", ""))
                tasks.append(self.whatsapp.dispatch(payload, w_num))
            elif ch_upper == "WEBHOOK":
                w_url = targets.get("webhook_url", targets.get("webhook", ""))
                tasks.append(self.webhook.dispatch(payload, w_url))

        if not tasks:
            # Default to Telegram if no tasks formed
            tasks.append(self.telegram.dispatch(payload, targets.get("telegram_chat_id", "")))

        results: List[DispatchResult] = await asyncio.gather(*tasks, return_exceptions=False)

        # Audit Log Persistence
        if persist_audit:
            try:
                overall_success = any(r.status == "SENT" for r in results) or all(r.status == "SKIPPED" for r in results)
                total_latency = sum(r.latency_ms for r in results)
                err_msgs = [r.error_message for r in results if r.error_message]

                # Update trigger lastTriggeredAt and triggerCount
                await db.eventtrigger.update(
                    where={"id": payload.trigger_id},
                    data={
                        "lastTriggeredAt": payload.candle_timestamp or datetime.now(timezone.utc),
                        "triggerCount": {"increment": 1},
                    },
                )


                # Persist TriggerExecutionLog
                await db.triggerexecutionlog.create(
                    data={
                        "triggerId": payload.trigger_id,
                        "symbol": payload.symbol,
                        "market": payload.market,
                        "timeframe": payload.timeframe,
                        "triggerType": payload.trigger_type,
                        "triggerPrice": payload.trigger_price,
                        "conditionsMet": Json(payload.conditions_met),
                        "candleTimestamp": payload.candle_timestamp,
                        "channelsNotified": Json([r.model_dump() for r in results]),
                        "dispatchSuccess": overall_success,
                        "latencyMs": total_latency,
                        "errorMessage": "; ".join(err_msgs) if err_msgs else None,
                        "createdBy": "SYSTEM",
                        "updatedBy": "SYSTEM",
                    }
                )
            except Exception as e:
                logger.error(f"Failed to persist trigger execution log: {e}", exc_info=True)

        return results


# Global singleton instance
dispatcher_service = MultiChannelAlertDispatcher()
