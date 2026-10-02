"""
Test: Feature 1.4 Dynamic Role Management & Auth API Endpoints
Verifies login, logout, me, and role matrix CRUD endpoints with FastAPI & httpx.
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

app = FastAPI(title="AuraTrade API Test App")
app.include_router(auth_router)


@pytest.mark.anyio
async def test_auth_and_roles_api():
    await connect_db()
    await seed_system_roles_and_superadmin()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Login with SuperAdmin credentials
        login_payload = {
            "identifier": DEFAULT_SUPERADMIN_EMAIL,
            "password": DEFAULT_SUPERADMIN_PASSWORD,
        }
        res = await client.post("/api/v1/auth/login", json=login_payload)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        token = data["token"]
        assert token is not None
        assert data["user"]["email"] == DEFAULT_SUPERADMIN_EMAIL
        assert data["user"]["role"] == "ADMIN"
        assert data["user"]["cash_balance"] >= 1000000.0
        print("\n[SUCCESS] Login endpoint validated, token generated, balance verified!")


        headers = {"Authorization": f"Bearer {token}"}

        # 2. Call /api/v1/auth/me
        me_res = await client.get("/api/v1/auth/me", headers=headers)
        assert me_res.status_code == 200
        me_data = me_res.json()["user"]
        assert me_data["email"] == DEFAULT_SUPERADMIN_EMAIL
        assert "MARKETVIEW" in me_data["permissions"]
        assert me_data["permissions"]["MARKETVIEW"]["can_view"] is True
        print("[SUCCESS] /auth/me returns active user with complete permission matrix!")

        # 3. List Roles
        roles_res = await client.get("/api/v1/roles", headers=headers)
        assert roles_res.status_code == 200
        roles_list = roles_res.json()["roles"]
        role_names = [r["name"] for r in roles_list]
        assert "ADMIN" in role_names
        assert "TRADER" in role_names
        assert "AUDITOR" in role_names
        print(f"[SUCCESS] /roles listed {len(roles_list)} roles successfully!")

        # 4. Create custom role
        new_role_payload = {
            "name": "TEST_QUANT_ROLE",
            "description": "Custom role for algorithmic quant testing",
            "permissions": {
                "MARKETVIEW": {"can_view": True, "can_edit": False, "can_delete": False},
                "ALGOTRADE": {"can_view": True, "can_edit": True, "can_delete": False},
            },
        }
        create_res = await client.post("/api/v1/roles", json=new_role_payload, headers=headers)
        assert create_res.status_code == 200
        new_role = create_res.json()["role"]
        assert new_role["name"] == "TEST_QUANT_ROLE"
        assert new_role["permissions"]["ALGOTRADE"]["can_edit"] is True
        new_role_id = new_role["id"]
        print(f"[SUCCESS] Custom role created: {new_role['name']} (id={new_role_id})")

        # 5. Attempt to delete protected system role ADMIN (should fail)
        admin_role_id = next(r["id"] for r in roles_list if r["name"] == "ADMIN")
        del_admin_res = await client.delete(f"/api/v1/roles/{admin_role_id}", headers=headers)
        assert del_admin_res.status_code == 400
        assert "Cannot delete system role" in del_admin_res.json()["detail"]
        print("[SUCCESS] Protected system role deletion prevented!")

        # 6. Delete custom role (should succeed)
        del_custom_res = await client.delete(f"/api/v1/roles/{new_role_id}", headers=headers)
        assert del_custom_res.status_code == 200
        assert del_custom_res.json()["success"] is True
        print("[SUCCESS] Custom role deleted cleanly!")

        # 7. Logout
        logout_res = await client.post("/api/v1/auth/logout", headers=headers)
        assert logout_res.status_code == 200
        assert logout_res.json()["success"] is True

        # 8. Subsequent call to /auth/me with revoked token should fail with 401
        me_after_logout = await client.get("/api/v1/auth/me", headers=headers)
        assert me_after_logout.status_code == 401
        print("[SUCCESS] Session successfully revoked on logout; subsequent access denied (401)!")

    await disconnect_db()


if __name__ == "__main__":
    asyncio.run(test_auth_and_roles_api())
