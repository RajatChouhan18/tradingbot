"""
Test: Feature 1.5 User Administration & Cash Balance Top-Up API
Verifies user creation, role reassignment, virtual cash top-up, and audit logging.
"""

import sys
import os
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from txcore.database import connect_db, disconnect_db, db
from txcore.auth.seeder import seed_system_roles_and_superadmin, DEFAULT_SUPERADMIN_EMAIL, DEFAULT_SUPERADMIN_PASSWORD
from txcore.auth.router import router as auth_router
from txcore.auth.user_router import router as user_router

app = FastAPI(title="AuraTrade User Management Test App")
app.include_router(auth_router)
app.include_router(user_router)


@pytest.mark.anyio
async def test_user_and_balance_management_api():
    await connect_db()
    await seed_system_roles_and_superadmin()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Login as SuperAdmin
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"identifier": DEFAULT_SUPERADMIN_EMAIL, "password": DEFAULT_SUPERADMIN_PASSWORD},
        )
        assert login_res.status_code == 200
        token = login_res.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. List Users
        users_res = await client.get("/api/v1/users", headers=headers)
        assert users_res.status_code == 200
        user_list = users_res.json()["users"]
        assert any(u["email"] == DEFAULT_SUPERADMIN_EMAIL for u in user_list)
        print(f"\n[SUCCESS] Listed {len(user_list)} user(s); SuperAdmin found!")

        # Find TRADER role id
        trader_role = await db.role.find_unique(where={"name": "TRADER"})
        auditor_role = await db.role.find_unique(where={"name": "AUDITOR"})
        assert trader_role is not None
        assert auditor_role is not None

        # Clean existing test user if present
        test_email = "test.trader.ops@auratrade.internal"
        existing = await db.user.find_unique(where={"email": test_email})
        if existing:
            await db.user.delete(where={"id": existing.id})

        # 3. Create new user with ₹500,000 initial balance
        create_payload = {
            "email": test_email,
            "username": "test_trader_ops",
            "password": "SecurePassword@123",
            "role_id": trader_role.id,
            "initial_balance": 500000.0,
        }
        create_res = await client.post("/api/v1/users", json=create_payload, headers=headers)
        assert create_res.status_code == 201
        created_user = create_res.json()["user"]
        user_id = created_user["id"]
        assert created_user["email"] == test_email
        assert created_user["cash_balance"] == 500000.0
        assert created_user["role"] == "TRADER"
        print(f"[SUCCESS] Created user {test_email} with balance: {created_user['cash_balance']} INR")

        # 4. Top-up cash balance by +₹150,000
        topup_payload = {
            "amount": 150000.0,
            "reason": "Test Incentive Allocation",
        }
        topup_res = await client.post(f"/api/v1/users/{user_id}/balance/topup", json=topup_payload, headers=headers)
        assert topup_res.status_code == 200
        topup_data = topup_res.json()
        assert topup_data["new_balance"] == 650000.0
        assert topup_data["previous_balance"] == 500000.0
        print(f"[SUCCESS] Top-up credited successfully: New balance = {topup_data['new_balance']} INR")

        # 5. Verify audit logs
        logs_res = await client.get(f"/api/v1/users/{user_id}/balance/logs", headers=headers)
        assert logs_res.status_code == 200
        logs = logs_res.json()["logs"]
        assert len(logs) >= 2  # 1 for initial balance + 1 for top-up
        assert logs[0]["amount"] == 150000.0
        assert logs[0]["adjusted_by"] == DEFAULT_SUPERADMIN_EMAIL
        print(f"[SUCCESS] Balance audit log verified with {len(logs)} immutable transaction entries!")

        # 6. Reassign Role to AUDITOR
        role_update_res = await client.put(
            f"/api/v1/users/{user_id}/role",
            json={"role_id": auditor_role.id},
            headers=headers,
        )
        assert role_update_res.status_code == 200
        assert role_update_res.json()["new_role"] == "AUDITOR"
        print("[SUCCESS] User role reassigned to AUDITOR successfully!")

        # Clean up test user
        await db.user.delete(where={"id": user_id})

    await disconnect_db()


if __name__ == "__main__":
    asyncio.run(test_user_and_balance_management_api())
