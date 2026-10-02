"""
txcore.persistence
~~~~~~~~~~~~~~~~~~
Thread-safe Prisma ORM database persistence bridge for the TxBot AlgoTrade platform.
Uses a dedicated background database worker thread with a persistent asyncio event loop.
This guarantees:
  - Zero event loop collision or 'Event loop is closed' errors across worker threads
  - Seamless support for both synchronous thread-pool execution and async FastAPI routes
  - Non-blocking fire-and-forget dispatching for signals, PnL, audits, and structured logs
  - Graceful fallback: trading pipelines never halt if PostgreSQL is offline or restarting
"""

import os
import json
import logging
import asyncio
import threading
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Union

from prisma import Prisma, Json

logger = logging.getLogger("txcore.persistence")


class DedicatedDBWorker:
    """
    Dedicated background worker running a permanent asyncio event loop
    with its own Prisma ORM client instance.
    """

    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, daemon=True, name="DedicatedDBWorkerThread")
        self.thread.start()
        self.db = Prisma(auto_register=False)
        self._connected = False
        self._lock = threading.Lock()

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def ensure_connected(self):
        """Ensures Prisma client is connected inside the dedicated worker loop."""
        if not self._connected:
            with self._lock:
                if not self._connected:
                    async def _conn():
                        if not self.db.is_connected():
                            await self.db.connect()

                    fut = asyncio.run_coroutine_threadsafe(_conn(), self.loop)
                    try:
                        fut.result(timeout=10.0)
                        self._connected = True
                        logger.info("Dedicated DB worker connected to PostgreSQL via Prisma ORM.")
                    except Exception as e:
                        logger.debug(f"DB worker connection deferred/offline: {e}")

    def run_sync(self, coro, timeout: float = 15.0):
        """Executes a coroutine inside the worker loop and synchronously waits for result."""
        self.ensure_connected()
        fut = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return fut.result(timeout=timeout)

    async def run_async(self, coro):
        """Executes a coroutine inside the worker loop and asynchronously awaits result from another loop."""
        self.ensure_connected()
        fut = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return await asyncio.wrap_future(fut)

    def submit(self, coro):
        """Fire-and-forget submission of a coroutine into the worker loop."""
        self.ensure_connected()
        asyncio.run_coroutine_threadsafe(coro, self.loop)


# Global Singleton Database Worker
db_worker = DedicatedDBWorker()

# Fast in-memory cache mapping business algo_id -> Prisma UUID
_ALGO_ID_TO_UUID: Dict[str, str] = {}
_DEFAULT_USER_ID: Optional[str] = None


# =============================================================================
# 1. USER HELPERS
# =============================================================================

async def _get_or_create_default_user_impl() -> Optional[str]:
    global _DEFAULT_USER_ID
    if _DEFAULT_USER_ID:
        return _DEFAULT_USER_ID

    try:
        if not db_worker.db.is_connected():
            await db_worker.db.connect()

        user = await db_worker.db.user.find_first()
        if user:
            _DEFAULT_USER_ID = user.id
            return user.id

        import hashlib
        pwd_hash = hashlib.sha256("Admin@123".encode()).hexdigest()
        new_user = await db_worker.db.user.create(
            data={
                "username": "admin",
                "email": "admin@txbot.local",
                "passwordHash": pwd_hash,
                "role": "ADMIN",
            }
        )
        _DEFAULT_USER_ID = new_user.id
        return new_user.id
    except Exception as e:
        logger.debug(f"User retrieval fallback: {e}")
        return None


async def get_or_create_default_user() -> Optional[str]:
    """Retrieves default user ID safely across loops."""
    try:
        return await db_worker.run_async(_get_or_create_default_user_impl())
    except Exception:
        return None


# =============================================================================
# 2. ALGOTRADE STRATEGY PERSISTENCE & HYDRATION
# =============================================================================

