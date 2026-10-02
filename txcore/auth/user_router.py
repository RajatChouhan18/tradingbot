"""
AuraTrade User Administration & Cash Balance Router (txcore.auth.user_router)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Provides REST endpoints for user creation, role assignment, and virtual
cash balance top-ups with ACID audit logging.
"""

from typing import List, Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from txcore.database import db
from txcore.auth.security import hash_password
from txcore.auth.dependencies import require_permission, get_current_user
from prisma.models import User

router = APIRouter(prefix="/api/v1/users", tags=["User & Cash Management"])


# =========================================================================
# Schemas
# =========================================================================
class CreateUserRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=100, description="User email address")
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    role_id: str
    initial_balance: Optional[float] = Field(default=1000000.0, ge=0)


class UpdateUserRoleRequest(BaseModel):
    role_id: str


class BalanceTopupRequest(BaseModel):
    amount: float = Field(..., description="Amount to credit (positive) or debit (negative)")
    reason: Optional[str] = Field(default="Admin Manual Adjustment")


class UpdateTerminalConfigRequest(BaseModel):
    default_market: Optional[str] = Field(default=None)
    default_symbol: Optional[str] = Field(default=None)
    default_timeframe: Optional[str] = Field(default=None)
    default_indicators: Optional[str] = Field(default=None)
    default_overlays: Optional[str] = Field(default=None)
    default_candles: Optional[str] = Field(default=None)
    default_patterns: Optional[str] = Field(default=None)


# =========================================================================
# User Management Endpoints
# =========================================================================
@router.get("")
async def list_users(current_user: User = Depends(require_permission("USER_MANAGEMENT", "view"))):
    """
    Lists all users with their assigned role and virtual cash balance.
    """
    users = await db.user.find_many(
        include={"role": True, "balance": True},
        order={"createdAt": "asc"},
    )
    result = []
    for u in users:
        cash_val = float(u.balance.cashBalance) if u.balance else 0.0
        result.append({
            "id": u.id,
            "email": u.email,
            "username": u.username,
            "is_active": u.isActive,
            "role": {
                "id": u.role.id,
                "name": u.role.name,
                "is_system_role": u.role.isSystemRole,
            } if u.role else None,
            "cash_balance": cash_val,
            "currency": u.balance.currency if u.balance else "INR",
            "created_at": u.createdAt.isoformat(),
        })
    return {"users": result}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(
    req: CreateUserRequest,
    current_user: User = Depends(require_permission("USER_MANAGEMENT", "edit")),
):
    """
    Creates a new user account, assigns a role, and initializes their cash balance.
    """
    # Verify unique email and username
    existing_email = await db.user.find_unique(where={"email": req.email})
    if existing_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already registered.")

    existing_username = await db.user.find_unique(where={"username": req.username})
    if existing_username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username is already taken.")

    # Verify role exists
    role = await db.role.find_unique(where={"id": req.role_id})
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Specified role does not exist.")

    pw_hash = hash_password(req.password)
    new_user = await db.user.create(
        data={
            "email": req.email,
            "username": req.username,
            "passwordHash": pw_hash,
            "roleId": req.role_id,
            "isActive": True,
        }
    )

    init_bal = Decimal(str(round(req.initial_balance or 1000000.0, 4)))
    balance = await db.accountbalance.create(
        data={
            "userId": new_user.id,
            "cashBalance": init_bal,
            "currency": "INR",
        }
    )

    # Initial log
    await db.balanceadjustmentlog.create(
        data={
            "userId": new_user.id,
            "adjustedBy": current_user.email,
            "amount": init_bal,
            "balanceBefore": Decimal("0.0000"),
            "balanceAfter": init_bal,
            "reason": "Account Opening Initial Balance",
        }
    )

    return {
        "success": True,
        "user": {
            "id": new_user.id,
            "email": new_user.email,
            "username": new_user.username,
            "role": role.name,
            "cash_balance": float(balance.cashBalance),
            "currency": balance.currency,
        },
    }


@router.put("/{user_id}/role")
async def update_user_role(
    user_id: str,
    req: UpdateUserRoleRequest,
    current_user: User = Depends(require_permission("USER_MANAGEMENT", "edit")),
):
    """
    Reassigns a user's role.
    """
    target_user = await db.user.find_unique(where={"id": user_id})
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    target_role = await db.role.find_unique(where={"id": req.role_id})
    if not target_role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found.")

    updated_user = await db.user.update(
        where={"id": user_id},
        data={"roleId": req.role_id},
        include={"role": True},
    )

    return {
        "success": True,
        "user_id": user_id,
        "new_role": updated_user.role.name,
    }


# =========================================================================
# Cash Balance Management Endpoints
# =========================================================================
@router.get("/{user_id}/balance")
async def get_user_balance(
    user_id: str,
    current_user: User = Depends(require_permission("USER_MANAGEMENT", "view")),
):
    """
    Retrieves the cash balance for a specified user.
    """
    balance = await db.accountbalance.find_unique(where={"userId": user_id})
    if not balance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account balance not found.")

    return {
        "user_id": user_id,
        "cash_balance": float(balance.cashBalance),
        "currency": balance.currency,
        "updated_at": balance.updatedAt.isoformat(),
    }


