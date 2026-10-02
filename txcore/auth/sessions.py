"""
AuraTrade Database-Stored Session Token Management (txcore.auth.sessions)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Manages cryptographically secure session tokens stored in the PostgreSQL
`user_sessions` table with SHA-256 hashing, expiration, and revocation.
"""

import hashlib
import secrets
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Any
from prisma.models import User, UserSession
from txcore.database import db, connect_db

logger = logging.getLogger("auratrade.auth.sessions")

DEFAULT_SESSION_DURATION_DAYS = 7


def hash_token(raw_token: str) -> str:
    """Computes SHA-256 hash of a raw session token."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


async def create_user_session(
    user_id: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    duration_days: int = DEFAULT_SESSION_DURATION_DAYS,
) -> str:
    """
    Generates a cryptographically random 32-byte hex token, hashes it,
    and stores the session in the `user_sessions` PostgreSQL table.
    Returns the plaintext raw token to be delivered to the client.
    """
    if not db.is_connected():
        await connect_db()

    raw_token = secrets.token_hex(32)
    token_h = hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=duration_days)

    await db.usersession.create(
        data={
            "userId": user_id,
            "tokenHash": token_h,
            "ipAddress": ip_address,
            "userAgent": user_agent,
            "expiresAt": expires_at,
        }
    )
    logger.info(f"Created active session in DB for user_id={user_id}, expires={expires_at.isoformat()}")
    return raw_token


async def validate_session_token(raw_token: str) -> Optional[User]:
    """
    Validates a raw token against the `user_sessions` table.
    Verifies that the session exists, has not been revoked, and has not expired.
    Returns the full User model with linked Role and RolePermissions if valid, else None.
    """
    if not raw_token or not isinstance(raw_token, str):
        return None

    if not db.is_connected():
        await connect_db()

    token_h = hash_token(raw_token)
    now = datetime.now(timezone.utc)

    session = await db.usersession.find_unique(
        where={"tokenHash": token_h},
        include={
            "user": {
                "include": {
                    "role": {
                        "include": {
                            "permissions": True,
                        }
                    },
                    "balance": True,
                }
            }
        },
    )

    if not session:
        return None

    # Check revocation
    if session.revokedAt is not None:
        logger.debug(f"Session rejected: Revoked at {session.revokedAt.isoformat()}")
        return None

    # Check expiration
    if session.expiresAt < now:
        logger.debug(f"Session rejected: Expired at {session.expiresAt.isoformat()}")
        return None

    # Check user active status
    if not session.user or not session.user.isActive:
        logger.debug("Session rejected: User account inactive or missing")
        return None

    return session.user


async def revoke_session(raw_token: str) -> bool:
    """
    Revokes an active session immediately by recording `revoked_at` in the database.
    """
    if not raw_token:
        return False

    if not db.is_connected():
        await connect_db()

    token_h = hash_token(raw_token)
    now = datetime.now(timezone.utc)

    try:
        session = await db.usersession.find_unique(where={"tokenHash": token_h})
        if session and session.revokedAt is None:
            await db.usersession.update(
                where={"id": session.id},
                data={"revokedAt": now},
            )
            logger.info(f"Revoked session id={session.id} for user_id={session.userId}")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to revoke session: {e}")
        return False


async def revoke_all_user_sessions(user_id: str) -> int:
    """
    Revokes all active sessions for a user (e.g. password reset or global logout).
    """
    if not db.is_connected():
        await connect_db()

    now = datetime.now(timezone.utc)
    try:
        updated = await db.usersession.update_many(
            where={"userId": user_id, "revokedAt": None},
            data={"revokedAt": now},
        )
        logger.info(f"Revoked {updated} active sessions for user_id={user_id}")
        return updated
    except Exception as e:
        logger.error(f"Failed to revoke all user sessions: {e}")
        return 0
