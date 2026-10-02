"""
AuraTrade Event Triggers REST Router (txcore.events.router)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Provides REST API endpoints for Event Trigger CRUD, status management,
execution history logs, and instant live rule simulation.
"""

import time
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status

from txcore.database import db
from txcore.auth.dependencies import require_permission, get_current_user
from prisma.models import User
from prisma.enums import TriggerType, TriggerStatus, ChannelType
from prisma import Json

from txcore.events.models import (
    CreateEventTriggerRequest,
    UpdateEventTriggerRequest,
    EventTriggerResponse,
    TriggerExecutionLogResponse,
    TestTriggerRequest,
    TestTriggerResponse,
)
from txcore.events.evaluators import SignalEvaluatorEngine, EvaluationResult
from txcore.events.dispatcher import dispatcher_service, AlertPayload
from txcore.marketview.providers.registry import provider_registry

logger = logging.getLogger("auratrade.events.router")

events_router = APIRouter(prefix="/api/v1/events", tags=["Event Triggers"])


def serialize_trigger(t) -> Dict[str, Any]:
    """Helper to serialize a Prisma EventTrigger model into a clean dict."""
    channels_val = t.channels
    if isinstance(channels_val, str):
        import json
        try:
            channels_val = json.loads(channels_val)
        except Exception:
            channels_val = [channels_val]
    elif not isinstance(channels_val, list):
        channels_val = list(channels_val) if channels_val else ["TELEGRAM"]

    return {
        "id": t.id,
        "name": t.name,
        "symbol": t.symbol,
        "market": t.market,
        "timeframe": t.timeframe,
        "trigger_type": t.triggerType,
        "threshold_config": t.thresholdConfig if isinstance(t.thresholdConfig, dict) else (t.thresholdConfig or {}),
        "channels": channels_val,
        "channel_targets": t.channelTargets if isinstance(t.channelTargets, dict) else (t.channelTargets or {}),
        "status": t.status,
        "last_triggered_at": t.lastTriggeredAt.isoformat() if t.lastTriggeredAt else None,
        "trigger_count": t.triggerCount,
        "is_deleted": t.isDeleted,
        "created_at": t.createdAt.isoformat(),
        "updated_at": t.updatedAt.isoformat(),
        "created_by": t.createdBy,
        "updated_by": t.updatedBy,
    }


def serialize_log(log_item) -> Dict[str, Any]:
    """Helper to serialize a Prisma TriggerExecutionLog model."""
    return {
        "id": log_item.id,
        "trigger_id": log_item.triggerId,
        "symbol": log_item.symbol,
        "market": log_item.market,
        "timeframe": log_item.timeframe,
        "trigger_type": log_item.triggerType,
        "trigger_price": log_item.triggerPrice,
        "conditions_met": log_item.conditionsMet if isinstance(log_item.conditionsMet, dict) else {},
        "candle_timestamp": log_item.candleTimestamp.isoformat(),
        "channels_notified": log_item.channelsNotified if isinstance(log_item.channelsNotified, list) else [],
        "dispatch_success": log_item.dispatchSuccess,
        "latency_ms": log_item.latencyMs,
        "error_message": log_item.errorMessage,
        "created_at": log_item.createdAt.isoformat(),
    }


# =========================================================================
# 1. List Event Triggers with Reactive Filters
# =========================================================================
@events_router.get("", response_model=List[Dict[str, Any]])
async def list_event_triggers(
    market: Optional[str] = Query(None, description="Filter by market (e.g. INDIAN_EQUITY, CRYPTO)"),
    symbol: Optional[str] = Query(None, description="Filter by asset symbol (e.g. RELIANCE, BTCUSDT)"),
    status: Optional[str] = Query(None, description="Filter by status (ACTIVE, PAUSED, DISABLED)"),
    trigger_type: Optional[str] = Query(None, description="Filter by trigger type"),
    search: Optional[str] = Query(None, description="Search by name or symbol"),
    include_deleted: bool = Query(False, description="Include soft-deleted triggers"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_permission("EVENT_TRIGGERS", "view")),
):
    """
    Lists standalone Event Triggers with reactive filtering and pagination.
    Soft-deleted triggers are excluded by default.
    """
    where_clause: Dict[str, Any] = {}

    if not include_deleted:
        where_clause["isDeleted"] = False

    if market and market.upper() != "ALL":
        where_clause["market"] = market.strip().upper()

    if symbol and symbol.upper() != "ALL":
        where_clause["symbol"] = symbol.strip().upper()

    if status and status.upper() != "ALL":
        where_clause["status"] = status.strip().upper()

    if trigger_type and trigger_type.upper() != "ALL":
        where_clause["triggerType"] = trigger_type.strip().upper()

    if search and search.strip():
        s = search.strip()
        where_clause["OR"] = [
            {"name": {"contains": s, "mode": "insensitive"}},
            {"symbol": {"contains": s, "mode": "insensitive"}},
        ]

    triggers = await db.eventtrigger.find_many(
        where=where_clause,
        take=limit,
        skip=offset,
        order={"createdAt": "desc"},
    )

    return [serialize_trigger(t) for t in triggers]