@router.post("/{user_id}/balance/topup")
async def topup_user_balance(
    user_id: str,
    req: BalanceTopupRequest,
    current_user: User = Depends(require_permission("USER_MANAGEMENT", "edit")),
):
    """
    Credits or debits a user's virtual cash balance with ACID audit logging.
    """
    balance_record = await db.accountbalance.find_unique(where={"userId": user_id})
    if not balance_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account balance record not found.")

    delta = Decimal(str(round(req.amount, 4)))
    current_bal = balance_record.cashBalance
    new_bal = current_bal + delta

    if new_bal < Decimal("0.0000"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Adjustment would result in negative cash balance ({new_bal} INR). Operation aborted.",
        )

    # Update balance
    updated_balance = await db.accountbalance.update(
        where={"userId": user_id},
        data={"cashBalance": new_bal},
    )

    # Record immutable audit log
    audit_entry = await db.balanceadjustmentlog.create(
        data={
            "userId": user_id,
            "adjustedBy": current_user.email,
            "amount": delta,
            "balanceBefore": current_bal,
            "balanceAfter": new_bal,
            "reason": req.reason or "Admin Manual Adjustment",
        }
    )

    return {
        "success": True,
        "user_id": user_id,
        "amount_adjusted": float(delta),
        "previous_balance": float(current_bal),
        "new_balance": float(new_bal),
        "currency": updated_balance.currency,
        "audit_log_id": audit_entry.id,
    }


@router.get("/{user_id}/balance/logs")
async def get_balance_audit_logs(
    user_id: str,
    current_user: User = Depends(require_permission("USER_MANAGEMENT", "view")),
):
    """
    Retrieves the cash balance audit history for a specified user.
    """
    logs = await db.balanceadjustmentlog.find_many(
        where={"userId": user_id},
        order={"createdAt": "desc"},
    )
    result = [
        {
            "id": log.id,
            "adjusted_by": log.adjustedBy,
            "amount": float(log.amount),
            "balance_before": float(log.balanceBefore),
            "balance_after": float(log.balanceAfter),
            "reason": log.reason,
            "created_at": log.createdAt.isoformat(),
        }
        for log in logs
    ]
    return {"user_id": user_id, "logs": result}


# =========================================================================
# User-Isolated Terminal Configuration (Feature 3.6)
# =========================================================================
@router.get("/me/terminal-config")
async def get_my_terminal_config(current_user: User = Depends(get_current_user)):
    """
    Retrieves the current authenticated user's isolated MarketView terminal configuration.
    Returns defaults if not explicitly customized yet.
    """
    config = await db.userterminalconfig.find_unique(where={"userId": current_user.id})
    if not config:
        return {
            "default_market": "INDIAN_EQUITY",
            "default_symbol": "RELIANCE",
            "default_timeframe": "5m",
            "default_indicators": "EMA_9,EMA_21,VWAP",
            "default_overlays": "EMA_9,EMA_21,VWAP",
            "default_candles": "ALL",
            "default_patterns": "ALL",
            "is_customized": False,
        }

    return {
        "id": config.id,
        "default_market": config.defaultMarket,
        "default_symbol": config.defaultSymbol,
        "default_timeframe": config.defaultTimeframe,
        "default_indicators": config.defaultOverlays,
        "default_overlays": config.defaultOverlays,
        "default_candles": config.defaultPatterns,
        "default_patterns": config.defaultPatterns,
        "is_customized": True,
        "updated_at": config.updatedAt.isoformat(),
    }


@router.put("/me/terminal-config")
async def update_my_terminal_config(
    req: UpdateTerminalConfigRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Saves and persists the authenticated user's isolated MarketView terminal preferences.
    """
    clean_market = (req.default_market.strip().upper() if req.default_market is not None else "INDIAN_EQUITY")
    clean_symbol = (req.default_symbol.strip().upper() if req.default_symbol is not None else "RELIANCE")
    clean_tf = (req.default_timeframe.strip().lower() if req.default_timeframe is not None else "5m")

    if req.default_indicators is not None:
        clean_overlays = req.default_indicators.strip()
    elif req.default_overlays is not None:
        clean_overlays = req.default_overlays.strip()
    else:
        clean_overlays = "EMA_9,EMA_21,VWAP"

    if req.default_candles is not None:
        clean_patterns = req.default_candles.strip()
    elif req.default_patterns is not None:
        clean_patterns = req.default_patterns.strip()
    else:
        clean_patterns = "ALL"

    config = await db.userterminalconfig.upsert(
        where={"userId": current_user.id},
        data={
            "create": {
                "userId": current_user.id,
                "defaultMarket": clean_market,
                "defaultSymbol": clean_symbol,
                "defaultTimeframe": clean_tf,
                "defaultOverlays": clean_overlays,
                "defaultPatterns": clean_patterns,
                "createdBy": current_user.email,
                "updatedBy": current_user.email,
            },
            "update": {
                "defaultMarket": clean_market,
                "defaultSymbol": clean_symbol,
                "defaultTimeframe": clean_tf,
                "defaultOverlays": clean_overlays,
                "defaultPatterns": clean_patterns,
                "updatedBy": current_user.email,
            },
        },
    )

    return {
        "success": True,
        "id": config.id,
        "default_market": config.defaultMarket,
        "default_symbol": config.defaultSymbol,
        "default_timeframe": config.defaultTimeframe,
        "default_indicators": config.defaultOverlays,
        "default_overlays": config.defaultOverlays,
        "default_candles": config.defaultPatterns,
        "default_patterns": config.defaultPatterns,
        "updated_at": config.updatedAt.isoformat(),
        "message": "Terminal preferences saved successfully.",
    }