async def _save_algo_to_db_impl(algo, user_id: Optional[str] = None) -> Optional[str]:
    try:
        uid = user_id or await _get_or_create_default_user_impl()
        if not uid:
            return None

        cfg = getattr(algo, "config", algo)
        algo_id = getattr(cfg, "algo_id", "") or getattr(algo, "algo_id", "")
        algo_name = getattr(cfg, "algo_name", "") or getattr(algo, "algo_name", "AlgoTrade")
        market = (getattr(cfg, "market", "INDIAN_EQUITY") or "INDIAN_EQUITY").upper()
        timeframe = getattr(cfg, "timeframe", "5m") or "5m"
        symbols = getattr(cfg, "symbols", []) or []
        indices = getattr(cfg, "indices", []) or []
        indicators = getattr(cfg, "indicators", []) or []
        patterns = getattr(cfg, "patterns", []) or []
        risk_reward = float(getattr(cfg, "risk_reward_ratio", 1.5))
        start_time = getattr(cfg, "start_time", None)
        stop_time = getattr(cfg, "stop_time", None)
        start_date = getattr(cfg, "start_date", None)
        end_date = getattr(cfg, "end_date", None)
        chart_enabled = bool(getattr(cfg, "chart_enabled", True))
        audit_enabled = bool(getattr(cfg, "audit_enabled", True))
        desc = getattr(cfg, "description", "") or ""
        is_deleted = bool(getattr(cfg, "is_deleted", False))

        status_val = getattr(getattr(algo, "status", None), "value", "IDLE")
        if status_val not in ("IDLE", "RUNNING", "PAUSED", "STOPPED", "ERROR"):
            status_val = "IDLE"

        record = await db_worker.db.algotrade.upsert(
            where={"algoId": algo_id},
            data={
                "create": {
                    "algoId": algo_id,
                    "userId": uid,
                    "algoName": algo_name,
                    "market": market,
                    "timeframe": timeframe,
                    "symbols": Json(symbols),
                    "indices": Json(indices),
                    "indicators": Json(indicators),
                    "patterns": Json(patterns),
                    "riskRewardRatio": risk_reward,
                    "status": status_val,
                    "startTime": start_time,
                    "stopTime": stop_time,
                    "startDate": start_date,
                    "endDate": end_date,
                    "chartEnabled": chart_enabled,
                    "auditEnabled": audit_enabled,
                    "description": desc,
                    "isDeleted": is_deleted,
                },
                "update": {
                    "algoName": algo_name,
                    "market": market,
                    "timeframe": timeframe,
                    "symbols": Json(symbols),
                    "indices": Json(indices),
                    "indicators": Json(indicators),
                    "patterns": Json(patterns),
                    "riskRewardRatio": risk_reward,
                    "status": status_val,
                    "startTime": start_time,
                    "stopTime": stop_time,
                    "startDate": start_date,
                    "endDate": end_date,
                    "chartEnabled": chart_enabled,
                    "auditEnabled": audit_enabled,
                    "description": desc,
                    "isDeleted": is_deleted,
                },
            },
        )
        _ALGO_ID_TO_UUID[algo_id] = record.id
        if hasattr(algo, "db_id"):
            algo.db_id = record.id
        return record.id
    except Exception as e:
        logger.debug(f"Failed to persist AlgoTrade to DB: {e}")
        return None


async def save_algo_to_db(algo, user_id: Optional[str] = None) -> Optional[str]:
    """Persists an AlgoTrade safely inside the dedicated worker loop."""
    return await db_worker.run_async(_save_algo_to_db_impl(algo, user_id=user_id))


async def _get_algo_db_uuid_impl(algo_id: str) -> Optional[str]:
    if algo_id in _ALGO_ID_TO_UUID:
        return _ALGO_ID_TO_UUID[algo_id]

    try:
        record = await db_worker.db.algotrade.find_unique(where={"algoId": algo_id})
        if record:
            _ALGO_ID_TO_UUID[algo_id] = record.id
            return record.id
    except Exception:
        pass
    return None


