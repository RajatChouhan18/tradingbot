"""
AuraTrade Auth & Dynamic Roles API Router (txcore.auth.router)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Provides REST endpoints for user authentication (login/logout/me) and
dynamic role permissions matrix management.
"""

from typing import Dict, List, Optional, Any
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from txcore.database import db
from txcore.auth.security import verify_password
from txcore.auth.sessions import create_user_session, revoke_session
from txcore.auth.dependencies import get_current_user, require_permission, extract_token_from_request
from txcore.auth.seeder import MODULE_KEYS
from prisma.models import User

router = APIRouter(prefix="/api/v1", tags=["Authentication & Roles"])


# =========================================================================
# Request & Response Schemas
# =========================================================================
class LoginRequest(BaseModel):
    identifier: str = Field(..., description="Email or Username")
    password: str = Field(..., description="Account password")


class ModulePermissionInput(BaseModel):
    can_view: bool = False
    can_edit: bool = False
    can_delete: bool = False


class RoleCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=50, description="Unique role identifier")
    description: Optional[str] = ""
    permissions: Dict[str, ModulePermissionInput] = Field(
        default_factory=dict,
        description="Map of MODULE_KEY to view/edit/delete booleans",
    )


class RoleUpdateRequest(BaseModel):
    description: Optional[str] = None
    permissions: Optional[Dict[str, ModulePermissionInput]] = None


# =========================================================================
# 1. Authentication Endpoints
# =========================================================================
@router.post("/auth/login")
async def login(req: LoginRequest, request: Request, response: Response):
    """
    Authenticates a user via email or username + password.
    Creates a database-stored session token in PostgreSQL and sets an HTTP-only cookie.
    """
    ident = req.identifier.strip()
    user = await db.user.find_first(
        where={
            "OR": [
                {"email": ident},
                {"username": ident},
            ]
        },
        include={"role": {"include": {"permissions": True}}, "balance": True},
    )

    if not user or not user.isActive:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials or account disabled.",
        )

    if not verify_password(req.password, user.passwordHash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )

    # Extract client metadata
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    raw_token = await create_user_session(
        user_id=user.id,
        ip_address=client_ip,
        user_agent=user_agent,
    )

    # Set secure HTTP-only cookie
    response.set_cookie(
        key="auratrade_session",
        value=raw_token,
        httponly=True,
        samesite="lax",
        secure=False,  # Local dev over HTTP; can be enabled via env in production
        max_age=7 * 24 * 3600,
    )

    perms_map = {
        p.moduleKey: {"can_view": p.canView, "can_edit": p.canEdit, "can_delete": p.canDelete}
        for p in (user.role.permissions or [])
    } if user.role else {}

    cash_val = float(user.balance.cashBalance) if user.balance else 0.0

    return {
        "success": True,
        "token": raw_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "role": user.role.name if user.role else "TRADER",
            "cash_balance": cash_val,
            "currency": user.balance.currency if user.balance else "INR",
            "permissions": perms_map,
        },
    }


@router.post("/auth/logout")
async def logout(request: Request, response: Response):
    """
    Revokes the active session token in PostgreSQL and clears the HTTP-only cookie.
    """
    raw_token = extract_token_from_request(request)
    if raw_token:
        await revoke_session(raw_token)

    response.delete_cookie(key="auratrade_session")
    return {"success": True, "message": "Successfully logged out and session revoked."}


@router.get("/auth/me")
async def get_me(user: User = Depends(get_current_user)):
    """
    Returns the currently authenticated user's profile, role, permissions, and cash balance.
    """
    perms_map = {
        p.moduleKey: {"can_view": p.canView, "can_edit": p.canEdit, "can_delete": p.canDelete}
        for p in (user.role.permissions or [])
    } if user.role else {}

    cash_val = float(user.balance.cashBalance) if user.balance else 0.0

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "role": user.role.name if user.role else "TRADER",
            "is_system_role": user.role.isSystemRole if user.role else False,
            "cash_balance": cash_val,
            "currency": user.balance.currency if user.balance else "INR",
            "permissions": perms_map,
        }
    }


