"""
txcore.execution.paper_engine
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
High-Performance, Market-Agnostic Paper Trading & Simulated Order Execution Engine.

Simulates institutional execution of trading signals discovered by AlgoTrades:
  - Virtual portfolio capital management (Cash, Margin, Equity)
  - Realistic institutional slippage and transaction cost modeling
  - Dynamic position sizing (risk-capital percentage or fixed allocation)
  - Position lifecycle tracking: OPEN -> ACTIVE MTM -> TARGET_HIT / SL_HIT / SQUARE_OFF
  - Dynamic Trailing Stop Loss ratcheting
  - Thread-safe state synchronization
  - Non-blocking async Prisma ORM persistence via persistence.dispatch_save_pnl
  - Real-time Server-Sent Events (SSE) telemetry broadcasts
"""

import logging
import threading
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from txcore.models.types import Direction, Signal
from txcore.stream import telemetry_broadcaster

logger = logging.getLogger(__name__)


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL_MARKET = "SL_MARKET"
    TARGET = "TARGET"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class PositionStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    SQUARED_OFF = "SQUARED_OFF"


@dataclass
class PaperOrder:
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: int
    price: float
    status: OrderStatus
    created_at: str
    algo_id: str = ""
    signal_id: Optional[str] = None
    filled_at: Optional[str] = None
    filled_price: Optional[float] = None
    slippage_points: float = 0.0
    commission: float = 0.0


@dataclass
class PaperPosition:
    position_id: str
    algo_id: str
    algo_name: str
    symbol: str
    direction: str                     # "CALL" or "PUT"
    side: str                          # "BUY" or "SELL"
    quantity: int
    entry_price: float
    current_price: float
    stop_loss: float
    target: float
    status: str                        # PositionStatus value
    entry_time: str
    trailing_sl: Optional[float] = None
    trailing_step: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    realized_pnl: float = 0.0
    realized_pnl_pct: float = 0.0
    exit_price: Optional[float] = None
    exit_time: Optional[str] = None
    exit_reason: Optional[str] = None  # "TARGET_HIT", "SL_HIT", "MANUAL_SQUARE_OFF"
    holding_bars: int = 0
    total_charges: float = 0.0
    signal_id: Optional[str] = None


