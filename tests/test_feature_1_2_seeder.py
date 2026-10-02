"""
Test: Feature 1.2 Password Security & SuperAdmin Auto-Seeder
Verifies PBKDF2 hashing, system roles seeding, default SuperAdmin credentials, and idempotency.
"""

import sys
import os
import pytest
import asyncio
from decimal import Decimal

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from txcore.database import connect_db, disconnect_db, db
from txcore.auth.security import hash_password, verify_password
from txcore.auth.seeder import (
    seed_system_roles_and_superadmin,
    DEFAULT_SUPERADMIN_EMAIL,
    DEFAULT_SUPERADMIN_PASSWORD,
    DEFAULT_INITIAL_BALANCE,
    MODULE_KEYS,
)


def test_password_security():
    password = "MyTestPassword@2026!"
    hashed = hash_password(password)

    # 1. Structure assertion
    assert hashed.startswith("pbkdf2:sha256:600000$")
    parts = hashed.split("$")
    assert len(parts) == 3

    # 2. Verification assertion
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False
    assert verify_password("", hashed) is False
    print("\n[SUCCESS] Password hashing and constant-time verification passed!")


@pytest.mark.anyio
async def test_seeder_and_superadmin_verification():
    await connect_db()

    # Run seeder (1st run)
    res1 = await seed_system_roles_and_superadmin()
    assert res1["status"] == "SEEDED"
    assert res1["superadmin_email"] == DEFAULT_SUPERADMIN_EMAIL

    # Assert System Roles exist
    roles = await db.role.find_many()
    role_names = [r.name for r in roles]
    assert "ADMIN" in role_names
    assert "TRADER" in role_names
    assert "AUDITOR" in role_names

    # Assert Admin role has permissions for all modules
    admin_role = await db.role.find_unique(where={"name": "ADMIN"}, include={"permissions": True})
    assert admin_role is not None
    admin_perms = {p.moduleKey: (p.canView, p.canEdit, p.canDelete) for p in admin_role.permissions}
    for m in MODULE_KEYS:
        assert m in admin_perms
        assert admin_perms[m] == (True, True, True)

    # Assert SuperAdmin User exists and credentials match
    superadmin = await db.user.find_unique(
        where={"email": DEFAULT_SUPERADMIN_EMAIL},
        include={"role": True, "balance": True},
    )
    assert superadmin is not None
    assert superadmin.email == DEFAULT_SUPERADMIN_EMAIL
    assert superadmin.role.name == "ADMIN"
    assert verify_password(DEFAULT_SUPERADMIN_PASSWORD, superadmin.passwordHash) is True

    # Assert initial cash balance
    assert superadmin.balance is not None
    assert superadmin.balance.cashBalance == DEFAULT_INITIAL_BALANCE
    assert isinstance(superadmin.balance.cashBalance, Decimal)
    print(f"\n[SUCCESS] SuperAdmin verified: {superadmin.email} with balance: {superadmin.balance.cashBalance} INR")

    # Idempotency test (2nd run)
    res2 = await seed_system_roles_and_superadmin()
    assert res2["status"] == "SEEDED"

    await disconnect_db()
    print("[SUCCESS] Seeder idempotency verified cleanly!")


if __name__ == "__main__":
    test_password_security()
    asyncio.run(test_seeder_and_superadmin_verification())