# =========================================================================
# 2. Dynamic Role Management Endpoints (SuperAdmin / User Management)
# =========================================================================
@router.get("/roles")
async def list_roles(current_user: User = Depends(require_permission("USER_MANAGEMENT", "view"))):
    """
    Lists all system and custom roles with their complete module permission matrix.
    """
    roles = await db.role.find_many(include={"permissions": True, "users": True})
    result = []
    for r in roles:
        perms_map = {
            p.moduleKey: {"can_view": p.canView, "can_edit": p.canEdit, "can_delete": p.canDelete}
            for p in r.permissions
        }
        result.append({
            "id": r.id,
            "name": r.name,
            "description": r.description or "",
            "is_system_role": r.isSystemRole,
            "user_count": len(r.users),
            "permissions": perms_map,
        })
    return {"roles": result, "available_modules": MODULE_KEYS}


@router.post("/roles")
async def create_role(
    req: RoleCreateRequest,
    current_user: User = Depends(require_permission("USER_MANAGEMENT", "edit")),
):
    """
    Creates a new custom role with custom module permission checkboxes.
    """
    clean_name = req.name.strip().upper()
    if clean_name in ["ADMIN", "TRADER", "AUDITOR", "VIEWER"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role name '{clean_name}' is reserved for system roles.",
        )

    existing = await db.role.find_unique(where={"name": clean_name})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A role with name '{clean_name}' already exists.",
        )

    role = await db.role.create(
        data={
            "name": clean_name,
            "description": req.description or "",
            "isSystemRole": False,
        }
    )

    # Insert permissions
    created_perms = {}
    for mod_key in MODULE_KEYS:
        input_perm = req.permissions.get(mod_key, ModulePermissionInput())
        p = await db.rolepermission.create(
            data={
                "roleId": role.id,
                "moduleKey": mod_key,
                "canView": input_perm.can_view,
                "canEdit": input_perm.can_edit,
                "canDelete": input_perm.can_delete,
            }
        )
        created_perms[mod_key] = {
            "can_view": p.canView,
            "can_edit": p.canEdit,
            "can_delete": p.canDelete,
        }

    return {
        "success": True,
        "role": {
            "id": role.id,
            "name": role.name,
            "description": role.description,
            "is_system_role": False,
            "permissions": created_perms,
        },
    }


@router.put("/roles/{role_id}")
async def update_role(
    role_id: str,
    req: RoleUpdateRequest,
    current_user: User = Depends(require_permission("USER_MANAGEMENT", "edit")),
):
    """
    Updates role description or module permission matrix.
    """
    role = await db.role.find_unique(where={"id": role_id}, include={"permissions": True})
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found.")

    if req.description is not None:
        await db.role.update(where={"id": role_id}, data={"description": req.description})

    # Update permissions if supplied
    if req.permissions:
        for mod_key, p_input in req.permissions.items():
            if mod_key in MODULE_KEYS:
                await db.rolepermission.upsert(
                    where={"roleId_moduleKey": {"roleId": role_id, "moduleKey": mod_key}},
                    data={
                        "create": {
                            "roleId": role_id,
                            "moduleKey": mod_key,
                            "canView": p_input.can_view,
                            "canEdit": p_input.can_edit,
                            "canDelete": p_input.can_delete,
                        },
                        "update": {
                            "canView": p_input.can_view,
                            "canEdit": p_input.can_edit,
                            "canDelete": p_input.can_delete,
                        },
                    },
                )

    updated_role = await db.role.find_unique(where={"id": role_id}, include={"permissions": True})
    perms_map = {
        p.moduleKey: {"can_view": p.canView, "can_edit": p.canEdit, "can_delete": p.canDelete}
        for p in updated_role.permissions
    }
    return {
        "success": True,
        "role": {
            "id": updated_role.id,
            "name": updated_role.name,
            "description": updated_role.description,
            "is_system_role": updated_role.isSystemRole,
            "permissions": perms_map,
        },
    }


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: str,
    current_user: User = Depends(require_permission("USER_MANAGEMENT", "delete")),
):
    """
    Deletes a custom role. System roles cannot be deleted.
    """
    role = await db.role.find_unique(where={"id": role_id}, include={"users": True})
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found.")

    if role.isSystemRole:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete system role '{role.name}'. System roles are protected.",
        )

    if len(role.users) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete role '{role.name}' because {len(role.users)} user(s) are assigned to it.",
        )

    await db.role.delete(where={"id": role_id})
    return {"success": True, "message": f"Role '{role.name}' deleted successfully."}
