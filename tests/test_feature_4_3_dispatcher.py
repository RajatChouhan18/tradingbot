"""
Test: Feature 4.3 Multi-Channel Alert Dispatcher
Verifies message formatting, async multi-channel dispatch coordination,
and execution log persistence in PostgreSQL.
"""

import sys
import os
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from txcore.database import connect_db, disconnect_db, db
from txcore.events.models import TriggerType, TriggerStatus
from txcore.events.dispatcher import (
    AlertPayload,
    format_institutional_alert_text,
    MultiChannelAlertDispatcher,
)
from prisma import Json


@pytest.mark.anyio
async def test_alert_formatting():
    payload = AlertPayload(
        trigger_id="trig-123",
        trigger_name="Nifty Supertrend Breakout",
        symbol="NIFTY 50",
        market="INDIAN_EQUITY",
        timeframe="5m",
        trigger_type="PRICE_SPIKE",
        trigger_price=24850.25,
        conditions_met={"spike_pct": 1.8},
        evaluation_message="Price surge of +1.8% confirmed over 3 bars.",
        candle_timestamp=datetime(2026, 10, 3, 1, 0, 0, tzinfo=timezone.utc),
    )

    text = format_institutional_alert_text(payload)
    assert "AURATRADE SIGNAL ALERT" in text
    assert "NIFTY 50" in text
    assert "24,850.2500" in text
    assert "Standalone Alert Watcher" in text


@pytest.mark.anyio
async def test_multi_channel_dispatch_with_audit_persistence():
    await connect_db()

    # Clean up test triggers
    await db.triggerexecutionlog.delete_many(where={"symbol": "DISPATCH_TEST"})
    await db.eventtrigger.delete_many(where={"symbol": "DISPATCH_TEST"})

    trigger = await db.eventtrigger.create(
        data={
            "name": "Dispatch Test Trigger",
            "symbol": "DISPATCH_TEST",
            "market": "INDIAN_EQUITY",
            "timeframe": "5m",
            "triggerType": TriggerType.PRICE_SPIKE,
            "thresholdConfig": Json({"spike_pct": 2.0}),
            "channels": Json(["TELEGRAM", "WEBHOOK"]),
            "channelTargets": Json({"telegram_chat_id": "12345", "webhook_url": "https://example.com/webhook"}),
            "status": TriggerStatus.ACTIVE,
        }
    )

    payload = AlertPayload(
        trigger_id=trigger.id,
        trigger_name=trigger.name,
        symbol=trigger.symbol,
        market=trigger.market,
        timeframe=trigger.timeframe,
        trigger_type=trigger.triggerType,
        trigger_price=1050.0,
        conditions_met={"spike_pct": 2.4},
        evaluation_message="Price surge of +2.4% met threshold.",
        candle_timestamp=datetime.now(timezone.utc),
    )

    dispatcher = MultiChannelAlertDispatcher()

    # Mock httpx.AsyncClient post to return 200 OK
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.text = "ok"

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        results = await dispatcher.dispatch_all(
            payload=payload,
            channels=["TELEGRAM", "WEBHOOK"],
            channel_targets={"telegram_chat_id": "12345", "webhook_url": "https://example.com/webhook"},
            persist_audit=True,
        )

    assert len(results) == 2
    # Verify execution log was created in DB
    logs = await db.triggerexecutionlog.find_many(where={"triggerId": trigger.id})
    assert len(logs) == 1
    assert logs[0].symbol == "DISPATCH_TEST"
    assert logs[0].triggerPrice == 1050.0

    # Verify trigger count was incremented
    updated_trig = await db.eventtrigger.find_unique(where={"id": trigger.id})
    assert updated_trig.triggerCount == 1
    assert updated_trig.lastTriggeredAt is not None

    # Clean up
    await db.triggerexecutionlog.delete_many(where={"symbol": "DISPATCH_TEST"})
    await db.eventtrigger.delete_many(where={"symbol": "DISPATCH_TEST"})

    print("\n[SUCCESS] Feature 4.3 Multi-Channel Alert Dispatcher verified!")
