"""
txcore.filters.risk_manager
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Institutional risk management and real-time circuit breaker engine.
Protects trading capital through multi-tier safety controls:
  - Account-level maximum daily loss limit (auto-halts new entries upon breach)
  - Portfolio maximum open exposure (concurrency limiter)
  - Consecutive loss streak limiter with automated cooling-off periods
  - Global emergency kill-switch & automatic portfolio square-off
"""

import logging
import threading
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Tuple, Optional, Dict, Any

from txcore.filters.base import BaseFilter

logger = logging.getLogger("txcore.filters.risk_manager")


class CircuitBreakerStatus(str, Enum):
    NORMAL = "NORMAL"                                # Fully operational
    WARNING = "WARNING"                              # Drawdown near threshold (>70% of max limit)
    TRIPPED_MAX_LOSS = "TRIPPED_MAX_LOSS"            # Daily loss limit exceeded -> hard halt
    TRIPPED_CONSECUTIVE_LOSS = "TRIPPED_CONSECUTIVE"  # Too many consecutive losses -> cooling off
    EMERGENCY_HALT = "EMERGENCY_HALT"                # Manual or automated panic kill-switch


class RiskManager(BaseFilter):
    """
    Thread-safe account risk guard and circuit breaker.
    Evaluates every potential trade setup before strategy execution or order routing.
    """

    _instance = None
    _lock = threading.RLock()

    def __init__(
        self,
        starting_daily_equity: float = 1_000_000.0,
        max_daily_loss_pct: float = 0.03,        # 3% maximum drawdown limit
        max_open_positions: int = 5,
        max_risk_per_trade_pct: float = 0.02,    # 2% max capital risk per order
        consecutive_loss_limit: int = 3,         # 3 losses in a row triggers cooling off
        cooldown_minutes: int = 30,
    ):
        self.lock = threading.RLock()
        self.starting_daily_equity = float(starting_daily_equity)
        self.current_equity = float(starting_daily_equity)
        
        self.max_daily_loss_pct = float(max_daily_loss_pct)
        self.max_open_positions = int(max_open_positions)
        self.max_risk_per_trade_pct = float(max_risk_per_trade_pct)
        self.consecutive_loss_limit = int(consecutive_loss_limit)
        self.cooldown_minutes = int(cooldown_minutes)

        self.status = CircuitBreakerStatus.NORMAL
        self.daily_realized_pnl = 0.0
        self.consecutive_losses = 0
        self.cooldown_until: Optional[datetime] = None
        self.halt_reason: Optional[str] = None
        self.last_reset_date = datetime.now(timezone.utc).date()

    @classmethod
    def get_instance(cls) -> "RiskManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # -------------------------------------------------------------------------
    # BASE FILTER CONTRACT
    # -------------------------------------------------------------------------

    def is_allowed(self, symbol: str, **kwargs) -> Tuple[bool, Optional[str]]:
        """
        Evaluates whether a trade setup is permitted under current risk parameters.
        Returns: (is_allowed: bool, reason_if_blocked: Optional[str])
        """
        with self.lock:
            self._check_daily_reset()

            # 1. Check Circuit Breaker Status
            if self.status == CircuitBreakerStatus.EMERGENCY_HALT:
                return False, f"Risk Alert: Global Emergency Kill Switch active ({self.halt_reason or 'Manual Halt'})"

            if self.status == CircuitBreakerStatus.TRIPPED_MAX_LOSS:
                return False, f"Risk Alert: Max daily loss limit breached ({self.max_daily_loss_pct * 100:.1f}%), trading halted"

            if self.status == CircuitBreakerStatus.TRIPPED_CONSECUTIVE_LOSS:
                if self.cooldown_until and datetime.now(timezone.utc) < self.cooldown_until:
                    rem = int((self.cooldown_until - datetime.now(timezone.utc)).total_seconds() / 60)
                    return False, f"Risk Alert: Consecutive loss limit ({self.consecutive_loss_limit}) reached, cooling off for {rem}m"
                else:
                    # Cooldown expired, resume to NORMAL
                    self.status = CircuitBreakerStatus.NORMAL
                    self.halt_reason = None
                    self.cooldown_until = None
                    logger.info("[RiskManager] Cooldown period expired, circuit breaker restored to NORMAL.")

            # 2. Check open position limits from Broker / Paper engine
            open_count = kwargs.get("active_positions_count")
            if open_count is None:
                # Query paper engine or active broker adapter
                try:
                    from txcore.execution.paper_engine import get_paper_engine
                    open_count = len(get_paper_engine().open_positions)
                except Exception:
                    open_count = 0

            if open_count >= self.max_open_positions:
                return False, f"Risk Alert: Max open positions limit ({self.max_open_positions}) reached (Active: {open_count})"

            # 3. Check Real-Time Drawdown
            if self.starting_daily_equity > 0:
                current_loss = self.starting_daily_equity - self.current_equity
                loss_pct = current_loss / self.starting_daily_equity
                if loss_pct >= self.max_daily_loss_pct:
                    self.status = CircuitBreakerStatus.TRIPPED_MAX_LOSS
                    self.halt_reason = f"Drawdown ({loss_pct * 100:.2f}%) exceeded limit ({self.max_daily_loss_pct * 100:.1f}%)"
                    self._broadcast_risk_alert("circuit_breaker_tripped", self.halt_reason)
                    return False, self.halt_reason
                elif loss_pct >= (self.max_daily_loss_pct * 0.70):
                    self.status = CircuitBreakerStatus.WARNING
                else:
                    if self.status == CircuitBreakerStatus.WARNING:
                        self.status = CircuitBreakerStatus.NORMAL

            return True, None

    # -------------------------------------------------------------------------
    # STATE MUTATION & PERFORMANCE TRACKING
    # -------------------------------------------------------------------------

    def record_trade_result(self, outcome: str, pnl_amount: float):
        """
        Updates realized PnL and tracks consecutive win/loss streaks.
        """
        with self.lock:
            self._check_daily_reset()
            self.daily_realized_pnl += pnl_amount
            self.current_equity += pnl_amount

            if outcome.upper() == "WIN":
                self.consecutive_losses = 0
            elif outcome.upper() == "LOSS":
                self.consecutive_losses += 1
                if self.consecutive_losses >= self.consecutive_loss_limit:
                    self.status = CircuitBreakerStatus.TRIPPED_CONSECUTIVE_LOSS
                    self.cooldown_until = datetime.now(timezone.utc) + timedelta(minutes=self.cooldown_minutes)
                    self.halt_reason = f"Hit {self.consecutive_losses} consecutive losses. Cooldown until {self.cooldown_until.strftime('%H:%M:%S UTC')}."
                    logger.warning(f"[RiskManager] {self.halt_reason}")
                    self._broadcast_risk_alert("circuit_breaker_tripped", self.halt_reason)

            # Re-evaluate daily drawdown
            if self.starting_daily_equity > 0:
                total_loss = self.starting_daily_equity - self.current_equity
                loss_pct = total_loss / self.starting_daily_equity
                if loss_pct >= self.max_daily_loss_pct:
                    self.status = CircuitBreakerStatus.TRIPPED_MAX_LOSS
                    self.halt_reason = f"Daily realized loss ({loss_pct * 100:.2f}%) breached limit"
                    self._broadcast_risk_alert("circuit_breaker_tripped", self.halt_reason)

    def update_current_equity(self, equity: float):
        """Updates live mark-to-market account equity."""
        with self.lock:
            self._check_daily_reset()
            self.current_equity = float(equity)
            if self.starting_daily_equity > 0:
                drawdown = max(0.0, self.starting_daily_equity - self.current_equity)
                drawdown_pct = drawdown / self.starting_daily_equity
                if drawdown_pct >= self.max_daily_loss_pct:
                    self.status = CircuitBreakerStatus.TRIPPED_MAX_LOSS
                    self.halt_reason = f"Live drawdown {drawdown_pct * 100:.2f}% breached max daily loss {self.max_daily_loss_pct * 100:.1f}%"
                    self._broadcast_risk_alert("circuit_breaker_tripped", self.halt_reason)
                elif drawdown_pct >= (self.max_daily_loss_pct * 0.70):
                    if self.status == CircuitBreakerStatus.NORMAL:
                        self.status = CircuitBreakerStatus.WARNING

    def trigger_emergency_square_off(self, reason: str = "Operator Emergency Kill Switch") -> Dict[str, Any]:
        """
        Global Emergency Panic Action:
        1. Trips Circuit Breaker to EMERGENCY_HALT.
        2. Squares off all open positions across Paper and Live brokers.
        3. Stops/pauses running AlgoTrade engines.
        4. Broadcasts SSE alert.
        """
        with self.lock:
            self.status = CircuitBreakerStatus.EMERGENCY_HALT
            self.halt_reason = reason
            logger.critical(f"[RiskManager] EMERGENCY KILL SWITCH ACTIVATED: {reason}")

            # 1. Square off paper engine
            closed_paper = []
            try:
                from txcore.execution.paper_engine import get_paper_engine
                pe = get_paper_engine()
                for pid in list(pe.open_positions.keys()):
                    trade = pe.close_position_manually(pid, reason="EMERGENCY_KILL_SWITCH")
                    if trade:
                        closed_paper.append(pid)
            except Exception as e:
                logger.error(f"Error squaring off paper engine: {e}")

            # 2. Square off active broker
            closed_broker = []
            try:
                from txcore.execution.broker_adapter import get_broker_manager
                bm = get_broker_manager()
                closed_broker = bm.get_adapter().square_off_all()
            except Exception as e:
                logger.error(f"Error squaring off broker adapter: {e}")

            # 3. Stop running algos
            stopped_algos = []
            try:
                from txcore.algotrade import AlgoTradeManager
                mgr = AlgoTradeManager.get_instance()
                for algo in mgr.algos.values():
                    if getattr(algo, "is_running", False):
                        algo.stop()
                        stopped_algos.append(algo.algo_id)
            except Exception as e:
                logger.error(f"Error stopping AlgoTrades: {e}")

            self._broadcast_risk_alert("emergency_halt_tripped", {
                "reason": reason,
                "closed_positions_count": len(closed_paper) + len(closed_broker),
                "stopped_algos": stopped_algos,
            })

            return {
                "status": "EMERGENCY_HALT_ACTIVE",
                "reason": reason,
                "closed_paper_positions": closed_paper,
                "closed_broker_positions": closed_broker,
                "stopped_algos": stopped_algos,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    def reset_circuit_breaker(self) -> Dict[str, Any]:
        """Manually restores circuit breaker status back to NORMAL."""
        with self.lock:
            self.status = CircuitBreakerStatus.NORMAL
            self.halt_reason = None
            self.consecutive_losses = 0
            self.cooldown_until = None
            logger.info("[RiskManager] Circuit breaker manually reset to NORMAL.")
            self._broadcast_risk_alert("circuit_breaker_reset", "Circuit breaker restored to NORMAL.")
            return {"status": "SUCCESS", "current_status": self.status.value}

    def get_risk_status(self) -> Dict[str, Any]:
        """Consolidates current risk telemetry, limits, and drawdown statistics."""
        with self.lock:
            self._check_daily_reset()
            drawdown = max(0.0, self.starting_daily_equity - self.current_equity)
            drawdown_pct = (drawdown / self.starting_daily_equity * 100.0) if self.starting_daily_equity > 0 else 0.0
            max_loss_amount = self.starting_daily_equity * self.max_daily_loss_pct

            # Query active positions count
            active_count = 0
            try:
                from txcore.execution.paper_engine import get_paper_engine
                active_count = len(get_paper_engine().open_positions)
            except Exception:
                pass

            return {
                "status": self.status.value,
                "halt_reason": self.halt_reason,
                "starting_daily_equity": round(self.starting_daily_equity, 2),
                "current_equity": round(self.current_equity, 2),
                "daily_realized_pnl": round(self.daily_realized_pnl, 2),
                "current_drawdown": round(drawdown, 2),
                "drawdown_pct": round(drawdown_pct, 2),
                "max_daily_loss_pct": round(self.max_daily_loss_pct * 100.0, 2),
                "max_daily_loss_amount": round(max_loss_amount, 2),
                "max_open_positions": self.max_open_positions,
                "active_positions_count": active_count,
                "consecutive_losses": self.consecutive_losses,
                "consecutive_loss_limit": self.consecutive_loss_limit,
                "cooldown_until": self.cooldown_until.isoformat() if self.cooldown_until else None,
            }

    def update_config(
        self,
        max_daily_loss_pct: Optional[float] = None,
        max_open_positions: Optional[int] = None,
        consecutive_loss_limit: Optional[int] = None,
        cooldown_minutes: Optional[int] = None,
        starting_daily_equity: Optional[float] = None,
    ):
        """Updates runtime risk parameters dynamically."""
        with self.lock:
            if max_daily_loss_pct is not None:
                self.max_daily_loss_pct = float(max_daily_loss_pct)
            if max_open_positions is not None:
                self.max_open_positions = int(max_open_positions)
            if consecutive_loss_limit is not None:
                self.consecutive_loss_limit = int(consecutive_loss_limit)
            if cooldown_minutes is not None:
                self.cooldown_minutes = int(cooldown_minutes)
            if starting_daily_equity is not None:
                self.starting_daily_equity = float(starting_daily_equity)
                self.current_equity = float(starting_daily_equity)

    def _check_daily_reset(self):
        """Resets daily counters at UTC midnight."""
        today = datetime.now(timezone.utc).date()
        if today > self.last_reset_date:
            self.last_reset_date = today
            self.daily_realized_pnl = 0.0
            self.starting_daily_equity = self.current_equity
            if self.status != CircuitBreakerStatus.EMERGENCY_HALT:
                self.status = CircuitBreakerStatus.NORMAL
                self.halt_reason = None
            logger.info(f"[RiskManager] Daily rollover executed. Baseline equity: {self.starting_daily_equity}")

    def _broadcast_risk_alert(self, event_type: str, message: Any):
        """Broadcasts real-time risk alert to connected frontends via SSE."""
        try:
            from txcore.stream import telemetry_broadcaster
            telemetry_broadcaster.broadcast_sync(event_type, {
                "event": event_type,
                "message": message,
                "risk_status": self.status.value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        except Exception:
            pass


def get_risk_manager() -> RiskManager:
    """Singleton accessor for institutional RiskManager."""
    return RiskManager.get_instance()
