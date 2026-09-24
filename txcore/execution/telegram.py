"""
txcore.execution.telegram
~~~~~~~~~~~~~~~~~~~~~~~~~
Telegram notification dispatcher supporting single or multiple chat IDs,
interactive chart document attachments, rate-limit pacing, and delivery logging via DeliveryTracker.
"""

import os
from typing import Optional, List, Union, Dict
import requests
from txcore.execution.base import BaseNotifier
from txcore.models.types import Signal
from txcore.audit.delivery_tracker import DeliveryTracker


class TelegramNotifier(BaseNotifier):
    """
    Sends formatted trade alert messages and interactive chart files to one or multiple Telegram chats/channels.
    Records delivery status (SENT / FAILED / SKIPPED) per chat ID into DeliveryTracker.
    """

    def __init__(
        self,
        bot_token: str = "",
        chat_id: Optional[str] = None,
        chat_ids: Optional[List[str]] = None,
        tracker: Optional[DeliveryTracker] = None,
    ):
        self.bot_token = bot_token
        self.tracker = tracker or DeliveryTracker()

        # Normalize chat_id and chat_ids
        resolved_ids: List[str] = []
        if chat_ids:
            resolved_ids.extend([str(c).strip() for c in chat_ids if str(c).strip()])
        if chat_id and str(chat_id).strip() and str(chat_id).strip() not in resolved_ids:
            resolved_ids.append(str(chat_id).strip())

        self.chat_ids = resolved_ids

    @property
    def is_configured(self) -> bool:
        valid_targets = [c for c in self.chat_ids if c and c != "dummy_chat_id"]
        return bool(self.bot_token and valid_targets)

    def send(
        self,
        message: str,
        signal: Optional[Signal] = None,
        chart_path: Optional[str] = None,
    ) -> Dict[str, bool]:
        """
        Dispatches alert text (and optional chart HTML attachment) to all configured Telegram chat IDs.
        Returns a dictionary mapping chat_id -> success boolean for the message alert.
        """
        results: Dict[str, bool] = {}

        if not self.bot_token:
            print("[TELEGRAM SKIPPED] TELEGRAM_BOT_TOKEN not configured.")
            return results

        if not self.chat_ids:
            print("[TELEGRAM SKIPPED] No chat IDs configured.")
            return results

        sig_id = signal.signal_id if signal else "UNSPECIFIED"
        pair = signal.pair if signal else "UNKNOWN"
        direction = signal.direction.value if signal else "UNKNOWN"
        pattern = signal.pattern if signal else "UNKNOWN"
        price = signal.price if signal else 0.0

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

        for cid in self.chat_ids:
            if not cid or cid == "dummy_chat_id":
                print(f"[TELEGRAM SKIPPED] Chat ID '{cid}' is a placeholder or empty.")
                self.tracker.record_dispatch(
                    signal_id=sig_id,
                    pair=pair,
                    direction=direction,
                    pattern=pattern,
                    price=price,
                    chat_id=cid,
                    status="SKIPPED",
                    error_message="Chat ID is placeholder or empty",
                )
                results[cid] = False
                continue

            try:
                response = requests.post(
                    url,
                    data={"chat_id": cid, "text": message},
                    timeout=15,
                )
                response.raise_for_status()

                self.tracker.record_dispatch(
                    signal_id=sig_id,
                    pair=pair,
                    direction=direction,
                    pattern=pattern,
                    price=price,
                    chat_id=cid,
                    status="SENT",
                )
                print(f"✈️ [TELEGRAM SENT] Dispatched signal {sig_id} to chat {cid}")
                results[cid] = True

            except Exception as e:
                err_msg = str(e)
                print(f"❌ [TELEGRAM ERROR] Failed to dispatch to chat {cid}: {err_msg}")
                self.tracker.record_dispatch(
                    signal_id=sig_id,
                    pair=pair,
                    direction=direction,
                    pattern=pattern,
                    price=price,
                    chat_id=cid,
                    status="FAILED",
                    error_message=err_msg,
                )
                results[cid] = False

        # If an interactive chart file is provided, dispatch it as a document
        if chart_path and os.path.exists(chart_path):
            sig_name = f"{pair} - {direction} {pattern}" if signal else "TradingView Chart"
            caption = f"📊 Interactive Chart: {sig_name}"
            self.send_document(chart_path, caption=caption, signal=signal)

        return results

    def send_document(
        self,
        document_path: str,
        caption: str = "",
        signal: Optional[Signal] = None,
    ) -> Dict[str, bool]:
        """
        Dispatches a document/chart file (e.g. interactive HTML chart) to all configured Telegram chat IDs.
        Returns a dictionary mapping chat_id -> success boolean.
        """
        results: Dict[str, bool] = {}

        if not self.bot_token or not self.chat_ids:
            return results

        if not os.path.exists(document_path):
            print(f"⚠️ [TELEGRAM CHART ERROR] File not found: {document_path}")
            return results

        url = f"https://api.telegram.org/bot{self.bot_token}/sendDocument"
        filename = os.path.basename(document_path)

        for cid in self.chat_ids:
            if not cid or cid == "dummy_chat_id":
                results[cid] = False
                continue

            try:
                with open(document_path, "rb") as doc_file:
                    response = requests.post(
                        url,
                        data={"chat_id": cid, "caption": caption},
                        files={"document": (filename, doc_file, "text/html")},
                        timeout=30,
                    )
                response.raise_for_status()
                print(f"📊 [TELEGRAM CHART SENT] Dispatched {filename} to chat {cid}")
                results[cid] = True
            except Exception as e:
                err_msg = str(e)
                print(f"❌ [TELEGRAM CHART ERROR] Failed to send chart to chat {cid}: {err_msg}")
                results[cid] = False

        return results