async def load_algos_from_db(manager) -> int:
    """Hydrates existing active AlgoTrades from PostgreSQL into runtime manager."""
    async def _impl():
        try:
            records = await db_worker.db.algotrade.find_many(where={"isDeleted": False})
            if not records:
                return 0

            from txcore.algotrade import AlgoTradeConfig, AlgoTradeStatus
            loaded = 0
            for rec in records:
                _ALGO_ID_TO_UUID[rec.algoId] = rec.id
                if rec.algoId in manager._algos:
                    continue

                symbols = rec.symbols if isinstance(rec.symbols, list) else []
                indices = rec.indices if isinstance(rec.indices, list) else []
                indicators = rec.indicators if isinstance(rec.indicators, list) else []
                patterns = rec.patterns if isinstance(rec.patterns, list) else []

                cfg = AlgoTradeConfig(
                    algo_name=rec.algoName,
                    market=rec.market,
                    timeframe=rec.timeframe,
                    symbols=symbols,
                    indices=indices,
                    indicators=indicators,
                    patterns=patterns,
                    risk_reward_ratio=float(rec.riskRewardRatio),
                    start_time=rec.startTime,
                    stop_time=rec.stopTime,
                    start_date=rec.startDate,
                    end_date=rec.endDate,
                    chart_enabled=rec.chartEnabled,
                    audit_enabled=rec.auditEnabled,
                    description=rec.description or "",
                    is_deleted=rec.isDeleted,
                    algo_id=rec.algoId,
                )

                algo = manager.register_algo(cfg)
                algo.db_id = rec.id
                try:
                    algo.status = AlgoTradeStatus(rec.status)
                except Exception:
                    algo.status = AlgoTradeStatus.IDLE
                loaded += 1
            return loaded
        except Exception as e:
            logger.debug(f"Hydration fallback: {e}")
            return 0

    return await db_worker.run_async(_impl())


async def update_algo_status_in_db(algo_id: str, status: str) -> bool:
    async def _impl():
        try:
            await db_worker.db.algotrade.update(
                where={"algoId": algo_id},
                data={"status": status},
            )
            return True
        except Exception:
            return False

    return await db_worker.run_async(_impl())


async def delete_algo_in_db(algo_id: str, hard: bool = False) -> bool:
    async def _impl():
        try:
            if hard:
                await db_worker.db.algotrade.delete(where={"algoId": algo_id})
            else:
                await db_worker.db.algotrade.update(
                    where={"algoId": algo_id},
                    data={"isDeleted": True, "status": "STOPPED"},
                )
            return True
        except Exception:
            return False

    return await db_worker.run_async(_impl())


# =============================================================================
# 3. SIGNAL & AUDIT PERSISTENCE
# =============================================================================

async def _save_signal_to_db_impl(signal_record: Dict[str, Any]) -> Optional[str]:
    try:
        algo_id = signal_record.get("algo_id", "")
        db_uuid = await _get_algo_db_uuid_impl(algo_id)
        if not db_uuid:
            return None

        sig_id = signal_record.get("signal_id") or signal_record.get("id") or f"SIG-{signal_record.get('symbol')}-{int(datetime.now().timestamp()*1000)}"
        direction = signal_record.get("direction", "CALL").upper()
        if direction not in ("CALL", "PUT", "NEUTRAL"):
            direction = "CALL"

        status_str = signal_record.get("status", "APPROVED").upper()
        if status_str not in ("APPROVED", "BLOCKED", "REJECTED", "PENDING"):
            status_str = "APPROVED"

        candle_time_raw = signal_record.get("candle_time")
        if isinstance(candle_time_raw, str):
            try:
                candle_dt = datetime.fromisoformat(candle_time_raw.replace("Z", "+00:00"))
            except Exception:
                candle_dt = datetime.now(timezone.utc)
        elif isinstance(candle_time_raw, datetime):
            candle_dt = candle_time_raw
        else:
            candle_dt = datetime.now(timezone.utc)

        metadata = {
            "atr": signal_record.get("atr"),
            "mtf_trend": signal_record.get("mtf_trend"),
            "risk_reward": signal_record.get("risk_reward"),
            "pnl_pct": signal_record.get("pnl_pct"),
            "pnl_points": signal_record.get("pnl_points"),
            "outcome": signal_record.get("outcome"),
            "dispatched": signal_record.get("dispatched", False),
        }

        record = await db_worker.db.signal.upsert(
            where={"signalId": sig_id},
            data={
                "create": {
                    "signalId": sig_id,
                    "algoTradeId": db_uuid,
                    "symbol": signal_record.get("symbol", ""),
                    "direction": direction,
                    "pattern": signal_record.get("pattern", "Technical Breakout"),
                    "price": float(signal_record.get("price", 0.0)),
                    "level": float(signal_record.get("level", 0.0)),
                    "stopLoss": float(signal_record.get("stop_loss", 0.0)),
                    "target": float(signal_record.get("target", 0.0)),
                    "timeframe": signal_record.get("timeframe", "5m"),
                    "provider": signal_record.get("algo_name", "TxBot"),
                    "newsStatus": "CLEAR",
                    "status": status_str,
                    "reason": signal_record.get("pattern", ""),
                    "chartPath": signal_record.get("chart_path"),
                    "auditChartPath": signal_record.get("audit_chart_path"),
                    "metadata": Json(metadata),
                    "candleTime": candle_dt,
                },
                "update": {
                    "status": status_str,
                    "chartPath": signal_record.get("chart_path"),
                    "auditChartPath": signal_record.get("audit_chart_path"),
                    "metadata": Json(metadata),
                },
            },
        )
        return record.id
    except Exception as e:
        logger.debug(f"Signal persistence fallback: {e}")
        return None


