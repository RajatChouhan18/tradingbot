"""
AuraTrade Database & ORM Management (txcore.database)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Provides Prisma ORM lifecycle management, event loop detection,
and database health checks for the PostgreSQL/TimescaleDB engine.
"""

import os
import time
import asyncio
import logging
from typing import Optional, Dict, Any
from prisma import Prisma

logger = logging.getLogger("auratrade.database")

# Global Prisma Client Instance
db = Prisma(auto_register=True)
_db_loop: Optional[asyncio.AbstractEventLoop] = None


async def connect_db() -> Prisma:
    """
    Connects to PostgreSQL via Prisma ORM.
    Detects if the active asyncio event loop has changed and reconnects if necessary.
    """
    global _db_loop
    current_loop = asyncio.get_running_loop()

    if db.is_connected():
        if _db_loop is not None and (_db_loop != current_loop or _db_loop.is_closed()):
            try:
                await db.disconnect()
            except Exception as e:
                logger.warning(f"Error during disconnect before reconnect: {e}")
            await db.connect()
            _db_loop = current_loop
            logger.info("Prisma database reconnected to new active event loop.")
            return db
        return db

    logger.info("Connecting to PostgreSQL via Prisma ORM...")
    await db.connect()
    _db_loop = current_loop
    logger.info("Prisma database connection established successfully.")
    return db


async def disconnect_db() -> None:
    """Gracefully disconnects the Prisma client."""
    global _db_loop
    if db.is_connected():
        logger.info("Disconnecting Prisma database client...")
        try:
            await db.disconnect()
        except Exception as e:
            logger.warning(f"Error during database disconnect: {e}")
        _db_loop = None
        logger.info("Prisma database client disconnected.")


async def check_db_health() -> Dict[str, Any]:
    """
    Executes a ping query to assess PostgreSQL health, latency, and system info.
    """
    start_time = time.perf_counter()
    try:
        if not db.is_connected():
            await connect_db()
        raw_res = await db.query_raw("SELECT current_database(), current_user, version();")
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        info = raw_res[0] if raw_res else {}
        return {
            "status": "HEALTHY",
            "database": info.get("current_database", "unknown"),
            "user": info.get("current_user", "unknown"),
            "version": info.get("version", "unknown"),
            "latency_ms": latency_ms,
        }
    except Exception as e:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "UNHEALTHY",
            "error": str(e),
            "latency_ms": latency_ms,
        }