# =========================================================================
# 2. Create Standalone Event Trigger
# =========================================================================
@events_router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_event_trigger(
    req: CreateEventTriggerRequest,
    current_user: User = Depends(require_permission("EVENT_TRIGGERS", "edit")),
):
    """
    Creates and activates a new standalone event watcher on a specific symbol.
    """
    clean_symbol = req.symbol.strip().upper()
    clean_market = req.market.strip().upper()
    clean_tf = req.timeframe.strip().lower()

    # Normalize channels
    channels_list = [c.value if hasattr(c, "value") else str(c).upper() for c in req.channels]
    config_data = req.threshold_config or req.conditions or {}

    trigger = await db.eventtrigger.create(
        data={
            "name": req.name.strip(),
            "symbol": clean_symbol,
            "market": clean_market,
            "timeframe": clean_tf,
            "triggerType": req.trigger_type.value if hasattr(req.trigger_type, "value") else str(req.trigger_type),
            "thresholdConfig": Json(config_data),
            "channels": Json(channels_list),
            "channelTargets": Json(req.channel_targets or {}),
            "status": req.status.value if hasattr(req.status, "value") else str(req.status),
            "createdBy": current_user.email,
            "updatedBy": current_user.email,
        }
    )

    return serialize_trigger(trigger)


# =========================================================================
# 3. Get Single Trigger by ID with Telemetry Snapshot
# =========================================================================
@events_router.get("/{trigger_id}", response_model=Dict[str, Any])
async def get_event_trigger(
    trigger_id: str,
    current_user: User = Depends(require_permission("EVENT_TRIGGERS", "view")),
):
    """
    Retrieves full details for a specific trigger along with its recent execution history.
    """
    trigger = await db.eventtrigger.find_unique(
        where={"id": trigger_id},
    )

    if not trigger or trigger.isDeleted:
        raise HTTPException(status_code=404, detail="Event trigger not found.")

    recent_logs = await db.triggerexecutionlog.find_many(
        where={"triggerId": trigger_id},
        take=20,
        order={"createdAt": "desc"},
    )

    res = serialize_trigger(trigger)
    res["recent_logs"] = [serialize_log(l) for l in recent_logs]
    return res



# =========================================================================
# 4. Update Event Trigger
# =========================================================================
@events_router.put("/{trigger_id}", response_model=Dict[str, Any])
async def update_event_trigger(
    trigger_id: str,
    req: UpdateEventTriggerRequest,
    current_user: User = Depends(require_permission("EVENT_TRIGGERS", "edit")),
):
    """
    Updates an existing event trigger's threshold parameters, channels, or status.
    """
    existing = await db.eventtrigger.find_unique(where={"id": trigger_id})
    if not existing or existing.isDeleted:
        raise HTTPException(status_code=404, detail="Event trigger not found.")

    update_data: Dict[str, Any] = {"updatedBy": current_user.email}

    if req.name is not None:
        update_data["name"] = req.name.strip()
    if req.symbol is not None:
        update_data["symbol"] = req.symbol.strip().upper()
    if req.market is not None:
        update_data["market"] = req.market.strip().upper()
    if req.timeframe is not None:
        update_data["timeframe"] = req.timeframe.strip().lower()
    if req.trigger_type is not None:
        update_data["triggerType"] = req.trigger_type.value if hasattr(req.trigger_type, "value") else str(req.trigger_type)
    if req.threshold_config is not None or req.conditions is not None:
        update_data["thresholdConfig"] = Json(req.threshold_config or req.conditions or {})
    if req.channels is not None:
        channels_list = [c.value if hasattr(c, "value") else str(c).upper() for c in req.channels]
        update_data["channels"] = Json(channels_list)
    if req.channel_targets is not None:
        update_data["channelTargets"] = Json(req.channel_targets)
    if req.status is not None:
        update_data["status"] = req.status.value if hasattr(req.status, "value") else str(req.status)

    updated = await db.eventtrigger.update(
        where={"id": trigger_id},
        data=update_data,
    )

    return serialize_trigger(updated)


