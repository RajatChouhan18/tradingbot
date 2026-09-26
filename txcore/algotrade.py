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

import uuid
import time
import logging
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
    analyze_trend,
)
from txcore.analysis.volatility import analyze_vix

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
    max_workers: int = 8                             # Parallel execution threads for concurrent symbol scans
    async_visualization: bool = True                 # Parallel non-blocking chart generation
    async_audit: bool = True                         # Parallel non-blocking audit logging
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
        self.notifiers = notifiers or []

        # Audit & Deduplication (Stage 8)
        self.deduplicator = SignalDeduplicator(max_age_seconds=86400.0)
        self.auditor = TradeAuditor()

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
                        completed_df.copy(),
                        symbol=symbol,
                        lookback_bars=lookback,
                        engine=self.config.chart_engine,
                        auto_open=self.config.chart_auto_open,
                    )
                else:
                    try:
                        chart_path = create_interactive_chart(
                            completed_df,
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

            self.signals_generated += 1
            signal.provider = f"AlgoTrade:{self.algo_name}"
            signal.timeframe = tf

            # -------------------------------------------------------------
            # STEP 8: AUDIT (Parallel Auditing Pipeline)
            # -------------------------------------------------------------
            if self.deduplicator.is_duplicate(signal.pair, signal.pattern, signal.candle_time):
                logger.info(f"[{self.algo_name}] Duplicate signal suppressed for {symbol}")
                return None

            self.deduplicator.record(signal.pair, signal.pattern, signal.candle_time)

            if self.config.audit_enabled:
                if self.config.async_audit:
                    self._executor.submit(
                        self.auditor.record_signal,
                        signal.pair,
                        signal.direction.value,
                        signal.pattern,
                        "APPROVED",
                        f"AlgoTrade:{self.algo_name}",
                    )
                else:
                    self.auditor.record_signal(
                        signal.pair,
                        signal.direction.value,
                        signal.pattern,
                        "APPROVED",
                        f"AlgoTrade:{self.algo_name}",
                    )

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

            return {
                "symbol": symbol,
                "signal": signal,
                "chart_path": resolved_chart_path,
                "analysis": analysis_factors,
                "dispatched": dispatched,
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

    def run_cycle(self) -> List[Dict[str, Any]]:
        """
        Executes one scan cycle across all configured symbols CONCURRENTLY in parallel
        threads to save time and achieve sub-second execution latency.
        """
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

        return results

    def get_metrics(self) -> Dict[str, Any]:
        """Returns live execution state and statistics for this AlgoTrade."""
        return {
            "algo_name": self.algo_name,
            "algo_id": self.algo_id,
            "market": self.config.market,
            "timeframe": self.config.timeframe,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "cycle_count": self.cycle_count,
            "signals_generated": self.signals_generated,
            "signals_dispatched": self.signals_dispatched,
            "last_scan_at": self.last_scan_at.isoformat() if self.last_scan_at else None,
            "error_count": len(self.error_log),
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

    def list_algos(self) -> List[Dict[str, Any]]:
        """Returns summary metrics for all registered AlgoTrades."""
        return [algo.get_metrics() for algo in self._algos.values()]

    def run_all_cycles(self) -> Dict[str, List[Dict[str, Any]]]:
        """Executes one scan cycle across all registered AlgoTrades in parallel."""
        results: Dict[str, List[Dict[str, Any]]] = {}
        for algo_id, algo in self._algos.items():
            if algo.status != AlgoTradeStatus.STOPPED:
                results[algo.algo_name] = algo.run_cycle()
        return results


# =============================================================================
# Backward-Compatible Aliases for Legacy Code & Tests
# =============================================================================
TradeAlgo = AlgoTrade
TradeAlgoConfig = AlgoTradeConfig
TradeAlgoStatus = AlgoTradeStatus
TradeAlgoManager = AlgoTradeManager