async def save_signal_to_db(signal_record: Dict[str, Any]) -> Optional[str]:
    return await db_worker.run_async(_save_signal_to_db_impl(signal_record))


async def _save_pnl_trade_to_db_impl(pnl_record: Dict[str, Any]) -> Optional[str]:
    try:
        algo_id = pnl_record.get("algo_id", "")
        db_uuid = await _get_algo_db_uuid_impl(algo_id)
        if not db_uuid:
            return None

        direction = pnl_record.get("direction", "CALL").upper()
        if direction not in ("CALL", "PUT", "NEUTRAL"):
            direction = "CALL"

        outcome = pnl_record.get("outcome", "WIN").upper()
        if outcome not in ("WIN", "LOSS", "TIMEOUT"):
            outcome = "WIN"

        signal_db_id = None
        sig_id = pnl_record.get("signal_id")
        if sig_id:
            sig = await db_worker.db.signal.find_unique(where={"signalId": sig_id})
            if sig:
                signal_db_id = sig.id

        now = datetime.now(timezone.utc)
        record = await db_worker.db.pnltrade.create(
            data={
                "algoTradeId": db_uuid,
                "signalId": signal_db_id,
                "symbol": pnl_record.get("symbol", ""),
                "direction": direction,
                "pattern": pnl_record.get("pattern", "Price Action"),
                "entryPrice": float(pnl_record.get("entry_price", 0.0)),
                "exitPrice": float(pnl_record.get("exit_price", 0.0)),
                "pnlPct": float(pnl_record.get("pnl_pct", 0.0)),
                "pnlPoints": float(pnl_record.get("pnl_points", 0.0)),
                "outcome": outcome,
                "holdingBars": int(pnl_record.get("holding_bars", 1)),
                "entryTime": now,
                "exitTime": now,
            }
        )
        return record.id
    except Exception as e:
        logger.debug(f"PnL persistence fallback: {e}")
        return None


async def save_pnl_trade_to_db(pnl_record: Dict[str, Any]) -> Optional[str]:
    return await db_worker.run_async(_save_pnl_trade_to_db_impl(pnl_record))