class PaperTradingEngine:
    """
    Thread-safe, institutional paper trading and position manager.
    Tracks portfolio equity, open positions with live MTM, and records closed trades.
    """

    def __init__(self, initial_capital: float = 1_000_000.0, currency: str = "INR"):
        self.lock = threading.RLock()
        self.initial_capital = float(initial_capital)
        self.cash_balance = float(initial_capital)
        self.currency = currency
        
        self.open_positions: Dict[str, PaperPosition] = {}
        self.orders: List[PaperOrder] = []
        self.closed_trades: List[Dict[str, Any]] = []
        
        self.win_trades = 0
        self.loss_trades = 0
        self.total_realized_pnl = 0.0
        self.total_charges = 0.0

    # -------------------------------------------------------------------------
    # PORTFOLIO SUMMARY & METRICS
    # -------------------------------------------------------------------------

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Calculates consolidated real-time equity, margins, and performance."""
        with self.lock:
            unrealized_total = sum(p.unrealized_pnl for p in self.open_positions.values())
            used_margin = sum(p.entry_price * p.quantity for p in self.open_positions.values())
            equity = self.cash_balance + used_margin + unrealized_total
            total_closed = self.win_trades + self.loss_trades
            win_rate = (self.win_trades / total_closed * 100.0) if total_closed > 0 else 0.0
            
            pnl_pct = ((equity - self.initial_capital) / self.initial_capital * 100.0) if self.initial_capital > 0 else 0.0

            return {
                "initial_capital": round(self.initial_capital, 2),
                "cash_balance": round(self.cash_balance, 2),
                "used_margin": round(used_margin, 2),
                "total_equity": round(equity, 2),
                "unrealized_pnl": round(unrealized_total, 2),
                "realized_pnl": round(self.total_realized_pnl, 2),
                "total_charges": round(self.total_charges, 2),
                "pnl_pct": round(pnl_pct, 2),
                "currency": self.currency,
                "open_positions_count": len(self.open_positions),
                "closed_trades_count": total_closed,
                "win_trades": self.win_trades,
                "loss_trades": self.loss_trades,
                "win_rate_pct": round(win_rate, 1),
            }

    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Returns all currently open positions with live mark-to-market calculations."""
        with self.lock:
            return [asdict(p) for p in self.open_positions.values()]

    def get_closed_trades(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Returns historical closed trade executions."""
        with self.lock:
            return list(reversed(self.closed_trades[-limit:]))

    # -------------------------------------------------------------------------
    # POSITION OPENING & EXECUTION
    # -------------------------------------------------------------------------

    def open_position_from_signal(
        self,
        signal: Signal,
        algo_id: str,
        algo_name: str,
        risk_capital_pct: float = 0.02,
        slippage_pct: float = 0.0005,
    ) -> Optional[PaperPosition]:
        """
        Executes a simulated paper order upon receiving an approved Signal.
        Applies realistic slippage, calculates position sizing, and registers an open position.
        """
        with self.lock:
            symbol = getattr(signal, "symbol", None) or getattr(signal, "pair", "UNKNOWN")
            # Check if an open position already exists for this symbol from this algo
            for p in self.open_positions.values():
                if p.symbol == symbol and p.algo_id == algo_id:
                    logger.debug(f"Position already active for {symbol} under {algo_id}, skipping duplicate.")
                    return None

            base_price = float(signal.price)
            if base_price <= 0:
                return None

            # Slippage calculation
            is_call = signal.direction == Direction.CALL
            slippage = base_price * slippage_pct
            entry_price = round(base_price + slippage if is_call else base_price - slippage, 2)

            # Position sizing: 2% of total capital or minimum 1 lot/share
            capital_allocation = self.cash_balance * risk_capital_pct
            if capital_allocation <= 0:
                capital_allocation = self.cash_balance * 0.01

            raw_qty = int(capital_allocation / entry_price) if entry_price > 0 else 1
            quantity = max(1, min(raw_qty, 500))

            required_margin = entry_price * quantity
            if required_margin > self.cash_balance:
                # Adjust quantity to fit available cash
                quantity = max(1, int(self.cash_balance / entry_price))
                required_margin = entry_price * quantity

            if self.cash_balance < required_margin:
                logger.warning(f"Insufficient cash for paper order {symbol}: Need {required_margin}, have {self.cash_balance}")
                return None

            # Deduct used margin
            self.cash_balance -= required_margin

            # Estimated transaction fee: 0.03% (turnover charges, exchange, GST)
            turnover = required_margin
            fee = round(turnover * 0.0003, 2)
            self.total_charges += fee
            self.cash_balance -= fee

            # Generate unique IDs
            now_iso = datetime.now(timezone.utc).isoformat()
            short_id = uuid.uuid4().hex[:6].upper()
            pos_id = f"POS-{symbol}-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{short_id}"
            ord_id = f"ORD-{symbol}-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{short_id}"

            # Register order
            sig_id = getattr(signal, "signal_id", None) or getattr(signal, "id", "")
            order = PaperOrder(
                order_id=ord_id,
                symbol=symbol,
                side=OrderSide.BUY if is_call else OrderSide.SELL,
                order_type=OrderType.MARKET,
                quantity=quantity,
                price=base_price,
                status=OrderStatus.FILLED,
                created_at=now_iso,
                algo_id=algo_id,
                signal_id=sig_id,
                filled_at=now_iso,
                filled_price=entry_price,
                slippage_points=round(abs(entry_price - base_price), 2),
                commission=fee,
            )
            self.orders.append(order)

            # Determine stop loss & target
            sig_sl = getattr(signal, "stop_loss", None) or (signal.metadata.get("stop_loss") if hasattr(signal, "metadata") and isinstance(signal.metadata, dict) else None)
            sig_tgt = getattr(signal, "target", None) or (signal.metadata.get("target") if hasattr(signal, "metadata") and isinstance(signal.metadata, dict) else None)
            sl = float(sig_sl) if sig_sl else (entry_price * 0.98 if is_call else entry_price * 1.02)
            tgt = float(sig_tgt) if sig_tgt else (entry_price * 1.03 if is_call else entry_price * 0.97)

            position = PaperPosition(
                position_id=pos_id,
                algo_id=algo_id,
                algo_name=algo_name,
                symbol=symbol,
                direction=signal.direction.value,
                side="BUY" if is_call else "SELL",
                quantity=quantity,
                entry_price=entry_price,
                current_price=entry_price,
                stop_loss=round(sl, 2),
                target=round(tgt, 2),
                trailing_sl=round(sl, 2),
                trailing_step=round(abs(entry_price - sl) * 0.5, 2),
                status=PositionStatus.OPEN.value,
                entry_time=now_iso,
                unrealized_pnl=0.0,
                unrealized_pnl_pct=0.0,
                realized_pnl=0.0,
                total_charges=fee,
                signal_id=signal.signal_id or signal.id,
            )
            self.open_positions[pos_id] = position

            logger.info(
                f"[PaperTrading] Opened {position.side} {quantity}x {symbol} @ {entry_price} "
                f"(SL: {position.stop_loss}, TGT: {position.target}) [Pos: {pos_id}]"
            )

            # Broadcast SSE notification
            telemetry_broadcaster.broadcast_sync("paper_position_opened", {
                "position": asdict(position),
                "summary": self.get_portfolio_summary(),
            })

            return position

    # -------------------------------------------------------------------------
    # REAL-TIME PRICE TICK / CANDLE UPDATE & POSITION MONITORING
    # -------------------------------------------------------------------------

    def update_price_tick(
        self,
        symbol: str,
        ltp: float,
        high: Optional[float] = None,
        low: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Updates open positions for a symbol against live market price.
        Checks for TARGET_HIT, SL_HIT, updates unrealized PnL, and adjusts trailing stops.
        """
        with self.lock:
            closed_now: List[Dict[str, Any]] = []
            target_high = high if high is not None else ltp
            target_low = low if low is not None else ltp

            positions_to_eval = [p for p in self.open_positions.values() if p.symbol == symbol]

            for pos in positions_to_eval:
                pos.current_price = round(ltp, 2)
                pos.holding_bars += 1
                is_long = pos.side == "BUY"

                # Calculate Mark-to-Market Unrealized PnL
                if is_long:
                    pnl_pts = ltp - pos.entry_price
                    pos.unrealized_pnl = round(pnl_pts * pos.quantity, 2)
                    pos.unrealized_pnl_pct = round((pnl_pts / pos.entry_price) * 100.0, 2)

                    # Ratchet Trailing SL if price has advanced favorably
                    if pos.trailing_sl and ltp > pos.entry_price:
                        potential_new_sl = round(ltp - pos.trailing_step, 2)
                        if potential_new_sl > pos.trailing_sl:
                            pos.trailing_sl = potential_new_sl

                    # 1. Target Hit check
                    if target_high >= pos.target:
                        closed_info = self._close_position_internal(
                            pos.position_id,
                            exit_price=pos.target,
                            reason="TARGET_HIT",
                            outcome="WIN",
                        )
                        if closed_info:
                            closed_now.append(closed_info)
                        continue

                    # 2. Stop Loss Hit check
                    eff_sl = pos.trailing_sl if pos.trailing_sl else pos.stop_loss
                    if target_low <= eff_sl:
                        closed_info = self._close_position_internal(
                            pos.position_id,
                            exit_price=eff_sl,
                            reason="SL_HIT",
                            outcome="LOSS",
                        )
                        if closed_info:
                            closed_now.append(closed_info)
                        continue

                else:  # Short / PUT position
                    pnl_pts = pos.entry_price - ltp
                    pos.unrealized_pnl = round(pnl_pts * pos.quantity, 2)
                    pos.unrealized_pnl_pct = round((pnl_pts / pos.entry_price) * 100.0, 2)

                    # Ratchet Trailing SL down for Short position
                    if pos.trailing_sl and ltp < pos.entry_price:
                        potential_new_sl = round(ltp + pos.trailing_step, 2)
                        if potential_new_sl < pos.trailing_sl:
                            pos.trailing_sl = potential_new_sl

                    # 1. Target Hit check (price drops to or below target)
                    if target_low <= pos.target:
                        closed_info = self._close_position_internal(
                            pos.position_id,
                            exit_price=pos.target,
                            reason="TARGET_HIT",
                            outcome="WIN",
                        )
                        if closed_info:
                            closed_now.append(closed_info)
                        continue

                    # 2. Stop Loss Hit check (price rises to or above SL)
                    eff_sl = pos.trailing_sl if pos.trailing_sl else pos.stop_loss
                    if target_high >= eff_sl:
                        closed_info = self._close_position_internal(
                            pos.position_id,
                            exit_price=eff_sl,
                            reason="SL_HIT",
                            outcome="LOSS",
                        )
                        if closed_info:
                            closed_now.append(closed_info)
                        continue

            return closed_now

    # -------------------------------------------------------------------------
    # POSITION CLOSE & SQUARE-OFF
    # -------------------------------------------------------------------------

    def _close_position_internal(
        self,
        position_id: str,
        exit_price: float,
        reason: str = "MANUAL_SQUARE_OFF",
        outcome: str = "WIN",
    ) -> Optional[Dict[str, Any]]:
        """Internal helper executing position square-off and database sync."""
        pos = self.open_positions.pop(position_id, None)
        if not pos:
            return None

        is_long = pos.side == "BUY"
        exit_p = round(float(exit_price), 2)
        pnl_pts = round((exit_p - pos.entry_price) if is_long else (pos.entry_price - exit_p), 2)
        realized_pnl = round(pnl_pts * pos.quantity, 2)
        pnl_pct = round((pnl_pts / pos.entry_price) * 100.0, 2)

        # Exit transaction fee
        exit_turnover = exit_p * pos.quantity
        exit_fee = round(exit_turnover * 0.0003, 2)
        total_fees = round(pos.total_charges + exit_fee, 2)
        net_realized_pnl = round(realized_pnl - exit_fee, 2)

        # Release initial margin back to cash + net PnL
        returned_margin = pos.entry_price * pos.quantity
        self.cash_balance += returned_margin + net_realized_pnl
        self.total_realized_pnl += net_realized_pnl
        self.total_charges += exit_fee

        if net_realized_pnl >= 0:
            self.win_trades += 1
            final_outcome = "WIN"
        else:
            self.loss_trades += 1
            final_outcome = "LOSS"

        now_iso = datetime.now(timezone.utc).isoformat()
        pos.status = PositionStatus.CLOSED.value
        pos.exit_price = exit_p
        pos.exit_time = now_iso
        pos.exit_reason = reason
        pos.realized_pnl = net_realized_pnl
        pos.realized_pnl_pct = pnl_pct
        pos.total_charges = total_fees

        trade_record = {
            "trade_id": f"TRD-{pos.symbol}-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
            "position_id": pos.position_id,
            "signal_id": pos.signal_id or "",
            "algo_id": pos.algo_id,
            "algo_name": pos.algo_name,
            "symbol": pos.symbol,
            "direction": pos.direction,
            "side": pos.side,
            "quantity": pos.quantity,
            "entry_price": pos.entry_price,
            "exit_price": exit_p,
            "entry_time": pos.entry_time,
            "exit_time": now_iso,
            "pnl_points": pnl_pts,
            "pnl_amount": net_realized_pnl,
            "pnl_pct": pnl_pct,
            "outcome": final_outcome,
            "reason": reason,
            "holding_bars": pos.holding_bars,
            "total_charges": total_fees,
            "timestamp": now_iso,
        }
        self.closed_trades.append(trade_record)

        logger.info(
            f"[PaperTrading] Closed {pos.symbol} @ {exit_p} ({reason}). "
            f"Net PnL: {net_realized_pnl} ({pnl_pct}%) [{final_outcome}]"
        )

        # Async DB persistence into pnl_trades via persistence module
        try:
            from txcore.persistence import dispatch_save_pnl
            dispatch_save_pnl({
                "signal_id": pos.signal_id,
                "algo_id": pos.algo_id,
                "algo_name": pos.algo_name,
                "symbol": pos.symbol,
                "direction": pos.direction,
                "entry_price": pos.entry_price,
                "exit_price": exit_p,
                "outcome": final_outcome,
                "pnl_pct": pnl_pct,
                "pnl_points": pnl_pts,
                "timestamp": now_iso,
            })
        except Exception as db_err:
            logger.debug(f"Paper trade persistence error: {db_err}")

        # Broadcast SSE event
        telemetry_broadcaster.broadcast_sync("paper_position_closed", {
            "trade": trade_record,
            "summary": self.get_portfolio_summary(),
        })

        return trade_record

    def close_position_manually(self, position_id: str, exit_price: Optional[float] = None, reason: str = "MANUAL_SQUARE_OFF") -> Optional[Dict[str, Any]]:
        """Manual square-off trigger by trader from UI, API, or broker adapter."""
        with self.lock:
            pos = self.open_positions.get(position_id)
            if not pos:
                return None
            p = exit_price if exit_price is not None else pos.current_price
            return self._close_position_internal(position_id, exit_price=p, reason=reason)

    def modify_position(
        self,
        position_id: str,
        stop_loss: Optional[float] = None,
        target: Optional[float] = None,
        trailing_sl: Optional[float] = None,
    ) -> Optional[PaperPosition]:
        """Modifies order brackets (SL, Target, Trailing Stop) on an active open position."""
        with self.lock:
            pos = self.open_positions.get(position_id)
            if not pos:
                return None
            if stop_loss is not None:
                pos.stop_loss = round(float(stop_loss), 2)
            if target is not None:
                pos.target = round(float(target), 2)
            if trailing_sl is not None:
                pos.trailing_sl = round(float(trailing_sl), 2)

            telemetry_broadcaster.broadcast_sync("paper_position_modified", {
                "position": asdict(pos),
            })
            return pos

    def reset_account(self, initial_capital: Optional[float] = None):
        """Resets virtual paper trading account to pristine starting state."""
        with self.lock:
            if initial_capital is not None:
                self.initial_capital = float(initial_capital)
            self.cash_balance = self.initial_capital
            self.open_positions.clear()
            self.orders.clear()
            self.closed_trades.clear()
            self.win_trades = 0
            self.loss_trades = 0
            self.total_realized_pnl = 0.0
            self.total_charges = 0.0
            logger.info(f"[PaperTrading] Account reset with capital: {self.initial_capital} {self.currency}")


# =============================================================================
# GLOBAL SINGLETON INSTANCE
# =============================================================================

_paper_engine_instance: Optional[PaperTradingEngine] = None
_paper_lock = threading.Lock()


def get_paper_engine(initial_capital: float = 1_000_000.0, currency: str = "INR") -> PaperTradingEngine:
    """Returns the process-wide singleton PaperTradingEngine."""
    global _paper_engine_instance
    with _paper_lock:
        if _paper_engine_instance is None:
            _paper_engine_instance = PaperTradingEngine(initial_capital=initial_capital, currency=currency)
        return _paper_engine_instance
