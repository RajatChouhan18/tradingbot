"""
AuraTrade System Roles & SuperAdmin Seeder (txcore.auth.seeder)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Idempotently seeds system roles (ADMIN, TRADER, AUDITOR) with complete
module permission matrices, and ensures the default SuperAdmin exists
with ₹1,000,000.0000 virtual cash balance.
"""

import logging
from decimal import Decimal
from typing import Dict, Any, List
from txcore.database import db, connect_db
from txcore.auth.security import hash_password

logger = logging.getLogger("auratrade.auth.seeder")

MODULE_KEYS = [
    "MARKETVIEW",
    "EVENT_TRIGGERS",
    "ALGOTRADE",
    "PAPER_TRADING",
    "CATALOG",
    "TEST_WORKBENCH",
    "THEME_STUDIO",
    "USER_MANAGEMENT",
]

DEFAULT_SUPERADMIN_EMAIL = "rajat.18.ds@gmail.com"
DEFAULT_SUPERADMIN_USERNAME = "rajat_admin"
DEFAULT_SUPERADMIN_PASSWORD = "Abcd@1234"
DEFAULT_INITIAL_BALANCE = Decimal("1000000.0000")


async def seed_system_roles_and_superadmin() -> Dict[str, Any]:
    """
    Idempotent seeding routine that creates system roles, their module permissions,
    and the default SuperAdmin account.
    """
    if not db.is_connected():
        await connect_db()

    # 1. Seed Roles
    roles_def = [
        {
            "name": "ADMIN",
            "description": "Full institutional administrator with unconstrained access across all modules",
            "is_system_role": True,
            "permissions": {mod: (True, True, True) for mod in MODULE_KEYS},
        },
        {
            "name": "TRADER",
            "description": "Standard trading operator with access to MarketView, Event Triggers, AlgoTrade, and Paper Trading",
            "is_system_role": True,
            "permissions": {
                "MARKETVIEW": (True, True, False),
                "EVENT_TRIGGERS": (True, True, True),
                "ALGOTRADE": (True, True, True),
                "PAPER_TRADING": (True, True, True),
                "CATALOG": (True, False, False),
                "THEME_STUDIO": (True, True, False),
                "TEST_WORKBENCH": (False, False, False),
                "USER_MANAGEMENT": (False, False, False),
            },
        },
        {
            "name": "AUDITOR",
            "description": "Compliance and risk auditor with read-only access to trading and access to test suites",
            "is_system_role": True,
            "permissions": {
                "MARKETVIEW": (True, False, False),
                "EVENT_TRIGGERS": (True, False, False),
                "ALGOTRADE": (True, False, False),
                "PAPER_TRADING": (True, False, False),
                "CATALOG": (True, False, False),
                "THEME_STUDIO": (True, False, False),
                "TEST_WORKBENCH": (True, True, False),
                "USER_MANAGEMENT": (False, False, False),
            },
        },
    ]

    role_records = {}
    for r_def in roles_def:
        role = await db.role.find_unique(where={"name": r_def["name"]})
        if not role:
            role = await db.role.create(
                data={
                    "name": r_def["name"],
                    "description": r_def["description"],
                    "isSystemRole": r_def["is_system_role"],
                }
            )
            logger.info(f"Created system role: {role.name}")
        role_records[r_def["name"]] = role

        # Seed / Sync permissions
        for mod_key, (c_view, c_edit, c_del) in r_def["permissions"].items():
            existing_perm = await db.rolepermission.find_unique(
                where={"roleId_moduleKey": {"roleId": role.id, "moduleKey": mod_key}}
            )
            if not existing_perm:
                await db.rolepermission.create(
                    data={
                        "roleId": role.id,
                        "moduleKey": mod_key,
                        "canView": c_view,
                        "canEdit": c_edit,
                        "canDelete": c_del,
                    }
                )

    # 2. Seed Default SuperAdmin
    admin_role = role_records["ADMIN"]
    superadmin = await db.user.find_unique(where={"email": DEFAULT_SUPERADMIN_EMAIL})
    if not superadmin:
        pw_hash = hash_password(DEFAULT_SUPERADMIN_PASSWORD)
        superadmin = await db.user.create(
            data={
                "email": DEFAULT_SUPERADMIN_EMAIL,
                "username": DEFAULT_SUPERADMIN_USERNAME,
                "passwordHash": pw_hash,
                "roleId": admin_role.id,
                "isActive": True,
            }
        )
        logger.info(f"Default SuperAdmin created: {superadmin.email}")

        # Seed initial cash balance
        await db.accountbalance.create(
            data={
                "userId": superadmin.id,
                "cashBalance": DEFAULT_INITIAL_BALANCE,
                "currency": "INR",
            }
        )
        logger.info(f"Initial cash balance seeded for SuperAdmin: {DEFAULT_INITIAL_BALANCE} INR")
    else:
        # Verify balance exists
        balance = await db.accountbalance.find_unique(where={"userId": superadmin.id})
        if not balance:
            await db.accountbalance.create(
                data={
                    "userId": superadmin.id,
                    "cashBalance": DEFAULT_INITIAL_BALANCE,
                    "currency": "INR",
                }
            )

    return {
        "status": "SEEDED",
        "superadmin_email": superadmin.email,
        "superadmin_role": admin_role.name,
        "roles_seeded": list(role_records.keys()),
    }