async def _save_audit_event_to_db_impl(event: Dict[str, Any]) -> Optional[str]:
    try:
        algo_id = event.get("algo_id", "")
        db_uuid = await _get_algo_db_uuid_impl(algo_id)
        if not db_uuid:
            first = await db_worker.db.algotrade.find_first()
            if first:
                db_uuid = first.id
                _ALGO_ID_TO_UUID[first.algoId] = first.id

        if not db_uuid:
            return None

        indicator_snap = event.get("indicator_snapshot") or {}
        level_snap = event.get("level_snapshot") or {}

        record = await db_worker.db.auditevent.create(
            data={
                "algoTradeId": db_uuid,
                "symbol": event.get("symbol", ""),
                "eventType": event.get("event_type", "CYCLE_SCAN"),
                "indicatorSnapshot": Json(indicator_snap),
                "levelSnapshot": Json(level_snap),
                "decisionReason": str(event.get("decision_reason", "")),
                "latencyMs": int(event.get("latency_ms", 0)),
            }
        )
        return record.id
    except Exception as e:
        logger.debug(f"Audit event persistence fallback: {e}")
        return None


async def save_audit_event_to_db(event: Dict[str, Any]) -> Optional[str]:
    return await db_worker.run_async(_save_audit_event_to_db_impl(event))


async def _save_structured_log_to_db_impl(
    level: str,
    source: str,
    message: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    try:
        record = await db_worker.db.structuredlog.create(
            data={
                "level": level.upper(),
                "source": source.lower(),
                "message": message,
                "metadata": Json(metadata) if metadata else None,
            }
        )
        return record.id
    except Exception as e:
        logger.debug(f"Structured log persistence fallback: {e}")
        return None


async def save_structured_log_to_db(
    level: str,
    source: str,
    message: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    return await db_worker.run_async(_save_structured_log_to_db_impl(level, source, message, metadata))


async def get_audit_events_from_db(
    algo_id: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    async def _impl():
        try:
            where_clause: Dict[str, Any] = {}
            if algo_id:
                db_uuid = await _get_algo_db_uuid_impl(algo_id)
                if db_uuid:
                    where_clause["algoTradeId"] = db_uuid
            if event_type:
                where_clause["eventType"] = event_type.upper()

            records = await db_worker.db.auditevent.find_many(
                where=where_clause,
                take=limit,
                order={"createdAt": "desc"},
                include={"algoTrade": True},
            )

            out = []
            for r in records:
                out.append({
                    "id": r.id,
                    "algo_id": r.algoTrade.algoId if r.algoTrade else "",
                    "algo_name": r.algoTrade.algoName if r.algoTrade else "",
                    "symbol": r.symbol,
                    "event_type": r.eventType,
                    "indicator_snapshot": r.indicatorSnapshot if isinstance(r.indicatorSnapshot, dict) else {},
                    "level_snapshot": r.levelSnapshot if isinstance(r.levelSnapshot, dict) else {},
                    "decision_reason": r.decisionReason,
                    "latency_ms": r.latencyMs,
                    "created_at": r.createdAt.isoformat() if r.createdAt else datetime.now(timezone.utc).isoformat(),
                })
            return out
        except Exception as e:
            logger.debug(f"Error querying audit events from DB: {e}")
            return []

    return await db_worker.run_async(_impl())


# =============================================================================
# 4. SYNCHRONOUS THREAD-SAFE DISPATCHERS (NON-BLOCKING)
# =============================================================================

def _run_coroutine_in_worker(coro):
    """Submits coroutine directly into the permanent db_worker loop."""
    db_worker.submit(coro)


def dispatch_save_signal(signal_record: Dict[str, Any]):
    """Non-blocking background dispatch to persist signal into PostgreSQL."""
    db_worker.submit(_save_signal_to_db_impl(signal_record))


def dispatch_save_pnl(pnl_record: Dict[str, Any]):
    """Non-blocking background dispatch to persist PnL trade into PostgreSQL."""
    db_worker.submit(_save_pnl_trade_to_db_impl(pnl_record))


def dispatch_save_audit(event: Dict[str, Any]):
    """Non-blocking background dispatch to persist AuditEvent into PostgreSQL."""
    db_worker.submit(_save_audit_event_to_db_impl(event))


def dispatch_save_log(level: str, source: str, message: str, metadata: Optional[Dict[str, Any]] = None):
    """Non-blocking background dispatch to persist StructuredLog into PostgreSQL."""
    db_worker.submit(_save_structured_log_to_db_impl(level, source, message, metadata))
