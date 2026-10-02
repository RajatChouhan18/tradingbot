"""
txcore.algotrade
~~~~~~~~~~~~~~~~
Universal AlgoTrade Process Model and High-Performance 9-Stage Market-Agnostic Trading Pipeline.

Architectural Guarantees:
  1. Select        - Market, timeframe, symbols, indicators, patterns, strategy via AlgoTradeConfig
  2. Fetch         - Ingests data from any market via injectable BaseDataProvider with TTL cache
  3. Identify      - Parallel/async extraction of candles, VIX, moving averages, and indicators
  4. Detect        - Parallel pattern recognition and indicator applications
  5. Visualization - Parallel background pipeline for creating charts without blocking main loop
  6. Analyze       - Fast multi-factor analysis (VIX, index, indicators, patterns, candles)
  7. Execute       - Strategy evaluation for final signal (CALL/PUT) with key levels
  8. Audit         - Parallel auditing pipeline: data, patterns, charts, SR levels, deduplication
  9. Dispatch      - Non-blocking asynchronous signal dispatch to Telegram, webhooks, or files
  10. Logging      - Non-blocking execution footprints for auditing and tracing
"""

import os
import json
import uuid
import time
import logging
import dataclasses
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

from txcore.models.types import Direction, Signal, SignalStatus
from txcore.providers.base import BaseDataProvider
from txcore.providers.tradingview import TradingViewProvider
from txcore.strategies.base import BaseStrategy
from txcore.strategies.pdf_price_action import PDFPriceActionStrategy
from txcore.execution.base import BaseNotifier
from txcore.execution.telegram import TelegramNotifier
from txcore.execution.file_logger import log_signal_to_file, log_market_data_to_file
from txcore.audit.deduplicator import SignalDeduplicator
from txcore.audit.auditor import TradeAuditor
from txcore.visualization.chart_builder import create_interactive_chart, scan_df_for_patterns
from txcore.analysis.indicators import (
    calculate_ema,
    calculate_sma,
    calculate_rsi,
    calculate_vwap,
    calculate_atr,
    analyze_trend,
)
from txcore.analysis.mtf import (
    evaluate_mtf_trend,
    validate_mtf_confirmation,
)
from txcore.analysis.volatility import analyze_vix
from txcore.stream import telemetry_broadcaster

logger = logging.getLogger(__name__)


