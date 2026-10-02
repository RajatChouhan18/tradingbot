"""
Test: Feature 1.1 Schema Verification
Validates Prisma models: Role, RolePermission, User, UserSession, AccountBalance, BalanceAdjustmentLog
with strict Decimal precision.
"""

import sys
import os
import pytest
import asyncio
from decimal import Decimal

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from txcore.database import connect_db, disconnect_db, db


@pytest.mark.anyio
async def test_feature_1_1_schema_models():
    await connect_db()

    # 1. Clean previous test runs if any
    test_user_email = "test.schema.user@auratrade.internal"
    existing_user = await db.user.find_unique(where={"email": test_user_email})
    if existing_user:
        await db.user.delete(where={"id": existing_user.id})

    existing_role = await db.role.find_unique(where={"name": "TEST_ROLE"})
    if existing_role:
        await db.role.delete(where={"id": existing_role.id})

    # 2. Create Role
    role = await db.role.create(
        data={
            "name": "TEST_ROLE",
            "description": "Test role for schema verification",
            "isSystemRole": False,
        }
    )
    assert role.id is not None
    assert role.name == "TEST_ROLE"

    # 3. Create RolePermission
    perm = await db.rolepermission.create(
        data={
            "roleId": role.id,
            "moduleKey": "MARKETVIEW",
            "canView": True,
            "canEdit": True,
            "canDelete": False,
        }
    )
    assert perm.id is not None
    assert perm.canView is True
    assert perm.canDelete is False

    # 4. Create User
    user = await db.user.create(
        data={
            "email": test_user_email,
            "username": "test_schema_user",
            "passwordHash": "dummy_pbkdf2_hash_for_test",
            "roleId": role.id,
        }
    )
    assert user.id is not None
    assert user.email == test_user_email

    # 5. Create UserSession
    from datetime import datetime, timezone, timedelta
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    session = await db.usersession.create(
        data={
            "userId": user.id,
            "tokenHash": "test_token_hash_hex_1234567890abcdef",
            "ipAddress": "127.0.0.1",
            "userAgent": "Mozilla/5.0 TestBrowser",
            "expiresAt": expires_at,
        }
    )
    assert session.id is not None
    assert session.tokenHash == "test_token_hash_hex_1234567890abcdef"

    # 6. Create AccountBalance with Decimal
    balance = await db.accountbalance.create(
        data={
            "userId": user.id,
            "cashBalance": Decimal("1000000.0000"),
            "currency": "INR",
        }
    )
    assert balance.id is not None
    assert isinstance(balance.cashBalance, Decimal)
    assert balance.cashBalance == Decimal("1000000.0000")

    # 7. Create BalanceAdjustmentLog
    log = await db.balanceadjustmentlog.create(
        data={
            "userId": user.id,
            "adjustedBy": "SuperAdmin",
            "amount": Decimal("50000.0000"),
            "balanceBefore": Decimal("1000000.0000"),
            "balanceAfter": Decimal("1050000.0000"),
            "reason": "Test Top-up Bonus",
        }
    )
    assert log.id is not None
    assert log.amount == Decimal("50000.0000")
    assert log.balanceAfter == Decimal("1050000.0000")

    # 8. Clean up
    await db.user.delete(where={"id": user.id})
    await db.role.delete(where={"id": role.id})

    await disconnect_db()
    print("\n[SUCCESS] Feature 1.1 Schema Models and Decimal Precision Verified!")


if __name__ == "__main__":
    asyncio.run(test_feature_1_1_schema_models())
