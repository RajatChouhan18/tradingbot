"""
Test: Feature 1.3 Database-Stored Session Tokens & Revocation
Verifies session creation, SHA-256 storage, retrieval, expiry, and revocation in PostgreSQL.
"""

import sys
import os
import pytest
import asyncio
from datetime import datetime, timezone, timedelta

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from txcore.database import connect_db, disconnect_db, db
from txcore.auth.seeder import seed_system_roles_and_superadmin, DEFAULT_SUPERADMIN_EMAIL
from txcore.auth.sessions import (
    create_user_session,
    validate_session_token,
    revoke_session,
    revoke_all_user_sessions,
    hash_token,
)


@pytest.mark.anyio
async def test_session_token_lifecycle():
    await connect_db()
    await seed_system_roles_and_superadmin()

    user = await db.user.find_unique(where={"email": DEFAULT_SUPERADMIN_EMAIL})
    assert user is not None

    # 1. Create active session
    raw_token = await create_user_session(
        user_id=user.id,
        ip_address="192.168.1.100",
        user_agent="PyTest-Runner",
        duration_days=7,
    )
    assert raw_token is not None
    assert len(raw_token) == 64  # 32-byte hex

    # Verify token is stored as SHA-256 hash in DB, NOT plaintext
    token_h = hash_token(raw_token)
    session_row = await db.usersession.find_unique(where={"tokenHash": token_h})
    assert session_row is not None
    assert session_row.userId == user.id
    assert session_row.revokedAt is None
    print("\n[SUCCESS] Token stored as SHA-256 hash in user_sessions table!")

    # 2. Validate valid session
    validated_user = await validate_session_token(raw_token)
    assert validated_user is not None
    assert validated_user.id == user.id
    assert validated_user.email == DEFAULT_SUPERADMIN_EMAIL
    assert validated_user.role.name == "ADMIN"
    print(f"[SUCCESS] Session validated successfully for {validated_user.email}")

    # 3. Reject tampered token
    tampered_token = raw_token[:-4] + "ffff"
    assert await validate_session_token(tampered_token) is None
    print("[SUCCESS] Tampered token rejected cleanly!")

    # 4. Reject expired token
    expired_token = await create_user_session(user_id=user.id, duration_days=-1)
    assert await validate_session_token(expired_token) is None
    print("[SUCCESS] Expired session rejected cleanly!")

    # 5. Revoke session (Logout)
    revoked = await revoke_session(raw_token)
    assert revoked is True
    assert await validate_session_token(raw_token) is None
    print("[SUCCESS] Revoked session immediately rejected upon subsequent validation!")

    # 6. Revoke all user sessions
    token1 = await create_user_session(user_id=user.id)
    token2 = await create_user_session(user_id=user.id)
    assert await validate_session_token(token1) is not None
    assert await validate_session_token(token2) is not None

    count = await revoke_all_user_sessions(user.id)
    assert count >= 2
    assert await validate_session_token(token1) is None
    assert await validate_session_token(token2) is None
    print(f"[SUCCESS] Global session revocation successfully revoked {count} sessions!")

    await disconnect_db()


if __name__ == "__main__":
    asyncio.run(test_session_token_lifecycle())
