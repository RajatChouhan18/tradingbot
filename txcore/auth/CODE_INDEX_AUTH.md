# AuraTrade Code Index: Module 1 (Auth & User Management)

> **Repository Identifier**: `txcore.auth`  
> **Module**: Module 1: User & Role Management  
> **Source Directory**: [`txcore/auth/`](file:///e:/Txbot/txcore/auth)  
> **Role**: Authentication, database-stored session tokens, dynamic module permissions matrix, and virtual cash balance management.

---

## 1. Schema & Database Models

| Model | Table | Purpose |
|---|---|---|
| `Role` | `roles` | System roles (`ADMIN`, `TRADER`, `AUDITOR`) and dynamic user-created roles. |
| `RolePermission` | `role_permissions` | Granular per-module permissions (`MARKETVIEW`, `EVENT_TRIGGERS`, `ALGOTRADE`, `PAPER_TRADING`, `CATALOG`, `TEST_WORKBENCH`, `THEME_STUDIO`, `USER_MANAGEMENT`). |
| `User` | `users` | User credentials, password hash, role linkage, and account status. |
| `UserSession` | `user_sessions` | Database-stored cryptographic session tokens with revocation and expiry tracking. |
| `AccountBalance` | `account_balances` | Virtual cash balances enforced with `Decimal(18, 4)`. |
| `BalanceAdjustmentLog` | `balance_adjustment_logs` | Immutable audit trail for all balance modifications by SuperAdmin. |

---

## 2. Core Security & Seeding Components

| Component File | Key Functions | Description |
|---|---|---|
| [`txcore/auth/security.py`](file:///e:/Txbot/txcore/auth/security.py) | `hash_password`, `verify_password` | PBKDF2-HMAC-SHA256 hashing (600,000 iterations) with constant-time verification. |
| [`txcore/auth/seeder.py`](file:///e:/Txbot/txcore/auth/seeder.py) | `seed_system_roles_and_superadmin` | Idempotent system roles and default SuperAdmin (`rajat.18.ds@gmail.com`) seeder. |
| [`txcore/auth/sessions.py`](file:///e:/Txbot/txcore/auth/sessions.py) | `create_user_session`, `validate_session_token`, `revoke_session` | 32-byte hex token generator, SHA-256 storage in `user_sessions`, and revocation. |
| [`txcore/auth/dependencies.py`](file:///e:/Txbot/txcore/auth/dependencies.py) | `get_current_user`, `require_permission` | FastAPI dependency injectors for session extraction and module RBAC enforcement. |
| [`txcore/auth/router.py`](file:///e:/Txbot/txcore/auth/router.py) | `login`, `logout`, `get_me`, `list_roles`, `create_role`, `update_role`, `delete_role` | REST API router for auth and role matrix management. |
| [`txcore/auth/user_router.py`](file:///e:/Txbot/txcore/auth/user_router.py) | `list_users`, `create_user`, `update_user_role`, `topup_user_balance`, `get_balance_audit_logs` | REST API router for user management and cash balance top-ups with ACID audit logging. |

---

## 3. Default System Roles & SuperAdmin Baseline
- **Default SuperAdmin**:
  - Email: `rajat.18.ds@gmail.com`
  - Password: `Abcd@1234`
  - Role: `ADMIN` (100% permissions enabled)
  - Initial Balance: ₹1,000,000.0000
- **Base Roles**:
  - `ADMIN`: Full view, edit, and delete permissions across all modules.
  - `TRADER`: Full access to MarketView, Event Triggers, AlgoTrade, Paper Trading, and Theme Studio. View-only on Catalog.
  - `AUDITOR`: View-only access across modules; access to Test Workbench and Audit Logs.
