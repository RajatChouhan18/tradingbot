"""
Test: Feature 4.4 REST API & Instant Simulator
Verifies Event Trigger REST endpoints: CRUD, status toggling, soft-delete,
execution logs retrieval, and dry-run rule simulation.
"""

import sys
import os
import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
from datetime import datetime, timezone

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from txcore.database import connect_db, disconnect_db, db
from prisma import Json
from txcore.auth.seeder import seed_system_roles_and_superadmin, DEFAULT_SUPERADMIN_EMAIL, DEFAULT_SUPERADMIN_PASSWORD
from txcore.auth.router import router as auth_router
from txcore.events.router import events_router


app = FastAPI(title="AuraTrade API Test App")
app.include_router(auth_router)
app.include_router(events_router)


@pytest.mark.anyio
async def test_event_triggers_api_full_flow():
    await connect_db()
    await seed_system_roles_and_superadmin()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Login to obtain SuperAdmin JWT
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"identifier": DEFAULT_SUPERADMIN_EMAIL, "password": DEFAULT_SUPERADMIN_PASSWORD},
        )
        assert login_res.status_code == 200
        token = login_res.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Clean up any previous test triggers
        await db.triggerexecutionlog.delete_many(where={"symbol": "API_TEST_SYM"})
        await db.eventtrigger.delete_many(where={"symbol": "API_TEST_SYM"})

        # 3. Create Event Trigger via POST /api/v1/events
        create_payload = {
            "name": "API Test Price Spike",
            "symbol": "API_TEST_SYM",
            "market": "INDIAN_EQUITY",
            "timeframe": "5m",
            "trigger_type": "PRICE_SPIKE",
            "conditions": {
                "spike_pct": 2.5,
                "direction": "BULLISH",
                "lookback_bars": 3,
            },
            "channels": ["TELEGRAM", "WEBHOOK"],
            "notes": "Testing event trigger API creation",
            "is_standalone": True,
        }
        res = await client.post("/api/v1/events", json=create_payload, headers=headers)
        assert res.status_code == 201, res.text
        created_data = res.json()
        assert created_data["name"] == "API Test Price Spike"
        assert created_data["symbol"] == "API_TEST_SYM"
        assert created_data["trigger_type"] == "PRICE_SPIKE"
        assert created_data["status"] == "ACTIVE"
        assert "TELEGRAM" in created_data["channels"]
        trigger_id = created_data["id"]
        assert trigger_id is not None
        print(f"\n[SUCCESS] Created Trigger ID: {trigger_id}")

        # 4. List Event Triggers via GET /api/v1/events
        list_res = await client.get("/api/v1/events?search=API_TEST_SYM", headers=headers)
        assert list_res.status_code == 200
        list_data = list_res.json()
        assert any(t["id"] == trigger_id for t in list_data)
        print(f"[SUCCESS] Listed {len(list_data)} triggers with search query")

        # 5. Get Trigger Details via GET /api/v1/events/{id}
        get_res = await client.get(f"/api/v1/events/{trigger_id}", headers=headers)
        assert get_res.status_code == 200
        trigger_detail = get_res.json()
        assert trigger_detail["id"] == trigger_id
        assert trigger_detail["threshold_config"]["spike_pct"] == 2.5

        # 6. Update Event Trigger via PUT /api/v1/events/{id}
        update_payload = {
            "name": "API Test Price Spike - Updated",
            "timeframe": "15m",
            "conditions": {
                "spike_pct": 3.0,
                "direction": "BULLISH",
                "lookback_bars": 5,
            },
            "channels": ["TELEGRAM", "WHATSAPP"],
            "status": "PAUSED",
        }
        put_res = await client.put(f"/api/v1/events/{trigger_id}", json=update_payload, headers=headers)
        assert put_res.status_code == 200
        updated_data = put_res.json()
        assert updated_data["name"] == "API Test Price Spike - Updated"
        assert updated_data["timeframe"] == "15m"
        assert updated_data["status"] == "PAUSED"
        assert "WHATSAPP" in updated_data["channels"]
        print("[SUCCESS] Updated trigger successfully")

        # 7. Quick Status Toggle via PATCH /api/v1/events/{id}/status
        patch_res = await client.patch(
            f"/api/v1/events/{trigger_id}/status",
            json={"status": "ACTIVE"},
            headers=headers,
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["status"] == "ACTIVE"
        print("[SUCCESS] Toggled trigger status to ACTIVE")

        # 8. Instant Simulation via POST /api/v1/events/simulate with real benchmark
        sim_payload = {
            "symbol": "RELIANCE",
            "market": "INDIAN_EQUITY",
            "timeframe": "5m",
            "trigger_type": "PRICE_SPIKE",
            "threshold_config": {"spike_pct": 0.001, "direction": "ANY", "lookback_bars": 3},
        }
        sim_res = await client.post("/api/v1/events/simulate", json=sim_payload, headers=headers)
        assert sim_res.status_code == 200, sim_res.text
        sim_data = sim_res.json()
        assert "matched" in sim_data
        assert sim_data["symbol"] == "RELIANCE"
        assert sim_data["latency_ms"] >= 0
        print(f"[SUCCESS] Live Simulation Result: {sim_data['evaluation_message']}")

        # 9. Test Trigger on existing trigger via POST /api/v1/events/{id}/test
        # First update trigger to use RELIANCE so provider can fetch live data
        await client.put(f"/api/v1/events/{trigger_id}", json={"symbol": "RELIANCE", "market": "INDIAN_EQUITY"}, headers=headers)
        test_res = await client.post(f"/api/v1/events/{trigger_id}/test?send_alert=false", headers=headers)
        assert test_res.status_code == 200, test_res.text
        test_data = test_res.json()
        assert "matched" in test_data
        print("[SUCCESS] Test Trigger endpoint executed successfully")


        # 10. Query Execution Logs via GET /api/v1/events/{trigger_id}/logs
        # First manually record a sample log
        await db.triggerexecutionlog.create(
            data={
                "triggerId": trigger_id,
                "symbol": "API_TEST_SYM",
                "market": "INDIAN_EQUITY",
                "timeframe": "5m",
                "candleTimestamp": datetime.now(timezone.utc),
                "triggerType": "PRICE_SPIKE",
                "triggerPrice": 105.0,
                "conditionsMet": '{"spike_pct": 3.96}',
                "channelsNotified": Json([{"channel": "TELEGRAM", "status": "SENT", "latency_ms": 45}]),
                "dispatchSuccess": True,
                "latencyMs": 58,
            }
        )


        logs_res = await client.get(f"/api/v1/events/{trigger_id}/logs", headers=headers)
        assert logs_res.status_code == 200
        logs = logs_res.json()
        assert len(logs) >= 1
        assert logs[0]["dispatch_success"] is True
        assert logs[0]["trigger_price"] == 105.0
        print(f"[SUCCESS] Retrieved {len(logs)} execution logs")


        # 11. Soft-Delete Trigger via DELETE /api/v1/events/{id}
        del_res = await client.delete(f"/api/v1/events/{trigger_id}", headers=headers)
        assert del_res.status_code == 200
        assert del_res.json()["success"] is True

        # Verify soft deletion in DB
        db_record = await db.eventtrigger.find_unique(where={"id": trigger_id})
        assert db_record is not None
        assert db_record.isDeleted is True
        assert db_record.status == "DISABLED"
        assert db_record.deletedAt is not None

        # Verify excluded from normal list
        list_after = await client.get("/api/v1/events?search=API_TEST_SYM", headers=headers)
        assert list_after.status_code == 200
        assert not any(t["id"] == trigger_id for t in list_after.json())
        print("[SUCCESS] Soft-delete verified: excluded from list, record preserved in DB!")