# =========================================================================
# 5. Toggle Trigger Status (Active / Paused)
# =========================================================================
@events_router.patch("/{trigger_id}/status", response_model=Dict[str, Any])
async def toggle_trigger_status(
    trigger_id: str,
    body: Optional[Dict[str, Any]] = None,
    target_status: Optional[str] = Query(None, description="ACTIVE or PAUSED"),
    current_user: User = Depends(require_permission("EVENT_TRIGGERS", "edit")),
):
    """
    Quick toggle for activating or pausing an event watcher without editing full configuration.
    """
    raw_status = target_status or (body.get("status") if body else None)
    if not raw_status:
        raise HTTPException(status_code=400, detail="Missing status parameter.")

    clean_st = str(raw_status).strip().upper()
    if clean_st not in ["ACTIVE", "PAUSED", "DISABLED"]:
        raise HTTPException(status_code=400, detail="Invalid status. Must be ACTIVE or PAUSED.")

    existing = await db.eventtrigger.find_unique(where={"id": trigger_id})
    if not existing or existing.isDeleted:
        raise HTTPException(status_code=404, detail="Event trigger not found.")

    updated = await db.eventtrigger.update(
        where={"id": trigger_id},
        data={
            "status": clean_st,
            "updatedBy": current_user.email,
        },
    )
    return serialize_trigger(updated)



# =========================================================================
# 6. Soft-Delete Trigger
# =========================================================================
@events_router.delete("/{trigger_id}", response_model=Dict[str, Any])
async def delete_event_trigger(
    trigger_id: str,
    current_user: User = Depends(require_permission("EVENT_TRIGGERS", "delete")),
):
    """
    Applies institutional zero-data-loss soft-delete to an event trigger.
    Preserves all execution logs and audit history.
    """
    existing = await db.eventtrigger.find_unique(where={"id": trigger_id})
    if not existing or existing.isDeleted:
        raise HTTPException(status_code=404, detail="Event trigger not found.")

    soft_deleted = await db.eventtrigger.update(
        where={"id": trigger_id},
        data={
            "isDeleted": True,
            "deletedAt": datetime.now(timezone.utc),
            "status": TriggerStatus.DISABLED,
            "updatedBy": current_user.email,
        },
    )

    return {
        "success": True,
        "message": f"Event trigger '{existing.name}' has been soft-deleted.",
        "id": trigger_id,
        "is_deleted": True,
    }


# =========================================================================
# 7. Live Simulation & Instant Trigger Test Runner
# =========================================================================
@events_router.post("/simulate", response_model=TestTriggerResponse)
async def simulate_trigger_evaluation(
    req: TestTriggerRequest,
    current_user: User = Depends(require_permission("EVENT_TRIGGERS", "view")),
):
    """
    Instantly tests a rule configuration against live/cached candles from the provider.
    Returns whether the condition was met, the evaluated math/values, and execution latency.
    """
    start_bench = time.perf_counter()

    # 1. Resolve configuration from trigger_id or direct parameters
    target_symbol = (req.symbol or "RELIANCE").strip().upper()
    target_market = (req.market or "INDIAN_EQUITY").strip().upper()
    target_tf = (req.timeframe or "5m").strip().lower()
    target_type = req.trigger_type or TriggerType.PRICE_SPIKE
    target_config = req.threshold_config or {}

    if req.trigger_id:
        existing = await db.eventtrigger.find_unique(where={"id": req.trigger_id})
        if existing:
            target_symbol = existing.symbol
            target_market = existing.market
            target_tf = existing.timeframe
            target_type = existing.triggerType
            target_config = existing.thresholdConfig if isinstance(existing.thresholdConfig, dict) else {}

    # 2. Fetch recent candles from MarketView provider registry
    candles = await provider_registry.fetch_candles_with_fallback(
        symbol=target_symbol,
        market=target_market,
        timeframe=target_tf,
        lookback=60,
    )

    if not candles:
        raise HTTPException(status_code=502, detail=f"No market data available for symbol '{target_symbol}' on {target_market}.")

    # 3. Evaluate rule condition
    eval_result: EvaluationResult = SignalEvaluatorEngine.evaluate(
        trigger_type=target_type,
        threshold_config=target_config,
        candles=candles,
    )

    elapsed_ms = round((time.perf_counter() - start_bench) * 1000.0, 2)
    last_candle = candles[-1]

    return TestTriggerResponse(
        matched=eval_result.matched,
        symbol=target_symbol,
        market=target_market,
        timeframe=target_tf,
        last_candle={
            "timestamp": last_candle.timestamp.isoformat(),
            "open": last_candle.open,
            "high": last_candle.high,
            "low": last_candle.low,
            "close": last_candle.close,
            "volume": last_candle.volume,
        },
        trigger_type=eval_result.trigger_type,
        evaluated_values=eval_result.conditions_met,
        evaluation_message=eval_result.evaluation_message,
        latency_ms=elapsed_ms,
    )


