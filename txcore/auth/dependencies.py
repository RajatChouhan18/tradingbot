"""
AuraTrade Authentication & RBAC Dependencies (txcore.auth.dependencies)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Provides FastAPI dependency injectors for retrieving authenticated users
and enforcing granular module permissions via role checks.
"""

from typing import Optional, Callable
from fastapi import Request, HTTPException, status, Depends
from prisma.models import User
from txcore.auth.sessions import validate_session_token


def extract_token_from_request(request: Request) -> Optional[str]:
    """
    Extracts raw session token from 'Authorization: Bearer <token>' header
    or 'auratrade_session' cookie.
    """
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:].strip()

    cookie_token = request.cookies.get("auratrade_session")
    if cookie_token:
        return cookie_token.strip()

    return None


async def get_current_user_optional(request: Request) -> Optional[User]:
    """
    Retrieves the current authenticated user if a valid session exists,
    otherwise returns None without raising an exception.
    """
    raw_token = extract_token_from_request(request)
    if not raw_token:
        return None
    return await validate_session_token(raw_token)


async def get_current_user(request: Request) -> User:
    """
    Enforces authentication. Raises HTTP 401 Unauthorized if the session token
    is missing, expired, or revoked.
    """
    user = await get_current_user_optional(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Session token is missing, expired, or revoked.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_permission(module_key: str, action: str = "view") -> Callable:
    """
    Dependency factory that verifies whether the authenticated user's role has
    the requested module permission (action: 'view', 'edit', 'delete').
    SuperAdmin (role.name == 'ADMIN') always bypasses and is granted permission.
    """
    async def permission_checker(user: User = Depends(get_current_user)) -> User:
        if not user.role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User has no role assigned.",
            )

        # SuperAdmin override
        if user.role.name == "ADMIN":
            return user

        # Check module permission
        perms = {p.moduleKey: p for p in (user.role.permissions or [])}
        perm = perms.get(module_key)
        if not perm:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Role '{user.role.name}' does not have permission for module '{module_key}'.",
            )

        has_access = False
        if action == "view":
            has_access = perm.canView
        elif action == "edit":
            has_access = perm.canEdit
        elif action == "delete":
            has_access = perm.canDelete

        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Role '{user.role.name}' is not permitted to perform '{action}' on '{module_key}'.",
            )

        return user

    return permission_checker
