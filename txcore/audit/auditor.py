"""
txcore.audit.auditor
~~~~~~~~~~~~~~~~~~~~
Cycle auditing and telemetry tracker.
Maintains statistics on scan cycles, latency, evaluated symbols, and signal conversion rates.
"""

import time
from typing import Dict, Any, List


class TradeAuditor:
    """
    Records runtime telemetry, cycle metrics, and signal approval history.
    """

    def __init__(self):
        self.cycle_count = 0
        self.total_scans = 0
        self.signals_generated = 0
        self.signals_blocked_by_news = 0
        self.history: List[Dict[str, Any]] = []

    def record_signal(self, symbol: str, direction: str, pattern: str, status: str, reason: str = ""):
        self.total_scans += 1
        if status == "APPROVED":
            self.signals_generated += 1
        elif status == "BLOCKED":
            self.signals_blocked_by_news += 1

        self.history.append({
            "timestamp": time.time(),
            "symbol": symbol,
            "direction": direction,
            "pattern": pattern,
            "status": status,
            "reason": reason,
        })
        # Keep history capped at 1000 events
        if len(self.history) > 1000:
            self.history = self.history[-1000:]

    def get_summary(self) -> Dict[str, Any]:
        return {
            "cycle_count": self.cycle_count,
            "total_scans": self.total_scans,
            "signals_generated": self.signals_generated,
            "signals_blocked_by_news": self.signals_blocked_by_news,
        }