# =========================================================================
# 8. Trigger-Specific Test Endpoint
# =========================================================================
@events_router.post("/{trigger_id}/test", response_model=TestTriggerResponse)
async def test_existing_trigger(
    trigger_id: str,
    send_alert: bool = Query(False, description="If true, dispatches a test alert to configured channels"),
    current_user: User = Depends(require_permission("EVENT_TRIGGERS", "edit")),
):
    """
    Dry-runs evaluation of an existing stored trigger against live market data.
    Optionally sends a test message to verify Telegram/WhatsApp connectivity.
    """
    trigger = await db.eventtrigger.find_unique(where={"id": trigger_id})
    if not trigger or trigger.isDeleted:
        raise HTTPException(status_code=404, detail="Event trigger not found.")

    candles = await provider_registry.fetch_candles_with_fallback(
        symbol=trigger.symbol,
        market=trigger.market,
        timeframe=trigger.timeframe,
        lookback=60,
    )

    if not candles:
        raise HTTPException(status_code=502, detail=f"No market data available for '{trigger.symbol}'.")

    config_dict = trigger.thresholdConfig if isinstance(trigger.thresholdConfig, dict) else {}
    eval_result = SignalEvaluatorEngine.evaluate(
        trigger_type=trigger.triggerType,
        threshold_config=config_dict,
        candles=candles,
    )

    # Optional test dispatch
    if send_alert and eval_result.matched:
        channels_val = trigger.channels
        if isinstance(channels_val, str):
            import json
            channels_val = json.loads(channels_val)

        payload = AlertPayload(
            trigger_id=trigger.id,
            trigger_name=trigger.name,
            symbol=trigger.symbol,
            market=trigger.market,
            timeframe=trigger.timeframe,
            trigger_type=trigger.triggerType,
            trigger_price=eval_result.trigger_price,
            conditions_met=eval_result.conditions_met,
            evaluation_message=eval_result.evaluation_message,
            candle_timestamp=candles[-1].timestamp,
        )

        await dispatcher_service.dispatch_all(
            payload=payload,
            channels=channels_val or ["TELEGRAM"],
            channel_targets=trigger.channelTargets if isinstance(trigger.channelTargets, dict) else {},
            persist_audit=True,
        )

    last_candle = candles[-1]
    return TestTriggerResponse(
        matched=eval_result.matched,
        symbol=trigger.symbol,
        market=trigger.market,
        timeframe=trigger.timeframe,
        last_candle={
            "timestamp": last_candle.timestamp.isoformat(),
            "open": last_candle.open,
            "high": last_candle.high,
            "low": last_candle.low,
            "close": last_candle.close,
            "volume": last_candle.volume,
        },
        trigger_type=eval_result.trigger_type,
        evaluated_values=eval_result.conditions_met,
        evaluation_message=eval_result.evaluation_message,
        latency_ms=eval_result.latency_ms,
    )


# =========================================================================
# 9. Get Trigger Execution Logs
# =========================================================================
@events_router.get("/{trigger_id}/logs", response_model=List[Dict[str, Any]])
async def get_trigger_logs(
    trigger_id: str,
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_permission("EVENT_TRIGGERS", "view")),
):
    """
    Returns audit execution logs for a specific event trigger.
    """
    logs = await db.triggerexecutionlog.find_many(
        where={"triggerId": trigger_id},
        take=limit,
        order={"createdAt": "desc"},
    )
    return [serialize_log(l) for l in logs]
