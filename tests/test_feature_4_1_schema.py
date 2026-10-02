"""
Test: Feature 4.1 Event Trigger Database Schema & Audit Models
Verifies EventTrigger and TriggerExecutionLog Prisma models, audit tracking columns,
soft-delete invariants, and relational integrity.
"""

import sys
import os
import pytest
from datetime import datetime, timezone

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from txcore.database import connect_db, disconnect_db, db
from prisma.enums import TriggerType, TriggerStatus, ChannelType
from prisma import Json


@pytest.mark.anyio
async def test_event_trigger_schema_crud_and_audit():
    await connect_db()

    # Clean up existing test triggers
    await db.triggerexecutionlog.delete_many(where={"symbol": "TEST_RELIANCE"})
    await db.eventtrigger.delete_many(where={"symbol": "TEST_RELIANCE"})

    # 1. Create an EventTrigger with JSON threshold config
    threshold_data = {
        "spike_pct": 2.5,
        "lookback_bars": 3,
        "direction": "BULLISH",
    }
    channels_data = ["TELEGRAM", "WHATSAPP"]
    targets_data = {"telegram_chat_id": "-100123456789"}

    trigger = await db.eventtrigger.create(
        data={
            "name": "Reliance Bullish Spike Watcher",
            "symbol": "TEST_RELIANCE",
            "market": "INDIAN_EQUITY",
            "timeframe": "5m",
            "triggerType": TriggerType.PRICE_SPIKE,
            "thresholdConfig": Json(threshold_data),
            "channels": Json(channels_data),
            "channelTargets": Json(targets_data),
            "status": TriggerStatus.ACTIVE,
            "createdBy": "superadmin@auratrade.com",
            "updatedBy": "superadmin@auratrade.com",
        }
    )

    assert trigger.id is not None
    assert trigger.name == "Reliance Bullish Spike Watcher"
    assert trigger.symbol == "TEST_RELIANCE"
    assert trigger.triggerType == TriggerType.PRICE_SPIKE
    assert trigger.status == TriggerStatus.ACTIVE
    assert trigger.isDeleted is False
    assert trigger.deletedAt is None
    assert trigger.createdAt is not None
    assert trigger.updatedAt is not None
    assert trigger.createdBy == "superadmin@auratrade.com"
    assert trigger.updatedBy == "superadmin@auratrade.com"

    # 2. Create a TriggerExecutionLog linked to the trigger
    log_data = {
        "triggerId": trigger.id,
        "symbol": trigger.symbol,
        "market": trigger.market,
        "timeframe": trigger.timeframe,
        "triggerType": trigger.triggerType,
        "triggerPrice": 2985.50,
        "conditionsMet": Json({"detected_spike": 2.85, "reference_price": 2902.75}),
        "candleTimestamp": datetime.now(timezone.utc),
        "channelsNotified": Json([
            {"channel": "TELEGRAM", "target": "-100123456789", "status": "SENT", "latencyMs": 85}
        ]),
        "dispatchSuccess": True,
        "latencyMs": 85,
        "createdBy": "SYSTEM",
        "updatedBy": "SYSTEM",
    }

    exec_log = await db.triggerexecutionlog.create(data=log_data)
    assert exec_log.id is not None
    assert exec_log.triggerId == trigger.id
    assert exec_log.triggerPrice == 2985.50
    assert exec_log.dispatchSuccess is True
    assert exec_log.createdAt is not None
    assert exec_log.createdBy == "SYSTEM"

    # 3. Query trigger with execution logs relation
    fetched = await db.eventtrigger.find_unique(
        where={"id": trigger.id},
        include={"executionLogs": True},
    )
    assert fetched is not None
    assert len(fetched.executionLogs) == 1
    assert fetched.executionLogs[0].id == exec_log.id

    # 4. Verify Institutional Soft-Delete
    soft_deleted = await db.eventtrigger.update(
        where={"id": trigger.id},
        data={
            "isDeleted": True,
            "deletedAt": datetime.now(timezone.utc),
            "status": TriggerStatus.DISABLED,
            "updatedBy": "operator@auratrade.com",
        },
    )
    assert soft_deleted.isDeleted is True
    assert soft_deleted.deletedAt is not None
    assert soft_deleted.updatedBy == "operator@auratrade.com"

    # 5. Verify default active filter excludes soft-deleted record
    active_triggers = await db.eventtrigger.find_many(
        where={"symbol": "TEST_RELIANCE", "isDeleted": False}
    )
    assert len(active_triggers) == 0

    # Clean up test records
    await db.triggerexecutionlog.delete_many(where={"symbol": "TEST_RELIANCE"})
    await db.eventtrigger.delete_many(where={"symbol": "TEST_RELIANCE"})

    print("\n[SUCCESS] Feature 4.1 Event Trigger Schema, Audit Columns & Soft-Delete Verified!")