class AlgoTradeStatus(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


@dataclass
class AlgoTradeConfig:
    """
    Complete specification for a single AlgoTrade process instance.
    Defines Stage 1 (Select) of the universal pipeline.
    """
    algo_name: str                                   # User-defined name (e.g. "Ishaq strategy 1", "NiftyScalper")
    market: str = "INDIAN_EQUITY"                    # Market (e.g. INDIAN_EQUITY, FOREX, COMMODITY, CRYPTO)
    timeframe: str = "5m"                            # Execution timeframe (e.g. 1m, 5m, 15m, 1h, 1d)
    symbols: List[str] = field(default_factory=list) # Target symbols/assets to monitor
    indices: List[str] = field(default_factory=list) # Benchmark/sectoral indices for context
    data_provider: str = "tradingview"               # Provider identifier
    strategy: str = "pdf_price_action"               # Strategy identifier
    indicators: List[str] = field(default_factory=lambda: ["EMA_20", "EMA_50", "RSI"])
    patterns: List[str] = field(default_factory=lambda: ["bullish_engulfing", "bearish_engulfing", "piercing_line", "dark_cloud_cover"])
    extra_data: List[str] = field(default_factory=lambda: ["vix", "volume", "index_movement"])
    chart_enabled: bool = True
    chart_engine: str = "tradingview"                # "tradingview" or "plotly"
    chart_auto_open: bool = False
    signal_endpoints: List[Dict[str, Any]] = field(default_factory=list)
    audit_enabled: bool = True
    lookback_bars: int = 100
    start_date: Optional[str] = None                 # User-selected start date/time (e.g. "2026-09-01", "2026-09-20 09:15:00")
    end_date: Optional[str] = None                   # User-selected end date/time (e.g. "2026-09-25", "2026-09-26 15:30:00")
    evaluate_strategy: bool = False                  # Historical strategy backtest / walk-forward evaluation mode
    risk_reward_ratio: float = 1.5                   # Risk-to-reward ratio for trade target calculation in evaluation
    enable_mtf: bool = False                         # Multi-Timeframe Confirmation filter
    higher_timeframe: str = "15m"                    # Macro timeframe for trend confirmation
    strict_mtf: bool = False                         # Requires pure trend alignment if True
    use_atr_risk: bool = True                        # Dynamic volatility-based Stop Loss & Target via ATR
    atr_period: int = 14                             # Period for ATR calculation
    atr_multiplier: float = 1.5                      # Multiplier for ATR risk distance
    creator: str = "Admin"                           # Creator / Owner (e.g. "Ishaq", "Admin")
    start_time: Optional[str] = None                 # Daily auto-start time (e.g. "09:15:00")
    stop_time: Optional[str] = None                  # Daily auto-stop time (e.g. "15:30:00")
    description: str = ""                            # Strategy summary/notes
    is_deleted: bool = False                         # Soft-delete flag
    max_workers: int = 8                             # Parallel execution threads for concurrent symbol scans
    async_visualization: bool = True                 # Parallel non-blocking chart generation
    async_audit: bool = True                         # Parallel non-blocking audit logging
    broker_name: str = "PAPER"                       # Target broker ("PAPER", "ZERODHA", "INTERACTIVE_BROKERS")
    discord_webhook_url: Optional[str] = None        # Optional Discord webhook URL
    webhook_url: Optional[str] = None                # Optional Generic JSON webhook URL
    algo_id: str = ""

    def __post_init__(self):
        if not self.algo_id:
            clean_name = "".join(c for c in self.algo_name if c.isalnum()) or "AlgoTrade"
            ts = datetime.now(timezone.utc).strftime("%Y%m%d")
            suffix = uuid.uuid4().hex[:6].upper()
            self.algo_id = f"AT-{clean_name}-{ts}-{suffix}"


class AlgoTrade:
    """
    A single running instance of the universal market-agnostic trading pipeline.
    Internally named AlgoTrade as required by architectural specifications.
    Uses multi-threading to parallelize pattern recognition, indicators, charting, and audit.
    """

    def __init__(
        self,
        config: AlgoTradeConfig,
        provider: Optional[BaseDataProvider] = None,
        strategy: Optional[BaseStrategy] = None,
        notifiers: Optional[List[BaseNotifier]] = None,
    ):
        self.config = config
        self.algo_name = config.algo_name
        self.algo_id = config.algo_id
        self.status = AlgoTradeStatus.IDLE
        self.created_at = datetime.now(timezone.utc)
        self.cycle_count = 0
        self.signals_generated = 0
        self.signals_dispatched = 0
        self.last_scan_at: Optional[datetime] = None
        self.error_log: List[Dict[str, Any]] = []
        self.signals_history: List[Dict[str, Any]] = []
        self.pnl_history: List[Dict[str, Any]] = []
        self.total_pnl_pct: float = 0.0
        self.total_pnl_points: float = 0.0
        self.win_count: int = 0
        self.loss_count: int = 0
        self.last_cycle_duration_ms: float = 0.0
        self.symbol_latencies_ms: Dict[str, float] = {}
        self.total_cycle_time_ms: float = 0.0

        # Thread pool for parallel computation (visualization, audit, indicators)
        self._executor = ThreadPoolExecutor(
            max_workers=max(4, config.max_workers),
            thread_name_prefix=f"AlgoTrade-{self.algo_name[:10]}",
        )

        # Injected Data Provider (Stage 2)
        if provider:
            self.provider = provider
        elif config.market.upper() in ("INDIAN_EQUITY", "INDIAN", "NSE", "BSE"):
            from txcore.providers.indian_provider import IndianMarketDataProvider
            self.provider = IndianMarketDataProvider()
        else:
            self.provider = TradingViewProvider()

        # Injected Strategy Engine (Stage 7)
        if strategy:
            self.strategy = strategy
        else:
            self.strategy = PDFPriceActionStrategy(scan_bars=8, lookback_sr=20)

        # Injected Notifiers (Stage 9)
        self.notifiers = list(notifiers or [])
        if getattr(config, "discord_webhook_url", None):
            from txcore.execution.discord import DiscordNotifier
            self.notifiers.append(DiscordNotifier(config.discord_webhook_url))
        if getattr(config, "webhook_url", None):
            from txcore.execution.webhook import WebhookNotifier
            self.notifiers.append(WebhookNotifier(config.webhook_url))

        # Audit & Deduplication (Stage 8)
        self.deduplicator = SignalDeduplicator(max_age_seconds=86400.0)
        self.auditor = TradeAuditor(algo_id=self.algo_id)
        self.db_id: Optional[str] = None

    def evaluate_historical(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Any:
        """
        Executes a historical strategy walk-forward evaluation / backtest on past candles.
        Returns a StrategyEvaluationReport with win-rate, PnL %, profit factor, and trade log.
        """
        from txcore.strategies.evaluator import StrategyEvaluator

        s_date = start_date or self.config.start_date
        e_date = end_date or self.config.end_date

        if hasattr(self.provider, "get_cached_candles"):
            raw_df = self.provider.get_cached_candles(
                symbol,
                timeframe=self.config.timeframe,
                lookback_bars=self.config.lookback_bars,
                start_date=s_date,
                end_date=e_date,
            )
        else:
            raw_df = self.provider.get_candles(
                symbol,
                timeframe=self.config.timeframe,
                lookback_bars=self.config.lookback_bars,
                start_date=s_date,
                end_date=e_date,
            )

        evaluator = StrategyEvaluator(
            strategy=self.strategy,
            risk_reward_ratio=self.config.risk_reward_ratio,
        )
        return evaluator.evaluate(
            df=raw_df,
            symbol=symbol,
            timeframe=self.config.timeframe,
            start_date=s_date,
            end_date=e_date,
        )

    # =========================================================================
    # THE 9-STEP UNIVERSAL PIPELINE EXECUTION (OPTIMIZED & PARALLELIZED)
    # =========================================================================

    def execute_pipeline(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Executes the complete 9-step pipeline for a single symbol with maximal
        computation saving and parallel/async non-blocking workers.
        """
        t_pipe_start = time.perf_counter()
        try:
            # -------------------------------------------------------------
            # STEP 1: SELECT (Loaded from self.config)
            # -------------------------------------------------------------
            tf = self.config.timeframe
            lookback = self.config.lookback_bars

            # -------------------------------------------------------------
            # STEP 2: FETCH (Data Ingestion with In-Memory Cache & Date Range)
            # -------------------------------------------------------------
            # Uses provider's get_cached_candles to save redundant network fetches
            if hasattr(self.provider, "get_cached_candles"):
                raw_df = self.provider.get_cached_candles(
                    symbol,
                    timeframe=tf,
                    lookback_bars=lookback,
                    start_date=self.config.start_date,
                    end_date=self.config.end_date,
                )
            else:
                raw_df = self.provider.get_candles(
                    symbol,
                    timeframe=tf,
                    lookback_bars=lookback,
                    start_date=self.config.start_date,
                    end_date=self.config.end_date,
                )

            if raw_df is None or len(raw_df) < 5:
                logger.debug(f"[{self.algo_name}] Insufficient bars for {symbol}")
                return None

            # Asynchronous raw footprint logging (non-blocking)
            self._executor.submit(log_market_data_to_file, symbol, raw_df)

            # Historical Strategy Evaluation Mode (Backtesting on past data)
            if self.config.evaluate_strategy:
                report = self.evaluate_historical(symbol)
                chart_path = None
                if self.config.chart_enabled:
                    try:
                        chart_path = create_interactive_chart(
                            raw_df,
                            symbol=symbol,
                            lookback_bars=lookback,
                            engine=self.config.chart_engine,
                            auto_open=self.config.chart_auto_open,
                        )
                    except Exception as c_err:
                        logger.debug(f"[{self.algo_name}] Chart error: {c_err}")

                return {
                    "symbol": symbol,
                    "evaluation": report,
                    "signal": None,
                    "chart_path": chart_path,
                }

            # Live Paper Trading tick update for active positions
            try:
                from txcore.execution.paper_engine import get_paper_engine
                last_bar = raw_df.iloc[-1]
                get_paper_engine().update_price_tick(
                    symbol,
                    ltp=float(last_bar["close"]),
                    high=float(last_bar.get("high", last_bar["close"])),
                    low=float(last_bar.get("low", last_bar["close"])),
                )
            except Exception as pe_tick_err:
                logger.debug(f"Paper tick update error: {pe_tick_err}")

            # Drop current in-progress bar for closed-candle analysis
            completed_df = raw_df.iloc[:-1].copy()
            if len(completed_df) < 5:
                return None

            # -------------------------------------------------------------
            # STEP 3 & 4: IDENTIFY & DETECT (Parallel Indicator & Pattern Tasks)
            # -------------------------------------------------------------
            # Save computation: precalculate requested indicators in a single vectorized pass
            if hasattr(self.provider, "precalculate_indicators"):
                completed_df = self.provider.precalculate_indicators(completed_df, self.config.indicators)

            # Run Pattern Detection and Trend Analysis concurrently in thread pool
            pattern_future = self._executor.submit(scan_df_for_patterns, completed_df)
            trend_future = self._executor.submit(analyze_trend, completed_df, symbol, tf)

            detected_patterns = pattern_future.result()
            trend_info = trend_future.result()

            identified_data: Dict[str, Any] = {
                "trend": trend_info,
                "rsi": float(completed_df["rsi"].iloc[-1]) if "rsi" in completed_df.columns else None,
                "ema_20": float(completed_df["ema_20"].iloc[-1]) if "ema_20" in completed_df.columns else None,
                "ema_50": float(completed_df["ema_50"].iloc[-1]) if "ema_50" in completed_df.columns else None,
            }

            # -------------------------------------------------------------
            # STEP 5: VISUALIZATION (Parallel Non-Blocking Pipeline)
            # -------------------------------------------------------------
            chart_future = None
            if self.config.chart_enabled:
                if self.config.async_visualization:
                    # Submit chart generation to background thread without stalling signal discovery!
                    chart_future = self._executor.submit(
                        create_interactive_chart,
                        raw_df.copy(),
                        symbol=symbol,
                        lookback_bars=lookback,
                        engine=self.config.chart_engine,
                        auto_open=self.config.chart_auto_open,
                    )
                else:
                    try:
                        chart_path = create_interactive_chart(
                            raw_df.copy(),
                            symbol=symbol,
                            lookback_bars=lookback,
                            engine=self.config.chart_engine,
                            auto_open=self.config.chart_auto_open,
                        )
                    except Exception as c_err:
                        chart_path = None
                        logger.debug(f"[{self.algo_name}] Chart error: {c_err}")

            # -------------------------------------------------------------
            # STEP 6: ANALYZE (Multi-Factor Analysis)
            # -------------------------------------------------------------
            analysis_factors = {
                "trend_state": trend_info.get("trend"),
                "support_level": trend_info.get("support"),
                "resistance_level": trend_info.get("resistance"),
                "rsi": identified_data.get("rsi"),
                "patterns_count": len(detected_patterns),
            }

            # Optional Multi-Timeframe (MTF) Trend Analysis
            htf_info: Dict[str, Any] = {}
            if self.config.enable_mtf:
                htf_info = evaluate_mtf_trend(
                    completed_df,
                    base_timeframe=tf,
                    higher_timeframe=self.config.higher_timeframe,
                    provider=self.provider,
                    symbol=symbol,
                )
                analysis_factors["htf_trend"] = htf_info.get("trend")

            # -------------------------------------------------------------
            # STEP 7: EXECUTE (Strategy Evaluation for CALL/PUT Signal)
            # -------------------------------------------------------------
            signal: Optional[Signal] = self.strategy.evaluate(completed_df, symbol=symbol)
            if not signal:
                chart_res = chart_future.result() if chart_future and not self.config.async_visualization else None
                return {
                    "symbol": symbol,
                    "signal": None,
                    "trend": trend_info,
                    "patterns": detected_patterns,
                    "chart_path": chart_res,
                }

            # Multi-Timeframe Confirmation Filter
            if self.config.enable_mtf:
                is_mtf_ok, mtf_reason = validate_mtf_confirmation(
                    signal.direction,
                    htf_trend=htf_info.get("trend", "SIDEWAYS"),
                    strict=self.config.strict_mtf,
                )
                if not is_mtf_ok:
                    logger.info(f"[{self.algo_name}] Signal for {symbol} filtered by MTF: {mtf_reason}")
                    if self.config.audit_enabled:
                        self.auditor.record_signal(
                            symbol=signal.pair,
                            direction=signal.direction.value,
                            pattern=signal.pattern,
                            status="BLOCKED",
                            reason=f"MTF Filter: {mtf_reason}",
                            algo_id=self.algo_id,
                            indicator_snapshot=analysis_factors,
                            level_snapshot={"support": trend_info.get("support"), "resistance": trend_info.get("resistance")},
                            latency_ms=int((time.perf_counter() - t_pipe_start) * 1000),
                        )
                    return None
                signal.metadata["mtf_trend"] = htf_info.get("trend")
                signal.metadata["mtf_timeframe"] = self.config.higher_timeframe

            # Risk Management & Circuit Breaker Guard
            try:
                from txcore.filters.risk_manager import get_risk_manager
                rm = get_risk_manager()
                is_risk_ok, risk_block_reason = rm.is_allowed(symbol)
                if not is_risk_ok:
                    logger.info(f"[{self.algo_name}] Signal for {symbol} blocked by Risk Guard: {risk_block_reason}")
                    if self.config.audit_enabled:
                        self.auditor.record_signal(
                            symbol=signal.pair,
                            direction=signal.direction.value,
                            pattern=signal.pattern,
                            status="BLOCKED",
                            reason=f"Risk Guard: {risk_block_reason}",
                            algo_id=self.algo_id,
                            indicator_snapshot=analysis_factors,
                            level_snapshot={"support": trend_info.get("support"), "resistance": trend_info.get("resistance")},
                            latency_ms=int((time.perf_counter() - t_pipe_start) * 1000),
                        )
                    return None
            except Exception as rm_err:
                logger.debug(f"Risk guard check error: {rm_err}")

            self.signals_generated += 1
            signal.provider = f"AlgoTrade:{self.algo_name}"
            signal.timeframe = tf

            # Dynamic Volatility & ATR Risk Management
            entry_price = float(signal.price)
            level = float(signal.level)
            atr_val = None
            if self.config.use_atr_risk:
                atr_series = calculate_atr(completed_df, period=self.config.atr_period)
                if not atr_series.empty and not pd.isna(atr_series.iloc[-1]):
                    atr_val = float(atr_series.iloc[-1])

            if atr_val is not None and atr_val > 0:
                atr_buffer = atr_val * self.config.atr_multiplier
                sr_risk = abs(entry_price - level)
                risk_dist = max(atr_buffer, sr_risk)
            else:
                risk_dist = max(entry_price * 0.002, abs(entry_price - level))

            if signal.direction == Direction.CALL:
                stop_loss = entry_price - risk_dist
                target = entry_price + (risk_dist * self.config.risk_reward_ratio)
            else:
                stop_loss = entry_price + risk_dist
                target = entry_price - (risk_dist * self.config.risk_reward_ratio)

            signal.metadata["stop_loss"] = stop_loss
            signal.metadata["target"] = target
            signal.metadata["risk_reward"] = self.config.risk_reward_ratio
            if atr_val is not None:
                signal.metadata["atr"] = atr_val

            # -------------------------------------------------------------
            # STEP 8: AUDIT (Parallel Auditing Pipeline)
            # -------------------------------------------------------------
            if self.deduplicator.is_duplicate(signal.pair, signal.pattern, signal.candle_time):
                logger.info(f"[{self.algo_name}] Duplicate signal suppressed for {symbol}")
                return None

            self.deduplicator.record(signal.pair, signal.pattern, signal.candle_time)

            if self.config.audit_enabled:
                aud_kwargs = {
                    "symbol": signal.pair,
                    "direction": signal.direction.value,
                    "pattern": signal.pattern,
                    "status": "APPROVED",
                    "reason": f"AlgoTrade:{self.algo_name}",
                    "algo_id": self.algo_id,
                    "indicator_snapshot": analysis_factors,
                    "level_snapshot": {
                        "entry_price": entry_price,
                        "level": level,
                        "stop_loss": round(stop_loss, 2),
                        "target": round(target, 2),
                        "atr": atr_val,
                    },
                    "latency_ms": int((time.perf_counter() - t_pipe_start) * 1000),
                }
                if self.config.async_audit:
                    self._executor.submit(self.auditor.record_signal, **aud_kwargs)
                else:
                    self.auditor.record_signal(**aud_kwargs)

            # Resolve chart path if chart generation was parallelized
            resolved_chart_path = None
            if chart_future:
                try:
                    resolved_chart_path = chart_future.result(timeout=5.0)
                except Exception as cf_err:
                    logger.debug(f"Chart future wait timeout: {cf_err}")

            # -------------------------------------------------------------
            # STEP 9: DISPATCH (Alert Distribution)
            # -------------------------------------------------------------
            alert_text = signal.to_alert_message(version_tag=f"AlgoTrade: {self.algo_name}")

            # Non-blocking file logging footprint
            self._executor.submit(log_signal_to_file, alert_text)

            # Dispatch to configured notifiers
            dispatched = False
            for notifier in self.notifiers:
                try:
                    sent = notifier.send(alert_text, signal=signal, chart_path=resolved_chart_path)
                    if sent:
                        dispatched = True
                except Exception as n_err:
                    logger.warning(f"Notifier error on dispatch: {n_err}")

            if dispatched:
                self.signals_dispatched += 1

            # Generate Audit Chart (timeframe = trade timeframe + 30 candles)
            audit_chart_path = None
            if self.config.chart_enabled:
                try:
                    audit_chart_path = create_interactive_chart(
                        raw_df.copy(),
                        symbol=symbol,
                        lookback_bars=lookback + 30,
                        signal=signal,
                        engine=self.config.chart_engine,
                        auto_open=False,
                    )
                except Exception as ac_err:
                    logger.debug(f"[{self.algo_name}] Audit chart error: {ac_err}")

            latest_close = float(raw_df.iloc[-1]["close"])
            if signal.direction == Direction.CALL:
                pnl_pts = latest_close - entry_price
                outcome = "WIN" if pnl_pts >= 0 else "LOSS"
            else:
                pnl_pts = entry_price - latest_close
                outcome = "WIN" if pnl_pts >= 0 else "LOSS"
            pnl_pct = (pnl_pts / entry_price) * 100 if entry_price > 0 else 0.0

            sig_id = f"SIG-{symbol}-{int(time.time() * 1000)}"
            signal_record = {
                "id": sig_id,
                "signal_id": sig_id,
                "algo_id": self.algo_id,
                "algo_name": self.algo_name,
                "creator": getattr(self.config, "creator", "Admin"),
                "symbol": symbol,
                "timeframe": tf,
                "direction": signal.direction.value,
                "pattern": signal.pattern,
                "price": entry_price,
                "level": level,
                "stop_loss": round(stop_loss, 2),
                "target": round(target, 2),
                "atr": round(atr_val, 4) if atr_val is not None else None,
                "mtf_trend": signal.metadata.get("mtf_trend"),
                "candle_time": str(signal.candle_time),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "chart_path": resolved_chart_path,
                "audit_chart_path": audit_chart_path,
                "dispatched": dispatched,
                "outcome": outcome,
                "pnl_pct": round(pnl_pct, 2),
                "pnl_points": round(pnl_pts, 2),
            }
            self.signals_history.append(signal_record)
            pnl_entry = {
                "signal_id": sig_id,
                "algo_id": self.algo_id,
                "algo_name": self.algo_name,
                "symbol": symbol,
                "direction": signal.direction.value,
                "entry_price": entry_price,
                "exit_price": round(latest_close, 2),
                "outcome": outcome,
                "pnl_pct": round(pnl_pct, 2),
                "pnl_points": round(pnl_pts, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self.pnl_history.append(pnl_entry)

            # Non-blocking async DB persistence
            try:
                from txcore.persistence import dispatch_save_signal, dispatch_save_pnl
                dispatch_save_signal(signal_record)
                dispatch_save_pnl(pnl_entry)
            except Exception as pe_err:
                logger.debug(f"Persistence dispatch error: {pe_err}")

            # Automatic Order Execution (routes to BrokerManager adapter or Paper Engine)
            try:
                from txcore.execution.broker_adapter import get_broker_manager, OrderSide
                bm = get_broker_manager()
                broker_name = getattr(self.config, "broker_name", None) or bm.active_broker_name
                adapter = bm.get_adapter(broker_name)
                side_enum = OrderSide.BUY if signal.direction == Direction.CALL else OrderSide.SELL
                adapter.place_order(
                    symbol=symbol,
                    side=side_enum,
                    quantity=1,
                    price=entry_price,
                    stop_loss=stop_loss,
                    target=target,
                    tag=self.algo_id,
                )
            except Exception as b_exec_err:
                logger.debug(f"Broker order placement error: {b_exec_err}")

            self.total_pnl_pct += pnl_pct
            self.total_pnl_points += pnl_pts
            if outcome == "WIN":
                self.win_count += 1
            else:
                self.loss_count += 1

            # Update Risk Guard with trade outcome
            try:
                from txcore.filters.risk_manager import get_risk_manager
                get_risk_manager().record_trade_result(outcome, pnl_pts)
            except Exception as rg_err:
                logger.debug(f"Risk guard outcome record error: {rg_err}")

            telemetry_broadcaster.broadcast_sync("signal_alert", {
                "signal": signal_record,
                "algo_name": self.algo_name,
                "algo_id": self.algo_id,
            })

            return {
                "symbol": symbol,
                "signal": signal,
                "signal_record": signal_record,
                "chart_path": resolved_chart_path,
                "audit_chart_path": audit_chart_path,
                "analysis": analysis_factors,
                "dispatched": dispatched,
                "pnl": {
                    "outcome": outcome,
                    "pnl_pct": round(pnl_pct, 2),
                    "pnl_points": round(pnl_pts, 2),
                },
            }

        except Exception as e:
            err_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "symbol": symbol,
                "error": str(e),
            }
            self.error_log.append(err_entry)
            logger.error(f"[{self.algo_name}] Error executing pipeline on {symbol}: {e}")
            return None
        finally:
            elapsed_ms = (time.perf_counter() - t_pipe_start) * 1000.0
            self.symbol_latencies_ms[symbol] = round(elapsed_ms, 2)

    def run_cycle(self) -> List[Dict[str, Any]]:
        """
        Executes one scan cycle across all configured symbols CONCURRENTLY in parallel
        threads to save time and achieve sub-second execution latency.
        """
        t_cycle_start = time.perf_counter()
        self.status = AlgoTradeStatus.RUNNING
        self.cycle_count += 1
        self.last_scan_at = datetime.now(timezone.utc)
        results: List[Dict[str, Any]] = []

        symbols = self.config.symbols
        if not symbols and self.config.market.upper() in ("INDIAN_EQUITY", "INDIAN"):
            symbols = ["NIFTY", "BANKNIFTY", "RELIANCE", "TCS", "HDFCBANK"]

        # Run symbols in parallel using thread pool
        futures = {self._executor.submit(self.execute_pipeline, sym): sym for sym in symbols}
        for fut in as_completed(futures):
            res = fut.result()
            if res:
                results.append(res)

        self.last_cycle_duration_ms = (time.perf_counter() - t_cycle_start) * 1000.0
        self.total_cycle_time_ms += self.last_cycle_duration_ms

        telemetry_broadcaster.broadcast_sync("cycle_update", {
            "algo_id": self.algo_id,
            "algo_name": self.algo_name,
            "cycle_count": self.cycle_count,
            "cycle_duration_ms": round(self.last_cycle_duration_ms, 2),
            "metrics": self.get_metrics(),
            "results_count": len(results),
        })

        return results

    def get_concurrency_stats(self) -> Dict[str, Any]:
        """Provides transparent real-time telemetry on the worker threads and execution latency."""
        threads = getattr(self._executor, "_threads", set())
        active_threads = len([t for t in threads if t.is_alive()]) if threads else 0
        queue_size = getattr(getattr(self._executor, "_work_queue", None), "qsize", lambda: 0)()
        avg_symbol_latency = (
            sum(self.symbol_latencies_ms.values()) / len(self.symbol_latencies_ms)
            if self.symbol_latencies_ms else 0.0
        )
        return {
            "model": "Multi-threaded Parallel Pipeline",
            "max_workers": max(4, self.config.max_workers),
            "active_worker_threads": active_threads,
            "queue_depth": queue_size,
            "last_cycle_duration_ms": round(self.last_cycle_duration_ms, 2),
            "avg_symbol_latency_ms": round(avg_symbol_latency, 2),
            "symbol_latencies_ms": dict(self.symbol_latencies_ms),
            "async_visualization": self.config.async_visualization,
            "async_audit": self.config.async_audit,
            "total_symbols": len(self.config.symbols),
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Returns live execution state and statistics for this AlgoTrade."""
        total_trades = self.win_count + self.loss_count
        win_rate = (self.win_count / total_trades * 100) if total_trades > 0 else 0.0
        return {
            "algo_name": self.algo_name,
            "algo_id": self.algo_id,
            "market": self.config.market,
            "timeframe": self.config.timeframe,
            "symbols": self.config.symbols,
            "indices": self.config.indices,
            "status": self.status.value,
            "creator": getattr(self.config, "creator", "Admin"),
            "start_time": getattr(self.config, "start_time", None),
            "stop_time": getattr(self.config, "stop_time", None),
            "start_date": self.config.start_date,
            "end_date": self.config.end_date,
            "is_deleted": getattr(self.config, "is_deleted", False),
            "description": getattr(self.config, "description", ""),
            "created_at": self.created_at.isoformat(),
            "cycle_count": self.cycle_count,
            "signals_generated": self.signals_generated,
            "signals_dispatched": self.signals_dispatched,
            "signals_count": len(self.signals_history),
            "win_count": self.win_count,
            "loss_count": self.loss_count,
            "win_rate_pct": round(win_rate, 1),
            "total_pnl_pct": round(self.total_pnl_pct, 2),
            "total_pnl_points": round(self.total_pnl_points, 2),
            "last_scan_at": self.last_scan_at.isoformat() if self.last_scan_at else None,
            "error_count": len(self.error_log),
            "concurrency": self.get_concurrency_stats(),
            "config": dataclasses.asdict(self.config),
        }

    def close(self):
        """Clean shutdown of the internal background thread pool."""
        self.status = AlgoTradeStatus.STOPPED
        self._executor.shutdown(wait=False)


class AlgoTradeManager:
    """
    Orchestrates the lifecycle of multiple named AlgoTrade instances concurrently.
    Provides registration, monitoring, status queries, and parallel batch execution.
    """

    def __init__(self):
        self._algos: Dict[str, AlgoTrade] = {}

    def register_algo(
        self,
        config: AlgoTradeConfig,
        provider: Optional[BaseDataProvider] = None,
        strategy: Optional[BaseStrategy] = None,
        notifiers: Optional[List[BaseNotifier]] = None,
    ) -> AlgoTrade:
        """Instantiates and registers a new AlgoTrade instance."""
        algo = AlgoTrade(config=config, provider=provider, strategy=strategy, notifiers=notifiers)
        self._algos[algo.algo_id] = algo
        logger.info(f"Registered AlgoTrade: '{algo.algo_name}' (ID: {algo.algo_id})")
        try:
            from txcore.persistence import _run_coroutine_in_worker, save_algo_to_db
            _run_coroutine_in_worker(save_algo_to_db(algo))
        except Exception as pe:
            logger.debug(f"Algo registration DB sync: {pe}")
        return algo

    def get_algo(self, algo_id: str) -> Optional[AlgoTrade]:
        """Retrieves an AlgoTrade by its unique algo_id."""
        return self._algos.get(algo_id)

    def get_algo_by_name(self, name: str) -> Optional[AlgoTrade]:
        """Retrieves an AlgoTrade by human-readable name."""
        for algo in self._algos.values():
            if algo.algo_name.lower() == name.lower():
                return algo
        return None

    def list_algos(self, include_deleted: bool = False) -> List[Dict[str, Any]]:
        """Returns summary metrics for all registered AlgoTrades."""
        algos = list(self._algos.values())
        if not include_deleted:
            algos = [a for a in algos if not getattr(a.config, "is_deleted", False)]
        return [algo.get_metrics() for algo in algos]

    def copy_algo(self, algo_id: str) -> Optional[AlgoTrade]:
        """Clones an existing AlgoTrade strategy with a new collision-resistant ID."""
        orig = self.get_algo(algo_id)
        if not orig:
            return None
        cfg_dict = dataclasses.asdict(orig.config)
        cfg_dict["algo_name"] = f"Copy of {orig.algo_name}"
        cfg_dict["algo_id"] = ""  # Trigger clean ID generation in post_init
        new_config = AlgoTradeConfig(**cfg_dict)
        return self.register_algo(
            new_config,
            provider=orig.provider,
            strategy=orig.strategy,
            notifiers=orig.notifiers,
        )

    def delete_algo(self, algo_id: str, hard: bool = False) -> bool:
        """Soft-deletes or purges an AlgoTrade instance."""
        algo = self.get_algo(algo_id)
        if not algo:
            return False
        algo.status = AlgoTradeStatus.STOPPED
        if hard:
            del self._algos[algo_id]
        else:
            algo.config.is_deleted = True
        try:
            from txcore.persistence import _run_coroutine_in_worker, delete_algo_in_db
            _run_coroutine_in_worker(delete_algo_in_db(algo_id, hard=hard))
        except Exception as pe:
            logger.debug(f"Algo deletion DB sync: {pe}")
        return True

    def start_algo(self, algo_id: str) -> Optional[List[Dict[str, Any]]]:
        """Starts an AlgoTrade and executes a cycle immediately."""
        algo = self.get_algo(algo_id)
        if not algo:
            return None
        algo.status = AlgoTradeStatus.RUNNING
        try:
            from txcore.persistence import _run_coroutine_in_worker, update_algo_status_in_db
            _run_coroutine_in_worker(update_algo_status_in_db(algo_id, "RUNNING"))
        except Exception as pe:
            logger.debug(f"Algo start DB sync: {pe}")
        return algo.run_cycle()

    def stop_algo(self, algo_id: str) -> bool:
        """Stops an AlgoTrade."""
        algo = self.get_algo(algo_id)
        if not algo:
            return False
        algo.status = AlgoTradeStatus.STOPPED
        try:
            from txcore.persistence import _run_coroutine_in_worker, update_algo_status_in_db
            _run_coroutine_in_worker(update_algo_status_in_db(algo_id, "STOPPED"))
        except Exception as pe:
            logger.debug(f"Algo stop DB sync: {pe}")
        return True

    def pause_algo(self, algo_id: str) -> bool:
        """Pauses an AlgoTrade."""
        algo = self.get_algo(algo_id)
        if not algo:
            return False
        algo.status = AlgoTradeStatus.PAUSED
        try:
            from txcore.persistence import _run_coroutine_in_worker, update_algo_status_in_db
            _run_coroutine_in_worker(update_algo_status_in_db(algo_id, "PAUSED"))
        except Exception as pe:
            logger.debug(f"Algo pause DB sync: {pe}")
        return True

    def get_all_signals(self, algo_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Collects all generated signals across all AlgoTrades or for a specific one."""
        signals = []
        if algo_id:
            algo = self.get_algo(algo_id)
            if algo:
                signals.extend(algo.signals_history)
        else:
            for algo in self._algos.values():
                signals.extend(algo.signals_history)
        signals.sort(key=lambda s: s.get("generated_at", ""), reverse=True)
        return signals

    def get_signal_by_id(self, sig_id: str) -> Optional[Dict[str, Any]]:
        """Finds a specific signal record across all AlgoTrades."""
        for algo in self._algos.values():
            for sig in algo.signals_history:
                if sig.get("id") == sig_id or sig.get("signal_id") == sig_id:
                    return sig
        return None

    def get_all_pnl(self, algo_id: Optional[str] = None) -> Dict[str, Any]:
        """Computes consolidated PnL statistics across all trades."""
        trades = []
        if algo_id:
            algo = self.get_algo(algo_id)
            if algo:
                trades.extend(algo.pnl_history)
        else:
            for algo in self._algos.values():
                trades.extend(algo.pnl_history)

        trades.sort(key=lambda t: t.get("timestamp", ""), reverse=True)
        total = len(trades)
        wins = sum(1 for t in trades if t.get("outcome") == "WIN")
        losses = sum(1 for t in trades if t.get("outcome") == "LOSS")
        total_pnl_pct = sum(t.get("pnl_pct", 0.0) for t in trades)
        total_pnl_pts = sum(t.get("pnl_points", 0.0) for t in trades)
        win_rate = (wins / total * 100) if total > 0 else 0.0

        # Calculate profit factor
        gross_profit = sum(t.get("pnl_points", 0.0) for t in trades if t.get("pnl_points", 0.0) > 0)
        gross_loss = abs(sum(t.get("pnl_points", 0.0) for t in trades if t.get("pnl_points", 0.0) < 0))
        pf = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 1.0)

        return {
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "win_rate_pct": round(win_rate, 1),
            "total_pnl_pct": round(total_pnl_pct, 2),
            "total_pnl_points": round(total_pnl_pts, 2),
            "profit_factor": round(pf, 2),
            "trades": trades,
        }

    def run_all_cycles(self) -> Dict[str, List[Dict[str, Any]]]:
        """Executes one scan cycle across all registered AlgoTrades in parallel."""
        results: Dict[str, List[Dict[str, Any]]] = {}
        for algo_id, algo in self._algos.items():
            if algo.status != AlgoTradeStatus.STOPPED and not getattr(algo.config, "is_deleted", False):
                results[algo.algo_name] = algo.run_cycle()
        return results

    def get_concurrency_overview(self) -> Dict[str, Any]:
        """Returns consolidated concurrency telemetry across all managed AlgoTrades."""
        total_workers = sum(getattr(a.config, "max_workers", 4) for a in self._algos.values() if not getattr(a.config, "is_deleted", False))
        active_threads = 0
        for a in self._algos.values():
            if a.status == AlgoTradeStatus.RUNNING:
                threads = getattr(a._executor, "_threads", set())
                active_threads += len([t for t in threads if t.is_alive()]) if threads else 0
        return {
            "total_algos_active": sum(1 for a in self._algos.values() if a.status == AlgoTradeStatus.RUNNING),
            "total_max_workers": total_workers,
            "total_active_threads": active_threads,
            "algos_breakdown": {
                a.algo_name: a.get_concurrency_stats()
                for a in self._algos.values()
                if not getattr(a.config, "is_deleted", False)
            },
        }



# =============================================================================
# Backward-Compatible Aliases for Legacy Code & Tests
# =============================================================================
TradeAlgo = AlgoTrade
TradeAlgoConfig = AlgoTradeConfig
TradeAlgoStatus = AlgoTradeStatus
TradeAlgoManager = AlgoTradeManager
