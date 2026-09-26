"""
txcore.strategies.evaluator
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Historical Strategy Evaluation & Backtesting Engine.
Executes a walk-forward candle replay of any BaseStrategy over historical data
for user-selected date ranges and generates performance, P&L, and accuracy metrics.
"""

from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, field
from datetime import datetime, timezone
import pandas as pd

from txcore.models.types import Direction, Signal
from txcore.strategies.base import BaseStrategy
from txcore.strategies.pdf_price_action import PDFPriceActionStrategy
from txcore.analysis.period import filter_candles_by_date


@dataclass
class TradeRecord:
    """Represents a simulated executed trade in historical evaluation."""
    trade_id: int
    symbol: str
    direction: str
    pattern: str
    entry_time: str
    entry_price: float
    exit_time: str
    exit_price: float
    stop_loss: float
    target: float
    outcome: str               # "WIN", "LOSS", "TIMEOUT"
    pnl_points: float
    pnl_pct: float
    holding_bars: int


@dataclass
class StrategyEvaluationReport:
    """Comprehensive performance report of strategy evaluation over a past time period."""
    symbol: str
    strategy_name: str
    timeframe: str
    period_start: str
    period_end: str
    total_bars: int
    total_signals: int
    call_signals: int
    put_signals: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    total_pnl_points: float
    total_pnl_pct: float
    profit_factor: float
    avg_trade_pnl_pct: float
    trades: List[TradeRecord] = field(default_factory=list)

    def to_summary_string(self) -> str:
        """Formats an executive summary of the historical strategy evaluation."""
        lines = [
            "==================================================================",
            f"📊 HISTORICAL STRATEGY EVALUATION REPORT: {self.symbol}",
            "==================================================================",
            f"Strategy:       {self.strategy_name}",
            f"Evaluation Time: {self.period_start} -> {self.period_end}",
            f"Total Bars:     {self.total_bars} bars [{self.timeframe}]",
            "------------------------------------------------------------------",
            f"Total Signals:  {self.total_signals} (CALL: {self.call_signals}, PUT: {self.put_signals})",
            f"Winning Trades: {self.winning_trades}",
            f"Losing Trades:  {self.losing_trades}",
            f"Win Rate:       {self.win_rate_pct:.1f}%",
            f"Total Return:   {self.total_pnl_pct:+.2f}% ({self.total_pnl_points:+.2f} pts)",
            f"Profit Factor:  {self.profit_factor:.2f}",
            f"Avg Trade PnL:  {self.avg_trade_pnl_pct:+.2f}%",
            "==================================================================",
        ]
        if self.trades:
            lines.append("📋 INDIVIDUAL HISTORICAL TRADES:")
            lines.append(f"{'#':2} | {'Time':16} | {'Dir':4} | {'Pattern':18} | {'Entry':9} | {'Exit':9} | {'Outcome':5} | {'PnL %':6}")
            lines.append("-" * 75)
            for t in self.trades[:15]:
                outcome_icon = "🟢" if t.outcome == "WIN" else "🔴"
                lines.append(
                    f"{t.trade_id:02d} | {str(t.entry_time)[:16]:16} | {t.direction:4} | {t.pattern[:18]:18} | "
                    f"{t.entry_price:9.2f} | {t.exit_price:9.2f} | {outcome_icon} {t.outcome:4} | {t.pnl_pct:+5.2f}%"
                )
            if len(self.trades) > 15:
                lines.append(f"... and {len(self.trades) - 15} more trade(s)")
            lines.append("==================================================================")
        return "\n".join(lines)


