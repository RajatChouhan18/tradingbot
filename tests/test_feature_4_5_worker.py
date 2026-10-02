"""
Test: Feature 4.5 Background Event Evaluation Worker & Deduplication Engine
Verifies background worker cycle, batch grouping, condition matching,
deduplication locks, and alert dispatching.
"""

import sys
import os
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock
from prisma import Json

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from txcore.database import connect_db, disconnect_db, db
from txcore.events.models import TriggerType, TriggerStatus
from txcore.events.worker import EventEvaluationWorker
from txcore.marketview.models import CandleData


@pytest.mark.anyio
async def test_worker_cycle_and_deduplication():
    await connect_db()

    # 1. Clean up old test data
    await db.triggerexecutionlog.delete_many(where={"symbol": "WORKER_TEST_SYM"})
    await db.eventtrigger.delete_many(where={"symbol": "WORKER_TEST_SYM"})

    # 2. Create 2 triggers for WORKER_TEST_SYM:
    # Trigger A: Price Spike condition that will MATCH
    trigger_a = await db.eventtrigger.create(
        data={
            "name": "Worker Spike Trigger",
            "symbol": "WORKER_TEST_SYM",
            "market": "INDIAN_EQUITY",
            "timeframe": "5m",
            "triggerType": "PRICE_SPIKE",
            "thresholdConfig": Json({"spike_pct": 1.0, "direction": "BULLISH", "lookback_bars": 2}),
            "channels": Json(["TELEGRAM"]),
            "channelTargets": Json({"telegram_chat_id": "test_chat"}),
            "status": "ACTIVE",
            "createdBy": "test@auratrade.io",
            "updatedBy": "test@auratrade.io",
        }
    )

    # Trigger B: SR Breakout condition that will NOT match
    trigger_b = await db.eventtrigger.create(
        data={
            "name": "Worker SR Trigger (No Match)",
            "symbol": "WORKER_TEST_SYM",
            "market": "INDIAN_EQUITY",
            "timeframe": "5m",
            "triggerType": "SR_BREAK",
            "thresholdConfig": Json({"level": 200.0, "break_type": "BREAKOUT"}),
            "channels": Json(["TELEGRAM"]),
            "status": "ACTIVE",
            "createdBy": "test@auratrade.io",
            "updatedBy": "test@auratrade.io",
        }
    )

    # Trigger C: Soft deleted trigger (should be ignored)
    trigger_c = await db.eventtrigger.create(
        data={
            "name": "Worker Deleted Trigger",
            "symbol": "WORKER_TEST_SYM",
            "market": "INDIAN_EQUITY",
            "timeframe": "5m",
            "triggerType": "PRICE_SPIKE",
            "thresholdConfig": Json({"spike_pct": 0.5}),
            "channels": Json(["TELEGRAM"]),
            "status": "ACTIVE",
            "isDeleted": True,
            "createdBy": "test@auratrade.io",
            "updatedBy": "test@auratrade.io",
        }
    )

    # Prepare mock candles with a bullish spike at the end
    candle_ts = datetime(2026, 10, 3, 2, 30, 0, tzinfo=timezone.utc)
    mock_candles = [
        CandleData(timestamp=datetime(2026, 10, 3, 2, 20, 0, tzinfo=timezone.utc), open=100.0, high=101.0, low=99.5, close=100.0, volume=1000.0),
        CandleData(timestamp=datetime(2026, 10, 3, 2, 25, 0, tzinfo=timezone.utc), open=100.0, high=101.5, low=99.8, close=101.0, volume=1500.0),
        CandleData(timestamp=candle_ts, open=101.0, high=105.0, low=100.5, close=104.0, volume=3000.0),
    ]

    worker = EventEvaluationWorker(poll_interval=1.0)

    # Mock provider fetch and httpx dispatcher post
    mock_post_resp = AsyncMock()
    mock_post_resp.status_code = 200
    mock_post_resp.text = "ok"

    with patch("txcore.marketview.providers.registry.provider_registry.fetch_candles_with_fallback", return_value=mock_candles):
        with patch("httpx.AsyncClient.post", return_value=mock_post_resp):
            # 3. First Evaluation Cycle
            stats1 = await worker.evaluate_cycle()
            assert stats1["active_triggers"] >= 2
            assert stats1["evaluated"] >= 2
            assert stats1["dispatched"] >= 1
            print(f"\n[SUCCESS] Cycle 1 Stats: {stats1}")

            # Verify trigger A was updated with lastTriggeredAt and triggerCount
            updated_a = await db.eventtrigger.find_unique(where={"id": trigger_a.id})
            assert updated_a.triggerCount == 1
            assert updated_a.lastTriggeredAt is not None

            # Verify execution log exists
            logs = await db.triggerexecutionlog.find_many(where={"triggerId": trigger_a.id})
            assert len(logs) == 1
            assert logs[0].triggerPrice == 104.0
            assert logs[0].dispatchSuccess is True

            # 4. Second Evaluation Cycle with the SAME candle data (Deduplication Check)
            stats2 = await worker.evaluate_cycle()
            assert stats2["active_triggers"] >= 2

            # Verify count on trigger A was NOT incremented due to deduplication
            reloaded_a = await db.eventtrigger.find_unique(where={"id": trigger_a.id})
            assert reloaded_a.triggerCount == 1
            logs_after_2 = await db.triggerexecutionlog.find_many(where={"triggerId": trigger_a.id})
            assert len(logs_after_2) == 1
            print(f"[SUCCESS] Cycle 2 Deduplication verified: triggerCount={reloaded_a.triggerCount}")

            # 5. Third Evaluation Cycle with a NEW candle timestamp
            new_candle_ts = datetime(2026, 10, 3, 2, 35, 0, tzinfo=timezone.utc)
            new_mock_candles = mock_candles + [
                CandleData(timestamp=new_candle_ts, open=104.0, high=108.0, low=103.5, close=107.0, volume=4000.0)
            ]

    with patch("txcore.marketview.providers.registry.provider_registry.fetch_candles_with_fallback", return_value=new_mock_candles):
        with patch("httpx.AsyncClient.post", return_value=mock_post_resp):
            stats3 = await worker.evaluate_cycle()
            final_a = await db.eventtrigger.find_unique(where={"id": trigger_a.id})
            assert final_a.triggerCount == 2
            logs_after_3 = await db.triggerexecutionlog.find_many(where={"triggerId": trigger_a.id})
            assert len(logs_after_3) == 2
            print(f"[SUCCESS] Cycle 3 with new candle timestamp dispatched: triggerCount={final_a.triggerCount}")


    # Clean up test data
    await db.triggerexecutionlog.delete_many(where={"symbol": "WORKER_TEST_SYM"})
    await db.eventtrigger.delete_many(where={"symbol": "WORKER_TEST_SYM"})
    print("[SUCCESS] Feature 4.5 Worker and Deduplication verified with 100% test pass!")
