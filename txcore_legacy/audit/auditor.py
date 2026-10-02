"""
txcore.audit.auditor
~~~~~~~~~~~~~~~~~~~~
Cycle auditing, rulebook compliance verification, and deep telemetry tracker.
Maintains institutional-grade statistics on:
  - Scan cycles and symbol batch latencies
  - Exact Indicator Snapshots (RSI, EMA 20, EMA 50, VWAP, VIX, PCR)
  - Dynamic Support/Resistance and ATR Level Snapshots
  - Filter Blocks (Multi-Timeframe Confirmation, Volatility, News, S/R Alignment)
  - Asynchronous non-blocking persistence to Prisma ORM (AuditEvent model)
  - Real-time Server-Sent Events (SSE) telemetry broadcasts
"""

import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import logging

from txcore.stream import telemetry_broadcaster
from txcore.persistence import dispatch_save_audit

logger = logging.getLogger("txcore.audit.auditor")


class TradeAuditor:
    """
    Records deep runtime telemetry, cycle metrics, and institutional audit footprints.
    Backed by non-blocking Prisma ORM persistence and live streaming.
    """

    def __init__(self, algo_id: str = ""):
        self.algo_id = algo_id
        self.cycle_count = 0
        self.total_scans = 0
        self.signals_generated = 0
        self.signals_blocked_by_news = 0
        self.signals_blocked_by_mtf = 0
        self.signals_blocked_by_risk = 0
        self.total_latency_ms = 0.0
        self.history: List[Dict[str, Any]] = []

    def record_signal(
        self,
        symbol: str,
        direction: str,
        pattern: str,
        status: str,
        reason: str = "",
        algo_id: Optional[str] = None,
        indicator_snapshot: Optional[Dict[str, Any]] = None,
        level_snapshot: Optional[Dict[str, Any]] = None,
        latency_ms: int = 0,
        chart_path: Optional[str] = None,
        audit_chart_path: Optional[str] = None,
    ):
        """
        Records an evaluated symbol into the audit trail with indicator & level footprints.
        """
        self.total_scans += 1
        status_upper = status.upper()

        if status_upper in ("APPROVED", "CONFIRMED_SIGNAL"):
            self.signals_generated += 1
        elif status_upper == "BLOCKED":
            reason_lower = reason.lower()
            if "mtf" in reason_lower:
                self.signals_blocked_by_mtf += 1
            elif "news" in reason_lower:
                self.signals_blocked_by_news += 1
            else:
                self.signals_blocked_by_risk += 1

        self.total_latency_ms += latency_ms

        event_algo_id = algo_id or self.algo_id
        now_dt = datetime.now(timezone.utc)
        
        event_record = {
            "timestamp": time.time(),
            "created_at": now_dt.isoformat(),
            "algo_id": event_algo_id,
            "symbol": symbol,
            "direction": direction,
            "pattern": pattern,
            "status": status_upper,
            "reason": reason,
            "decision_reason": reason or f"Pattern: {pattern} | Status: {status_upper}",
            "event_type": "SIGNAL_APPROVED" if status_upper in ("APPROVED", "CONFIRMED_SIGNAL") else "FILTER_BLOCK",
            "indicator_snapshot": indicator_snapshot or {},
            "level_snapshot": level_snapshot or {},
            "latency_ms": int(latency_ms),
            "chart_path": chart_path,
            "audit_chart_path": audit_chart_path,
        }

        self.history.append(event_record)
        if len(self.history) > 2000:
            self.history = self.history[-1500:]

        # Non-blocking async persistence to PostgreSQL
        try:
            dispatch_save_audit(event_record)
        except Exception as e:
            logger.debug(f"Audit persistence dispatch error: {e}")

        # Real-time SSE telemetry broadcast to UI
        try:
            telemetry_broadcaster.broadcast_sync("audit_event", event_record)
        except Exception as e:
            logger.debug(f"Audit telemetry broadcast error: {e}")

    def record_filter_block(
        self,
        symbol: str,
        filter_name: str,
        reason: str,
        direction: str = "NEUTRAL",
        pattern: str = "N/A",
        indicator_snapshot: Optional[Dict[str, Any]] = None,
        level_snapshot: Optional[Dict[str, Any]] = None,
        latency_ms: int = 0,
    ):
        """Shortcut to record an explicit filter rejection."""
        self.record_signal(
            symbol=symbol,
            direction=direction,
            pattern=pattern,
            status="BLOCKED",
            reason=f"[{filter_name}] {reason}",
            indicator_snapshot=indicator_snapshot,
            level_snapshot=level_snapshot,
            latency_ms=latency_ms,
        )

    def get_events(
        self,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Queries in-memory audit trail with optional filtering."""
        filtered = self.history
        if status:
            filtered = [e for e in filtered if e.get("status", "").upper() == status.upper()]
        return list(reversed(filtered[-limit:]))

    def get_summary(self) -> Dict[str, Any]:
        """Provides consolidated audit metrics and filter rejection ratios."""
        approval_rate = (
            (self.signals_generated / self.total_scans * 100.0)
            if self.total_scans > 0
            else 0.0
        )
        avg_latency = (
            (self.total_latency_ms / self.total_scans)
            if self.total_scans > 0
            else 0.0
        )
        return {
            "algo_id": self.algo_id,
            "cycle_count": self.cycle_count,
            "total_scans": self.total_scans,
            "signals_generated": self.signals_generated,
            "signals_blocked_by_news": self.signals_blocked_by_news,
            "signals_blocked_by_mtf": self.signals_blocked_by_mtf,
            "signals_blocked_by_risk": self.signals_blocked_by_risk,
            "approval_rate_pct": round(approval_rate, 1),
            "avg_latency_ms": round(avg_latency, 2),
            "total_audit_events": len(self.history),
        }