class StrategyEvaluator:
    """
    Simulates walk-forward execution of a strategy on past candlestick data.
    Enables rigorous backtesting, win-rate analysis, and signal validation.
    """

    def __init__(
        self,
        strategy: Optional[BaseStrategy] = None,
        risk_reward_ratio: float = 1.5,
        max_holding_bars: int = 5,
        min_bars_warmup: int = 15,
    ):
        self.strategy = strategy or PDFPriceActionStrategy(scan_bars=8, lookback_sr=20)
        self.risk_reward_ratio = risk_reward_ratio
        self.max_holding_bars = max_holding_bars
        self.min_bars_warmup = min_bars_warmup

    def evaluate(
        self,
        df: pd.DataFrame,
        symbol: str = "ASSET",
        timeframe: str = "5m",
        start_date: Optional[Union[str, datetime]] = None,
        end_date: Optional[Union[str, datetime]] = None,
    ) -> StrategyEvaluationReport:
        """
        Executes historical strategy walk-forward evaluation on the given candles.
        """
        # Filter to requested historical period if specified
        if start_date or end_date:
            df = filter_candles_by_date(df, start_date=start_date, end_date=end_date)

        if df is None or len(df) < self.min_bars_warmup:
            return StrategyEvaluationReport(
                symbol=symbol,
                strategy_name=getattr(self.strategy, "name", "PDF Price Action"),
                timeframe=timeframe,
                period_start="N/A",
                period_end="N/A",
                total_bars=0 if df is None else len(df),
                total_signals=0,
                call_signals=0,
                put_signals=0,
                winning_trades=0,
                losing_trades=0,
                win_rate_pct=0.0,
                total_pnl_points=0.0,
                total_pnl_pct=0.0,
                profit_factor=0.0,
                avg_trade_pnl_pct=0.0,
            )

        period_start = str(df.iloc[0]["time"])[:19]
        period_end = str(df.iloc[-1]["time"])[:19]

        trades: List[TradeRecord] = []
        last_signal_idx = -999
        trade_counter = 0

        # Walk-forward candle replay
        n_bars = len(df)
        for i in range(self.min_bars_warmup, n_bars - 1):
            # Avoid firing immediately adjacent duplicate signals
            if i - last_signal_idx < 3:
                continue

            # Historical slice up to candle i (simulates completed closed candles at time i)
            historical_window = df.iloc[: i + 1].copy()
            signal: Optional[Signal] = self.strategy.evaluate(historical_window, symbol=symbol)

            if not signal:
                continue

            last_signal_idx = i
            trade_counter += 1
            entry_price = float(df.iloc[i]["close"])
            entry_time = str(df.iloc[i]["time"])

            # Define SL & Target from signal levels
            sr_level = float(signal.level)
            if signal.direction == Direction.CALL:
                # Support is below entry price
                sl_distance = max(entry_price * 0.002, entry_price - sr_level)
                sl_price = entry_price - sl_distance
                target_price = entry_price + (sl_distance * self.risk_reward_ratio)
            else:
                # Resistance is above entry price
                sl_distance = max(entry_price * 0.002, sr_level - entry_price)
                sl_price = entry_price + sl_distance
                target_price = entry_price - (sl_distance * self.risk_reward_ratio)

            # Forward outcome check over subsequent candles
            exit_price = entry_price
            exit_time = entry_time
            outcome = "TIMEOUT"
            holding_bars = 0

            max_forward = min(n_bars, i + 1 + self.max_holding_bars)
            for f_idx in range(i + 1, max_forward):
                holding_bars += 1
                f_bar = df.iloc[f_idx]
                f_high = float(f_bar["high"])
                f_low = float(f_bar["low"])
                f_close = float(f_bar["close"])
                exit_time = str(f_bar["time"])

                if signal.direction == Direction.CALL:
                    if f_high >= target_price:
                        outcome = "WIN"
                        exit_price = target_price
                        break
                    elif f_low <= sl_price:
                        outcome = "LOSS"
                        exit_price = sl_price
                        break
                else:
                    if f_low <= target_price:
                        outcome = "WIN"
                        exit_price = target_price
                        break
                    elif f_high >= sl_price:
                        outcome = "LOSS"
                        exit_price = sl_price
                        break

            # If still open after max_holding_bars, close at final bar close
            if outcome == "TIMEOUT" and max_forward > i + 1:
                exit_price = float(df.iloc[max_forward - 1]["close"])
                exit_time = str(df.iloc[max_forward - 1]["time"])
                if signal.direction == Direction.CALL:
                    outcome = "WIN" if exit_price > entry_price else "LOSS"
                else:
                    outcome = "WIN" if exit_price < entry_price else "LOSS"

            # Calculate PnL
            if signal.direction == Direction.CALL:
                pnl_pts = exit_price - entry_price
                pnl_pct = (pnl_pts / entry_price) * 100.0
            else:
                pnl_pts = entry_price - exit_price
                pnl_pct = (pnl_pts / entry_price) * 100.0

            trades.append(
                TradeRecord(
                    trade_id=trade_counter,
                    symbol=symbol,
                    direction=signal.direction.value,
                    pattern=signal.pattern,
                    entry_time=entry_time,
                    entry_price=round(entry_price, 2),
                    exit_time=exit_time,
                    exit_price=round(exit_price, 2),
                    stop_loss=round(sl_price, 2),
                    target=round(target_price, 2),
                    outcome=outcome,
                    pnl_points=round(pnl_pts, 2),
                    pnl_pct=round(pnl_pct, 2),
                    holding_bars=holding_bars,
                )
            )

        # Aggregate metrics
        call_signals = sum(1 for t in trades if t.direction == "CALL")
        put_signals = sum(1 for t in trades if t.direction == "PUT")
        wins = sum(1 for t in trades if t.outcome == "WIN")
        losses = sum(1 for t in trades if t.outcome == "LOSS")
        total_pnl_pts = sum(t.pnl_points for t in trades)
        total_pnl_pct = sum(t.pnl_pct for t in trades)
        win_rate = (wins / len(trades) * 100.0) if trades else 0.0

        gross_profit = sum(t.pnl_pct for t in trades if t.pnl_pct > 0)
        gross_loss = abs(sum(t.pnl_pct for t in trades if t.pnl_pct < 0))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 1.0)
        avg_pnl = (total_pnl_pct / len(trades)) if trades else 0.0

        return StrategyEvaluationReport(
            symbol=symbol,
            strategy_name=getattr(self.strategy, "name", "PDF Price Action"),
            timeframe=timeframe,
            period_start=period_start,
            period_end=period_end,
            total_bars=n_bars,
            total_signals=len(trades),
            call_signals=call_signals,
            put_signals=put_signals,
            winning_trades=wins,
            losing_trades=losses,
            win_rate_pct=round(win_rate, 1),
            total_pnl_points=round(total_pnl_pts, 2),
            total_pnl_pct=round(total_pnl_pct, 2),
            profit_factor=round(profit_factor, 2),
            avg_trade_pnl_pct=round(avg_pnl, 2),
            trades=trades,
        )
