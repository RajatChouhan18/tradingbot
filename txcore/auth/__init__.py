"""
Module 1: User & Role Management (txcore.auth)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Handles user authentication, password security (PBKDF2/bcrypt), database-stored session tokens,
dynamic role permissions matrix, and virtual cash balance management.
"""

from txcore.auth.security import hash_password, verify_password
from txcore.auth.seeder import seed_system_roles_and_superadmin, MODULE_KEYS
from txcore.auth.sessions import (
    create_user_session,
    validate_session_token,
    revoke_session,
    revoke_all_user_sessions,
)
from txcore.auth.dependencies import (
    get_current_user,
    get_current_user_optional,
    require_permission,
    extract_token_from_request,
)
from txcore.auth.router import router as auth_router
from txcore.auth.user_router import router as user_router

__all__ = [
    "hash_password",
    "verify_password",
    "seed_system_roles_and_superadmin",
    "MODULE_KEYS",
    "create_user_session",
    "validate_session_token",
    "revoke_session",
    "revoke_all_user_sessions",
    "get_current_user",
    "get_current_user_optional",
    "require_permission",
    "extract_token_from_request",
    "auth_router",
    "user_router",
]
