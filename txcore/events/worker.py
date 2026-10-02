"""
AuraTrade Background Event Evaluation Worker (txcore.events.worker)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Executes background polling and rule evaluation across all active standalone
event watchers. Batches data fetching by (symbol, market, timeframe), enforces
candle-level deduplication locks, dispatches alerts via dispatcher_service,
and updates institutional telemetry.
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from prisma import Json

from txcore.database import db
from txcore.marketview.providers.registry import provider_registry
from txcore.events.evaluators import SignalEvaluatorEngine, EvaluationResult
from txcore.events.dispatcher import dispatcher_service, AlertPayload
from txcore.events.models import TriggerStatus

logger = logging.getLogger("auratrade.events.worker")


class EventEvaluationWorker:
    """
    Background worker orchestrating continuous signal evaluation and alert dispatching.
    """

    def __init__(self, poll_interval: float = 5.0):
        self.poll_interval = poll_interval
        self._is_running = False
        self._worker_task: Optional[asyncio.Task] = None
        self._cycle_count = 0
        self._total_evaluated = 0
        self._total_dispatched = 0

    @property
    def is_running(self) -> bool:
        return self._is_running

    def get_stats(self) -> Dict[str, Any]:
        return {
            "is_running": self._is_running,
            "poll_interval": self.poll_interval,
            "cycles_completed": self._cycle_count,
            "total_evaluated": self._total_evaluated,
            "total_dispatched": self._total_dispatched,
        }

    async def start(self):
        """Starts the background worker loop if not already running."""
        if self._is_running:
            logger.warning("[!] EventEvaluationWorker is already running.")
            return

        self._is_running = True
        self._worker_task = asyncio.create_task(self._run_loop())
        logger.info(f"[*] EventEvaluationWorker started with interval {self.poll_interval}s.")

    async def stop(self):
        """Stops the background worker loop gracefully."""
        if not self._is_running:
            return

        self._is_running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
        logger.info("[*] EventEvaluationWorker stopped.")

    async def _run_loop(self):
        """Continuous execution loop."""
        while self._is_running:
            try:
                await self.evaluate_cycle()
            except Exception as e:
                logger.error(f"[!] Error in EventEvaluationWorker cycle: {e}", exc_info=True)
            await asyncio.sleep(self.poll_interval)

    async def evaluate_cycle(self) -> Dict[str, Any]:
        """
        Executes a single end-to-end evaluation cycle across all active triggers.
        Returns summary statistics for the cycle.
        """
        cycle_start = time.perf_counter()
        self._cycle_count += 1

        # 1. Query all active, non-deleted triggers
        active_triggers = await db.eventtrigger.find_many(
            where={
                "status": TriggerStatus.ACTIVE.value,
                "isDeleted": False,
            }
        )

        if not active_triggers:
            return {
                "cycle": self._cycle_count,
                "active_triggers": 0,
                "evaluated": 0,
                "dispatched": 0,
                "latency_ms": round((time.perf_counter() - cycle_start) * 1000.0, 2),
            }

        # 2. Group triggers by (symbol, market, timeframe) to batch data fetches
        grouped_triggers: Dict[tuple, List[Any]] = {}
        for trigger in active_triggers:
            key = (trigger.symbol.strip().upper(), trigger.market.strip().upper(), trigger.timeframe.strip().lower())
            grouped_triggers.setdefault(key, []).append(trigger)

        cycle_evaluated = 0
        cycle_dispatched = 0

        # 3. Process each instrument group
        for (symbol, market, timeframe), triggers in grouped_triggers.items():
            try:
                # Fetch recent candles once for the entire group
                candles = await provider_registry.fetch_candles_with_fallback(
                    symbol=symbol,
                    market=market,
                    timeframe=timeframe,
                    lookback=60,
                )

                if not candles:
                    logger.debug(f"[-] No market data returned for group {symbol}:{market}:{timeframe}")
                    continue

                last_candle = candles[-1]

                for trigger in triggers:
                    cycle_evaluated += 1
                    self._total_evaluated += 1

                    try:
                        # Parse trigger configuration
                        config_dict = trigger.thresholdConfig if isinstance(trigger.thresholdConfig, dict) else {}

                        # Evaluate rule
                        eval_result: EvaluationResult = SignalEvaluatorEngine.evaluate(
                            trigger_type=trigger.triggerType,
                            threshold_config=config_dict,
                            candles=candles,
                        )

                        if not eval_result.matched:
                            continue

                        # Deduplication check: Has this trigger already fired for this specific candle timestamp?
                        candle_ts = last_candle.timestamp
                        if trigger.lastTriggeredAt:
                            # Compare normalized UTC timestamps
                            last_trig_ts = trigger.lastTriggeredAt
                            if hasattr(last_trig_ts, "tzinfo") and last_trig_ts.tzinfo is None:
                                last_trig_ts = last_trig_ts.replace(tzinfo=timezone.utc)
                            if hasattr(candle_ts, "tzinfo") and candle_ts.tzinfo is None:
                                candle_ts = candle_ts.replace(tzinfo=timezone.utc)

                            # If last trigger was on or after current candle timestamp, skip
                            if last_trig_ts >= candle_ts:
                                logger.debug(f"[dedup] Skipping duplicate trigger {trigger.id} on {symbol} for timestamp {candle_ts}")
                                continue

                        # Parse channels
                        channels_val = trigger.channels
                        if isinstance(channels_val, str):
                            import json
                            try:
                                channels_val = json.loads(channels_val)
                            except Exception:
                                channels_val = [channels_val]
                        elif not isinstance(channels_val, list):
                            channels_val = list(channels_val) if channels_val else ["TELEGRAM"]

                        # Build Alert Payload
                        payload = AlertPayload(
                            trigger_id=trigger.id,
                            trigger_name=trigger.name,
                            symbol=symbol,
                            market=market,
                            timeframe=timeframe,
                            trigger_type=trigger.triggerType,
                            trigger_price=eval_result.trigger_price,
                            conditions_met=eval_result.conditions_met,
                            evaluation_message=eval_result.evaluation_message,
                            candle_timestamp=candle_ts,
                        )

                        targets = trigger.channelTargets if isinstance(trigger.channelTargets, dict) else {}

                        # Dispatch alert and persist audit log
                        dispatch_results = await dispatcher_service.dispatch_all(
                            payload=payload,
                            channels=channels_val,
                            channel_targets=targets,
                            persist_audit=True,
                        )

                        cycle_dispatched += 1
                        self._total_dispatched += 1

                        logger.info(
                            f"[ALERT FIRED] Trigger '{trigger.name}' ({symbol} - {trigger.triggerType}) "
                            f"@ {eval_result.trigger_price:.4f} -> Dispatched to {len(dispatch_results)} channels."
                        )

                    except Exception as trig_err:
                        logger.error(f"[!] Error evaluating trigger {trigger.id} ({trigger.name}): {trig_err}")

            except Exception as group_err:
                logger.error(f"[!] Error processing symbol group {symbol}:{market}:{timeframe}: {group_err}")

        cycle_latency = round((time.perf_counter() - cycle_start) * 1000.0, 2)
        return {
            "cycle": self._cycle_count,
            "active_triggers": len(active_triggers),
            "evaluated": cycle_evaluated,
            "dispatched": cycle_dispatched,
            "latency_ms": cycle_latency,
        }


# Global Worker Instance
event_worker = EventEvaluationWorker(poll_interval=5.0)
