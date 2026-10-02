"""
txcore.service
~~~~~~~~~~~~~~
Universal High-Performance FastAPI Backend Service for the TxBot AlgoTrade Platform.
Serves REST API endpoints for non-technical frontend users:
  - AlgoTrade Strategy Creation, Lifecycle (Start, Stop, Pause, Delete, Copy) & Scheduling
  - Historical Strategy Evaluation & Walk-Forward Backtesting
  - Signal Dispatch, Detail Views with Execution Chart + 30-Candle Audit Chart, and Resend Signal
  - Consolidated PnL Tracking and Performance Analytics
  - Market Data Layer queries, saved requests, on-demand charts, and side-by-side comparison
  - Auditing pipeline grouped by AlgoTrade name
  - Real-time footprints, market logs, signal logs, and error tracing
"""

import os
import sys
import json
import time
import logging
import threading
import asyncio
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from txcore.stream import telemetry_broadcaster
from txcore.algotrade import (
    AlgoTrade,
    AlgoTradeConfig,
    AlgoTradeManager,
    AlgoTradeStatus,
)
from txcore.providers.base import BaseDataProvider
from txcore.providers.tradingview import TradingViewProvider
from txcore.providers.indian_provider import IndianMarketDataProvider
from txcore.providers.nse_provider import NSEClient
from txcore.providers.session_manager import MarketSessionManager, create_indian_session_manager
from txcore.analysis.volatility import analyze_vix
from txcore.analysis.indicators import analyze_trend
from txcore.analysis.period import filter_candles_by_date
from txcore.visualization.chart_builder import create_interactive_chart, scan_df_for_patterns
from txcore.strategies.pdf_price_action import PDFPriceActionStrategy
from txcore.strategies.evaluator import StrategyEvaluator
from config.settings import TELEGRAM_BOT_TOKEN, CHAT_IDS, INDIAN_STOCKS, INDIAN_INDEXES

logger = logging.getLogger("txcore.service")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# In-Memory Stream Buffer for Real-Time UI Log Display
system_log_buffer: List[Dict[str, Any]] = [
    {
        "source": "system",
        "text": "TxBot Core Platform initialized. Universal Market-Agnostic Engine active.",
        "is_error": False,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
]

class InMemoryLogHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            entry = {
                "source": "engine",
                "text": msg,
                "is_error": record.levelno >= logging.ERROR,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            system_log_buffer.append(entry)
            telemetry_broadcaster.broadcast_sync("log_event", entry)
            if len(system_log_buffer) > 1000:
                del system_log_buffer[:-800]
        except Exception:
            pass

_mem_handler = InMemoryLogHandler()
_mem_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
logging.getLogger("txcore").addHandler(_mem_handler)

WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHARTS_DIR = os.path.join(WORKSPACE_DIR, "exports", "charts")
EXPORTS_DIR = os.path.join(WORKSPACE_DIR, "exports")
os.makedirs(CHARTS_DIR, exist_ok=True)
os.makedirs(EXPORTS_DIR, exist_ok=True)

# Global AlgoTrade Manager Instance
manager = AlgoTradeManager()
nse_client = NSEClient()
session_mgr = create_indian_session_manager()
saved_market_requests: List[Dict[str, Any]] = []


# =============================================================================
# SEED DEFAULT ALGOTRADE STRATEGIES IF NONE REGISTERED
# =============================================================================

def seed_default_algos():
    """Seeds rich default AlgoTrades for instant testing by non-technical users."""
    if manager._algos:
        return

    # 1. Ishaq Strategy 1 on Bluechips
    cfg1 = AlgoTradeConfig(
        algo_name="Ishaq Strategy 1",
        market="INDIAN_EQUITY",
        timeframe="5m",
        symbols=["RELIANCE", "TCS", "HDFCBANK"],
        indices=["NIFTY 50", "NIFTY BANK"],
        creator="Ishaq",
        start_time="09:15:00",
        stop_time="15:30:00",
        description="Pure price action setup with rolling Support/Resistance retracement confirmation on 5m candles.",
        chart_enabled=True,
        audit_enabled=True,
        risk_reward_ratio=1.5,
    )
    # 2. Nifty Scalper on Benchmark Index
    cfg2 = AlgoTradeConfig(
        algo_name="Nifty Scalper",
        market="INDIAN_EQUITY",
        timeframe="5m",
        symbols=["NIFTY", "BANKNIFTY"],
        indices=["NIFTY 50"],
        creator="Rajat",
        start_time="09:15:00",
        stop_time="15:15:00",
        description="High-momentum index scalping looking for Engulfing and Piercing Line patterns near major psychological levels.",
        chart_enabled=True,
        audit_enabled=True,
        risk_reward_ratio=2.0,
    )
    # 3. Forex Price Action
    cfg3 = AlgoTradeConfig(
        algo_name="Forex Price Action",
        market="FOREX",
        timeframe="15m",
        symbols=["EUR/USD", "GBP/USD", "USD/JPY"],
        creator="System",
        description="Multi-pair Forex price action scanner with Dark Cloud Cover and Engulfing pattern identification.",
        chart_enabled=True,
        audit_enabled=True,
        risk_reward_ratio=1.5,
    )

    manager.register_algo(cfg1)
    manager.register_algo(cfg2)
    manager.register_algo(cfg3)
    logger.info("Seeded 3 default AlgoTrade strategies into manager.")


# =============================================================================
# BACKGROUND SCHEDULER FOR PROCESS START/STOP TIMES
# =============================================================================

def _scheduler_worker():
    """Checks custom start/stop times for each AlgoTrade based on process ID."""
    while True:
        try:
            now_ist = session_mgr.get_current_time()
            now_str = now_ist.strftime("%H:%M:%S")

            for algo_id, algo in list(manager._algos.items()):
                if getattr(algo.config, "is_deleted", False):
                    continue

                s_time = getattr(algo.config, "start_time", None)
                e_time = getattr(algo.config, "stop_time", None)

                # Check Auto-Start
                if s_time and algo.status in (AlgoTradeStatus.IDLE, AlgoTradeStatus.PAUSED):
                    # Start within 1 minute window
                    if s_time[:5] == now_str[:5]:
                        logger.info(f"⏰ Auto-Starting AlgoTrade '{algo.algo_name}' (ID: {algo.algo_id}) at {now_str}")
                        algo.status = AlgoTradeStatus.RUNNING
                        algo.run_cycle()

                # Check Auto-Stop
                if e_time and algo.status == AlgoTradeStatus.RUNNING:
                    if e_time[:5] == now_str[:5]:
                        logger.info(f"⏰ Auto-Stopping AlgoTrade '{algo.algo_name}' (ID: {algo.algo_id}) at {now_str}")
                        algo.status = AlgoTradeStatus.STOPPED

        except Exception as e:
            logger.error(f"Scheduler error: {e}")

        time.sleep(30.0)


# =============================================================================
# FASTAPI APP CREATION & CONFIGURATION
# =============================================================================

app = FastAPI(
    title="TxBot Universal AlgoTrade API",
    description="Backend service for creating, managing, auditing, evaluating, and visualizing AlgoTrade strategies.",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount exports/charts directory so frontend can embed and view interactive charts directly
app.mount("/charts", StaticFiles(directory=CHARTS_DIR), name="charts")
app.mount("/exports", StaticFiles(directory=EXPORTS_DIR), name="exports")


# =============================================================================
# PYDANTIC REQUEST SCHEMAS
# =============================================================================

class CreateAlgoRequest(BaseModel):
    algo_name: str
    market: str = "INDIAN_EQUITY"
    timeframe: str = "5m"
    symbols: List[str] = Field(default_factory=lambda: ["RELIANCE", "TCS"])
    indices: List[str] = Field(default_factory=lambda: ["NIFTY 50"])
    patterns: List[str] = Field(default_factory=lambda: ["bullish_engulfing", "bearish_engulfing", "piercing_line", "dark_cloud_cover"])
    indicators: List[str] = Field(default_factory=lambda: ["EMA_20", "EMA_50", "RSI"])
    extra_data: List[str] = Field(default_factory=lambda: ["vix", "volume", "index_movement"])
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    start_time: Optional[str] = None
    stop_time: Optional[str] = None
    chart_enabled: bool = True
    chart_engine: str = "tradingview"
    audit_enabled: bool = True
    risk_reward_ratio: float = 1.5
    enable_mtf: bool = False
    higher_timeframe: str = "15m"
    strict_mtf: bool = False
    use_atr_risk: bool = True
    atr_period: int = 14
    atr_multiplier: float = 1.5
    max_workers: int = 8
    lookback_bars: int = 100
    creator: str = "Admin"
    description: str = ""
    broker_name: str = "PAPER"
    discord_webhook_url: Optional[str] = None
    webhook_url: Optional[str] = None


class RiskConfigRequest(BaseModel):
    max_daily_loss_pct: Optional[float] = None
    max_open_positions: Optional[int] = None
    consecutive_loss_limit: Optional[int] = None
    cooldown_minutes: Optional[int] = None
    starting_daily_equity: Optional[float] = None


class EmergencySquareOffRequest(BaseModel):
    reason: Optional[str] = "Operator Panic Action via UI"


class SelectBrokerRequest(BaseModel):
    broker_name: str


class BrokerOrderRequest(BaseModel):
    symbol: str
    side: str = "BUY"
    quantity: int = 1
    price: float = 0.0
    stop_loss: Optional[float] = None
    target: Optional[float] = None
    exchange: str = "NSE"
    tag: str = "MANUAL"


class MarketDataFetchRequest(BaseModel):
    symbol: str
    market: str = "INDIAN_EQUITY"
    timeframe: str = "5m"
    lookback_bars: int = 50
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class CompareRequest(BaseModel):
    symbol_a: str
    timeframe_a: str = "5m"
    symbol_b: str
    timeframe_b: str = "5m"
    market: str = "INDIAN_EQUITY"
    lookback_bars: int = 50


# =============================================================================
# API ROUTES
# =============================================================================

@app.on_event("startup")
async def on_startup():
    try:
        loop = asyncio.get_running_loop()
        telemetry_broadcaster.set_event_loop(loop)
    except Exception:
        pass

    try:
        from txcore.database import connect_db, seed_market_symbols_catalog, seed_default_user, db
        from txcore.persistence import load_algos_from_db
        await connect_db()
        await seed_default_user()
        count = await db.marketsymbol.count()
        if count == 0:
            await seed_market_symbols_catalog()
        logger.info(f"Database connected via Prisma ORM. Total symbols in catalog: {count}")
        loaded = await load_algos_from_db(manager)
        if loaded == 0 and len(manager._algos) == 0:
            seed_default_algos()
    except Exception as e:
        logger.warning(f"Database connection warning on startup: {e}")
        if len(manager._algos) == 0:
            seed_default_algos()

    t = threading.Thread(target=_scheduler_worker, daemon=True)
    t.start()
    logger.info(f"TxBot Backend Service started on FastAPI. Active AlgoTrades: {len(manager._algos)}")


@app.on_event("shutdown")
async def on_shutdown():
    try:
        from txcore.database import disconnect_db
        await disconnect_db()
    except Exception as e:
        logger.warning(f"Error disconnecting database on shutdown: {e}")


# -----------------------------------------------------------------------------
# MARKET CATALOG & GROUP SELECTION ROUTES (PRISMA ORM)
# -----------------------------------------------------------------------------

@app.get("/api/catalog/groups")
async def get_catalog_groups():
    """
    Returns all Market Groups / Benchmark Index Families (e.g. NSE, BSE, DOW_JONES,
    NASDAQ, SP500, FOREX, CRYPTO, MCX) with their member symbol counts.
    """
    try:
        from txcore.database import db
        if db.is_connected():
            groups = await db.marketgroup.find_many(
                include={"symbols": True},
                order={"name": "asc"},
            )
            if groups:
                return [
                    {
                        "groupId": g.groupId,
                        "name": g.name,
                        "market": g.market,
                        "description": g.description,
                        "symbolCount": len(g.symbols) if g.symbols else 0,
                    }
                    for g in groups
                ]
    except Exception as e:
        logger.warning(f"Database query for groups failed, using fallback: {e}")

    from txcore.database import SEEDED_MARKET_GROUPS, SEEDED_MARKET_SYMBOLS
    counts: Dict[str, int] = {}
    for s in SEEDED_MARKET_SYMBOLS:
        gid = s.get("groupId") or ""
        counts[gid] = counts.get(gid, 0) + 1
    return [
        {
            "groupId": g["groupId"],
            "name": g["name"],
            "market": g["market"],
            "description": g.get("description"),
            "symbolCount": counts.get(g["groupId"], 0),
        }
        for g in SEEDED_MARKET_GROUPS
    ]


@app.get("/api/catalog/symbols")
async def get_catalog_symbols(
    group: Optional[str] = Query(None, description="Market group ID, e.g. NSE, BSE, DOW_JONES, FOREX, CRYPTO, MCX"),
    market: Optional[str] = Query(None, description="Market category, e.g. INDIAN_EQUITY, US_EQUITY, FOREX"),
    asset_type: Optional[str] = Query(None, description="Asset type: STOCK, INDEX, CURRENCY, CRYPTO, COMMODITY"),
    search: Optional[str] = Query(None, description="Fuzzy search across symbol, shortName, and fullName"),
    limit: int = Query(100, ge=1, le=500),
):
    """
    Returns seeded stocks, indexes, currencies, and commodities filtered by group,
    market, asset_type, or fuzzy search query for dropdowns.
    """
    try:
        from txcore.database import db
        if db.is_connected():
            where: Dict[str, Any] = {"isActive": True}
            if group:
                where["groupId"] = group.upper().strip()
            if market:
                where["market"] = market.upper().strip()
            if asset_type:
                where["assetType"] = asset_type.upper().strip()

            if search and search.strip():
                q = search.strip()
                where["OR"] = [
                    {"symbol": {"contains": q, "mode": "insensitive"}},
                    {"shortName": {"contains": q, "mode": "insensitive"}},
                    {"fullName": {"contains": q, "mode": "insensitive"}},
                ]

            symbols = await db.marketsymbol.find_many(
                where=where,
                take=limit,
                order={"symbol": "asc"},
            )
            if symbols:
                return [
                    {
                        "symbol": s.symbol,
                        "shortName": s.shortName,
                        "fullName": s.fullName,
                        "market": s.market,
                        "exchange": s.exchange,
                        "assetType": s.assetType,
                        "sector": s.sector,
                        "indexGroup": s.indexGroup,
                        "groupId": s.groupId,
                        "lotSize": s.lotSize,
                        "tickSize": s.tickSize,
                        "tvSymbol": s.tvSymbol,
                    }
                    for s in symbols
                ]
    except Exception as e:
        logger.warning(f"Database query for symbols failed, using fallback: {e}")

    from txcore.database import SEEDED_MARKET_SYMBOLS
    res = []
    q = (search or "").strip().lower()
    g_filter = (group or "").strip().upper()
    m_filter = (market or "").strip().upper()
    a_filter = (asset_type or "").strip().upper()

    for s in SEEDED_MARKET_SYMBOLS:
        if g_filter and s.get("groupId", "").upper() != g_filter:
            continue
        if m_filter and s.get("market", "").upper() != m_filter:
            continue
        if a_filter and s.get("assetType", "").upper() != a_filter:
            continue
        if q:
            match = (
                q in s.get("symbol", "").lower()
                or q in s.get("shortName", "").lower()
                or q in s.get("fullName", "").lower()
            )
            if not match:
                continue
        res.append(s)
        if len(res) >= limit:
            break
    return res


@app.get("/api/catalog/markets")
def get_catalog_markets():
    """Returns supported market categories and their associated exchanges and default groups."""
    return [
        {
            "id": "INDIAN_EQUITY",
            "name": "Indian Equities & F&O",
            "defaultGroup": "NSE",
            "groups": ["NSE", "BSE"],
            "assetTypes": ["STOCK", "INDEX"],
            "currency": "INR",
        },
        {
            "id": "US_EQUITY",
            "name": "US Equities & Indexes",
            "defaultGroup": "DOW_JONES",
            "groups": ["DOW_JONES", "NASDAQ", "SP500"],
            "assetTypes": ["STOCK", "INDEX"],
            "currency": "USD",
        },
        {
            "id": "FOREX",
            "name": "Forex Currencies",
            "defaultGroup": "FOREX",
            "groups": ["FOREX"],
            "assetTypes": ["CURRENCY"],
            "currency": "USD",
        },
        {
            "id": "CRYPTO",
            "name": "Cryptocurrencies",
            "defaultGroup": "CRYPTO",
            "groups": ["CRYPTO"],
            "assetTypes": ["CRYPTO"],
            "currency": "USDT",
        },
        {
            "id": "COMMODITY",
            "name": "Commodities (MCX)",
            "defaultGroup": "MCX",
            "groups": ["MCX"],
            "assetTypes": ["COMMODITY"],
            "currency": "INR",
        },
    ]


@app.get("/api/status")
def get_system_status():
    """Real-time system health, market session state, India VIX, and breadth."""
    try:
        session = session_mgr.get_session_info()
        vix_quote = nse_client.get_vix_quote()
        vix_val = vix_quote.last_price if vix_quote and vix_quote.last_price > 0 else 14.5
        vix = analyze_vix(vix_val, change=vix_quote.change if vix_quote else 0.0, percent_change=vix_quote.percent_change if vix_quote else 0.0)
        breadth = nse_client.get_market_breadth("NIFTY 50")

        return {
            "status": "ONLINE",
            "server_time": datetime.now(timezone.utc).isoformat(),
            "session": {
                "market_state": session.status.value,
                "current_time": session.current_time_ist,
                "is_trading": session.is_trading_active,
                "minutes_to_open": session.time_to_open_minutes,
                "minutes_to_close": session.time_to_close_minutes,
                "summary": session.to_alert_line(),
            },
            "vix": {
                "value": vix.current_vix,
                "change": vix.change,
                "percent_change": vix.percent_change,
                "regime": vix.regime.value,
                "summary": vix.to_summary_string(),
            },
            "breadth": {
                "advances": breadth.advances,
                "declines": breadth.declines,
                "unchanged": breadth.unchanged,
                "adr": breadth.advance_decline_ratio,
                "sentiment": breadth.sentiment,
            },
            "algos_count": len(manager.list_algos(include_deleted=False)),
            "active_algos": sum(1 for a in manager._algos.values() if a.status == AlgoTradeStatus.RUNNING),
        }
    except Exception as e:
        logger.error(f"Status error: {e}")
        return {"status": "ERROR", "error": str(e)}


# -----------------------------------------------------------------------------
# ALGOTRADE MODULE ROUTES
# -----------------------------------------------------------------------------

@app.get("/api/algos")
def list_algos(status: Optional[str] = None, creator: Optional[str] = None, include_deleted: bool = False):
    """Retrieves all registered AlgoTrade strategies with live state and PnL."""
    algos = manager.list_algos(include_deleted=include_deleted)
    if status:
        algos = [a for a in algos if a.get("status", "").upper() == status.upper()]
    if creator:
        algos = [a for a in algos if a.get("creator", "").lower() == creator.lower()]
    return algos


@app.post("/api/algos")
async def create_algo(req: CreateAlgoRequest):
    """Creates and registers a new AlgoTrade process, persisting to Prisma ORM."""
    try:
        config = AlgoTradeConfig(
            algo_name=req.algo_name.strip(),
            market=req.market.upper(),
            timeframe=req.timeframe,
            symbols=[s.strip().toUpperCase() if hasattr(s, "toUpperCase") else str(s).strip().upper() for s in req.symbols if str(s).strip()],
            indices=req.indices,
            patterns=req.patterns,
            indicators=req.indicators,
            extra_data=req.extra_data,
            start_date=req.start_date,
            end_date=req.end_date,
            start_time=req.start_time,
            stop_time=req.stop_time,
            chart_enabled=req.chart_enabled,
            chart_engine=req.chart_engine,
            audit_enabled=req.audit_enabled,
            risk_reward_ratio=req.risk_reward_ratio,
            enable_mtf=req.enable_mtf,
            higher_timeframe=req.higher_timeframe,
            strict_mtf=req.strict_mtf,
            use_atr_risk=req.use_atr_risk,
            atr_period=req.atr_period,
            atr_multiplier=req.atr_multiplier,
            max_workers=req.max_workers,
            lookback_bars=req.lookback_bars,
            creator=req.creator,
            description=req.description,
            broker_name=req.broker_name,
            discord_webhook_url=req.discord_webhook_url,
            webhook_url=req.webhook_url,
        )

        algo = manager.register_algo(config)

        # Sync to Prisma PostgreSQL if connected
        try:
            from txcore.database import db
            if db.is_connected():
                admin_user = await db.user.find_first()
                if admin_user:
                    await db.algotrade.upsert(
                        where={"algoId": algo.algo_id},
                        data={
                            "create": {
                                "algoId": algo.algo_id,
                                "userId": admin_user.id,
                                "algoName": algo.algo_name,
                                "market": req.market.upper(),
                                "timeframe": req.timeframe,
                                "symbols": json.dumps(config.symbols),
                                "indices": json.dumps(config.indices),
                                "indicators": json.dumps(config.indicators),
                                "patterns": json.dumps(config.patterns),
                                "riskRewardRatio": req.risk_reward_ratio,
                                "status": "IDLE",
                                "startTime": req.start_time,
                                "stopTime": req.stop_time,
                                "chartEnabled": req.chart_enabled,
                                "auditEnabled": req.audit_enabled,
                            },
                            "update": {
                                "algoName": algo.algo_name,
                                "market": req.market.upper(),
                                "timeframe": req.timeframe,
                                "symbols": json.dumps(config.symbols),
                                "indices": json.dumps(config.indices),
                                "riskRewardRatio": req.risk_reward_ratio,
                            },
                        },
                    )
        except Exception as db_err:
            logger.warning(f"Could not persist AlgoTrade to database: {db_err}")

        return {
            "success": True,
            "message": f"AlgoTrade '{algo.algo_name}' created successfully.",
            "algo_name": algo.algo_name,
            "algo_id": algo.algo_id,
            "algo": algo.get_metrics(),
        }
    except Exception as e:
        logger.error(f"Error creating algo: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/algos/{algo_id}")
def get_algo_detail(algo_id: str):
    """Gets details, recent signals, and metrics for an AlgoTrade."""
    algo = manager.get_algo(algo_id)
    if not algo:
        raise HTTPException(status_code=404, detail=f"AlgoTrade '{algo_id}' not found.")
    metrics = algo.get_metrics()
    metrics["signals"] = algo.signals_history
    metrics["pnl_trades"] = algo.pnl_history
    return metrics


@app.post("/api/algos/{algo_id}/start")
def start_algo(algo_id: str):
    """Executes/Starts an AlgoTrade and performs one cycle immediately."""
    algo = manager.get_algo(algo_id)
    if not algo:
        raise HTTPException(status_code=404, detail=f"AlgoTrade '{algo_id}' not found.")
    cycle_results = algo.run_cycle()
    return {
        "success": True,
        "algo_id": algo.algo_id,
        "algo_name": algo.algo_name,
        "status": algo.status.value,
        "results": cycle_results,
        "metrics": algo.get_metrics(),
    }


@app.post("/api/algos/{algo_id}/stop")
def stop_algo(algo_id: str):
    """Stops an AlgoTrade."""
    ok = manager.stop_algo(algo_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"AlgoTrade '{algo_id}' not found.")
    return {"success": True, "message": "AlgoTrade stopped."}


@app.post("/api/algos/{algo_id}/pause")
def pause_algo(algo_id: str):
    """Pauses an AlgoTrade."""
    ok = manager.pause_algo(algo_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"AlgoTrade '{algo_id}' not found.")
    return {"success": True, "message": "AlgoTrade paused."}


@app.post("/api/algos/{algo_id}/copy")
def copy_algo(algo_id: str):
    """Duplicates an existing AlgoTrade strategy with a new ID."""
    copied = manager.copy_algo(algo_id)
    if not copied:
        raise HTTPException(status_code=404, detail=f"AlgoTrade '{algo_id}' not found.")
    return {
        "success": True,
        "message": f"Cloned into '{copied.algo_name}'.",
        "algo": copied.get_metrics(),
    }


@app.delete("/api/algos/{algo_id}")
def delete_algo(algo_id: str, hard: bool = False):
    """Deletes an AlgoTrade (soft-delete by default)."""
    ok = manager.delete_algo(algo_id, hard=hard)
    if not ok:
        raise HTTPException(status_code=404, detail=f"AlgoTrade '{algo_id}' not found.")
    return {"success": True, "message": "AlgoTrade deleted."}


@app.post("/api/algos/{algo_id}/evaluate")
def evaluate_algo(algo_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None):
    """Runs a historical walk-forward backtest / evaluation across configured symbols."""
    algo = manager.get_algo(algo_id)
    if not algo:
        raise HTTPException(status_code=404, detail=f"AlgoTrade '{algo_id}' not found.")

    s_date = start_date or algo.config.start_date
    e_date = end_date or algo.config.end_date

    reports = []
    for symbol in (algo.config.symbols or ["RELIANCE"]):
        rep = algo.evaluate_historical(symbol, start_date=s_date, end_date=e_date)
        reports.append({
            "symbol": rep.symbol,
            "strategy": rep.strategy_name,
            "period": f"{rep.period_start} -> {rep.period_end}",
            "total_bars": rep.total_bars,
            "total_signals": rep.total_signals,
            "winning_trades": rep.winning_trades,
            "losing_trades": rep.losing_trades,
            "win_rate_pct": rep.win_rate_pct,
            "total_pnl_pct": rep.total_pnl_pct,
            "total_pnl_points": rep.total_pnl_points,
            "profit_factor": rep.profit_factor,
            "trades": [
                {
                    "trade_id": t.trade_id,
                    "direction": t.direction,
                    "pattern": t.pattern,
                    "entry_time": t.entry_time,
                    "entry_price": t.entry_price,
                    "exit_time": t.exit_time,
                    "exit_price": t.exit_price,
                    "outcome": t.outcome,
                    "pnl_pct": t.pnl_pct,
                    "pnl_points": t.pnl_points,
                }
                for t in rep.trades
            ],
            "summary_text": rep.to_summary_string(),
        })

    return {
        "algo_id": algo.algo_id,
        "algo_name": algo.algo_name,
        "evaluation_period": f"{s_date or 'Earliest'} -> {e_date or 'Latest'}",
        "reports": reports,
    }


@app.post("/api/algos/run-all")
def run_all_algos():
    """Executes one scan cycle across all active AlgoTrades concurrently."""
    results = manager.run_all_cycles()
    return {"success": True, "results": results}


# -----------------------------------------------------------------------------
# SIGNALS & PNL ROUTES
# -----------------------------------------------------------------------------

@app.get("/api/signals")
def list_signals(algo_id: Optional[str] = None, symbol: Optional[str] = None, direction: Optional[str] = None):
    """Retrieves generated signals with optional filters."""
    signals = manager.get_all_signals(algo_id=algo_id)
    if symbol:
        signals = [s for s in signals if s.get("symbol", "").upper() == symbol.upper()]
    if direction:
        signals = [s for s in signals if s.get("direction", "").upper() == direction.upper()]

    # Convert absolute chart paths to static URLs
    for s in signals:
        if s.get("chart_path"):
            s["chart_url"] = f"/charts/{os.path.basename(s['chart_path'])}"
        if s.get("audit_chart_path"):
            s["audit_chart_url"] = f"/charts/{os.path.basename(s['audit_chart_path'])}"

    return signals


@app.get("/api/signals/{signal_id}")
def get_signal_detail(signal_id: str):
    """Gets detailed view of a signal including execution chart and +30 candles audit chart."""
    sig = manager.get_signal_by_id(signal_id)
    if not sig:
        raise HTTPException(status_code=404, detail=f"Signal '{signal_id}' not found.")

    res = dict(sig)
    if res.get("chart_path"):
        res["chart_url"] = f"/charts/{os.path.basename(res['chart_path'])}"
    if res.get("audit_chart_path"):
        res["audit_chart_url"] = f"/charts/{os.path.basename(res['audit_chart_path'])}"

    return res


@app.post("/api/signals/{signal_id}/resend")
def resend_signal(signal_id: str):
    """Re-dispatches an alert to configured endpoints (e.g. Telegram)."""
    sig = manager.get_signal_by_id(signal_id)
    if not sig:
        raise HTTPException(status_code=404, detail=f"Signal '{signal_id}' not found.")

    dispatched = False
    if TELEGRAM_BOT_TOKEN and CHAT_IDS:
        from txcore.execution.telegram import TelegramNotifier
        notifier = TelegramNotifier(bot_token=TELEGRAM_BOT_TOKEN, chat_ids=CHAT_IDS)
        alert_msg = (
            f"🔄 [RESENT SIGNAL] {sig.get('direction')} on {sig.get('symbol')}\n"
            f"Pattern: {sig.get('pattern')}\n"
            f"Price: {sig.get('price')}\n"
            f"SL: {sig.get('stop_loss')} | Target: {sig.get('target')}\n"
            f"Algo: {sig.get('algo_name')}"
        )
        sent = notifier.send(alert_msg, chart_path=sig.get("chart_path"))
        if sent:
            dispatched = True

    return {
        "success": True,
        "signal_id": signal_id,
        "dispatched": dispatched,
        "message": "Signal resent to configured endpoints." if dispatched else "Signal recorded (no external endpoint configured).",
    }


@app.get("/api/pnl")
def get_pnl_summary(algo_id: Optional[str] = None):
    """Retrieves consolidated and per-trade PnL analytics."""
    return manager.get_all_pnl(algo_id=algo_id)


# -----------------------------------------------------------------------------
# MARKET DATA MODULE ROUTES
# -----------------------------------------------------------------------------

@app.post("/api/market/fetch")
def fetch_market_data(req: MarketDataFetchRequest):
    """Uses DataProvider layer to fetch candles and save request footprint."""
    sym = req.symbol.strip().upper()
    provider = IndianMarketDataProvider() if req.market.upper() in ("INDIAN_EQUITY", "INDIAN", "NSE") else TradingViewProvider()

    s_date = req.start_date.strip() if req.start_date and req.start_date.strip() else None
    e_date = req.end_date.strip() if req.end_date and req.end_date.strip() else None

    df = provider.get_cached_candles(
        sym,
        timeframe=req.timeframe,
        lookback_bars=req.lookback_bars,
        start_date=s_date,
        end_date=e_date,
    )

    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"Could not fetch data for symbol '{sym}'.")

    # Trend and Indicator Summary
    trend = analyze_trend(df, symbol=sym, timeframe=req.timeframe, lookback_bars=req.lookback_bars)

    candles = []
    for _, row in df.tail(100).iterrows():
        candles.append({
            "time": str(row["time"]),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": float(row.get("volume", 0.0)),
        })

    # Save to stored requests list
    rec = {
        "id": f"REQ-{len(saved_market_requests) + 1:03d}",
        "symbol": sym,
        "market": req.market,
        "timeframe": req.timeframe,
        "bars": len(df),
        "start_date": req.start_date,
        "end_date": req.end_date,
        "latest_close": float(df.iloc[-1]["close"]),
        "trend": trend.get("trend", "N/A"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    saved_market_requests.insert(0, rec)

    return {
        "symbol": sym,
        "market": req.market,
        "timeframe": req.timeframe,
        "total_bars": len(df),
        "trend": trend,
        "candles": candles,
        "request_record": rec,
    }


@app.get("/api/market/history")
def get_market_requests_history():
    """Lists saved/stored market data queries."""
    return saved_market_requests[:30]


@app.post("/api/market/chart")
def generate_chart_on_demand(req: MarketDataFetchRequest):
    """Generates an interactive HTML chart and returns its URL."""
    sym = req.symbol.strip().upper()
    provider = IndianMarketDataProvider() if req.market.upper() in ("INDIAN_EQUITY", "INDIAN", "NSE") else TradingViewProvider()

    s_date = req.start_date.strip() if req.start_date and req.start_date.strip() else None
    e_date = req.end_date.strip() if req.end_date and req.end_date.strip() else None

    df = provider.get_cached_candles(
        sym,
        timeframe=req.timeframe,
        lookback_bars=req.lookback_bars,
        start_date=s_date,
        end_date=e_date,
    )
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail="Candle data unavailable.")

    chart_path = create_interactive_chart(
        df,
        symbol=sym,
        lookback_bars=req.lookback_bars,
        auto_open=False,
    )
    chart_url = f"/charts/{os.path.basename(chart_path)}" if chart_path else None
    return {
        "symbol": sym,
        "timeframe": req.timeframe,
        "chart_path": chart_path,
        "chart_url": chart_url,
    }


@app.post("/api/market/compare")
def compare_charts_side_by_side(req: CompareRequest):
    """Generates dual datasets and chart URLs for side-by-side comparison."""
    provider = IndianMarketDataProvider() if req.market.upper() in ("INDIAN_EQUITY", "INDIAN", "NSE") else TradingViewProvider()

    df_a = provider.get_cached_candles(req.symbol_a, timeframe=req.timeframe_a, lookback_bars=req.lookback_bars)
    df_b = provider.get_cached_candles(req.symbol_b, timeframe=req.timeframe_b, lookback_bars=req.lookback_bars)

    if df_a is None or df_b is None:
        raise HTTPException(status_code=400, detail="Could not extract data for comparison.")

    chart_a = create_interactive_chart(df_a, symbol=req.symbol_a, lookback_bars=req.lookback_bars, auto_open=False)
    chart_b = create_interactive_chart(df_b, symbol=req.symbol_b, lookback_bars=req.lookback_bars, auto_open=False)

    return {
        "side_a": {
            "symbol": req.symbol_a,
            "timeframe": req.timeframe_a,
            "latest_close": float(df_a.iloc[-1]["close"]),
            "chart_url": f"/charts/{os.path.basename(chart_a)}" if chart_a else None,
        },
        "side_b": {
            "symbol": req.symbol_b,
            "timeframe": req.timeframe_b,
            "latest_close": float(df_b.iloc[-1]["close"]),
            "chart_url": f"/charts/{os.path.basename(chart_b)}" if chart_b else None,
        },
    }


# -----------------------------------------------------------------------------
# AUDITING MODULE ROUTES
# -----------------------------------------------------------------------------

@app.get("/api/audits")
def get_audits_list():
    """Returns audit records grouped by AlgoTrade with deep compliance & filter metrics."""
    audits_by_algo = []
    for algo in manager._algos.values():
        if getattr(algo.config, "is_deleted", False):
            continue
        sigs = algo.signals_history
        aud_summary = algo.auditor.get_summary() if hasattr(algo, "auditor") else {}
        audits_by_algo.append({
            "algo_name": algo.algo_name,
            "algo_id": algo.algo_id,
            "market": algo.config.market,
            "timeframe": algo.config.timeframe,
            "total_signals": len(sigs),
            "approved_signals": sum(1 for s in sigs if s.get("status") in ("APPROVED", "CONFIRMED_SIGNAL", None)),
            "win_rate_pct": algo.get_metrics()["win_rate_pct"],
            "total_pnl_pct": algo.get_metrics()["total_pnl_pct"],
            "last_audit_time": algo.last_scan_at.isoformat() if algo.last_scan_at else algo.created_at.isoformat(),
            "signals_blocked_by_mtf": aud_summary.get("signals_blocked_by_mtf", 0),
            "signals_blocked_by_news": aud_summary.get("signals_blocked_by_news", 0),
            "signals_blocked_by_risk": aud_summary.get("signals_blocked_by_risk", 0),
            "avg_latency_ms": aud_summary.get("avg_latency_ms", 0.0),
            "total_audit_events": aud_summary.get("total_audit_events", 0),
        })
    return audits_by_algo


@app.get("/api/audits/{algo_name}")
def get_algo_audit_detail(algo_name: str):
    """Detailed audit view for a specific AlgoTrade by name or collision-resistant ID."""
    algo = manager.get_algo_by_name(algo_name) or manager.get_algo(algo_name)
    if not algo:
        raise HTTPException(status_code=404, detail=f"AlgoTrade '{algo_name}' not found.")

    sigs = list(algo.signals_history)
    for s in sigs:
        if s.get("audit_chart_path"):
            s["audit_chart_url"] = f"/charts/{os.path.basename(s['audit_chart_path'])}"
        if s.get("chart_path"):
            s["chart_url"] = f"/charts/{os.path.basename(s['chart_path'])}"

    auditor_events = algo.auditor.get_events(limit=100) if hasattr(algo, "auditor") else []
    for ev in auditor_events:
        if ev.get("audit_chart_path"):
            ev["audit_chart_url"] = f"/charts/{os.path.basename(ev['audit_chart_path'])}"
        if ev.get("chart_path"):
            ev["chart_url"] = f"/charts/{os.path.basename(ev['chart_path'])}"

    return {
        "algo_name": algo.algo_name,
        "algo_id": algo.algo_id,
        "status": algo.status.value,
        "created_at": algo.created_at.isoformat(),
        "cycle_count": algo.cycle_count,
        "summary": algo.auditor.get_summary() if hasattr(algo, "auditor") else {},
        "signals": sigs,
        "audit_events": auditor_events,
        "pnl_history": algo.pnl_history,
        "error_log": algo.error_log,
    }


@app.get("/api/audits-events")
async def get_persisted_audit_events(
    algo_id: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 100,
):
    """Retrieves deep audit events from PostgreSQL or memory."""
    from txcore.persistence import get_audit_events_from_db
    events = await get_audit_events_from_db(algo_id=algo_id, event_type=event_type, limit=limit)
    if not events:
        if algo_id:
            algo = manager.get_algo(algo_id) or manager.get_algo_by_name(algo_id)
            if algo and hasattr(algo, "auditor"):
                events = algo.auditor.get_events(limit=limit)
        else:
            all_ev = []
            for a in manager._algos.values():
                if hasattr(a, "auditor"):
                    all_ev.extend(a.auditor.get_events(limit=limit))
            events = sorted(all_ev, key=lambda x: x.get("timestamp", 0), reverse=True)[:limit]
    return {"total": len(events), "events": events}


# -----------------------------------------------------------------------------
# LOGGING MODULE ROUTES
# -----------------------------------------------------------------------------

@app.get("/api/logs")
def get_logs(source: str = "all", search: Optional[str] = None, limit: int = 150):
    """Retrieves live application footprints, signal logs, engine logs, market data logs, and structured JSONL logs."""
    from txcore.execution.file_logger import query_structured_logs

    lines = []

    # 1. Include structured JSONL logs
    structured = query_structured_logs(source=source if source != "all" else None, search=search, limit=limit)
    lines.extend(structured)

    # 2. Include engine and runtime system telemetry if requested
    if source in ("all", "engine", "system"):
        for entry in system_log_buffer:
            if not search or search.lower() in entry["text"].lower():
                lines.append(entry)

    # 3. Include file-based persistent footprints
    log_files = {
        "market": os.path.join(WORKSPACE_DIR, "tv_market_data.log"),
        "signals": os.path.join(WORKSPACE_DIR, "signals_history.log"),
        "delivery": os.path.join(WORKSPACE_DIR, "telegram_delivery.log"),
    }

    target_sources = log_files.keys() if source == "all" else [source]
    for src in target_sources:
        if src in ("engine", "system"):
            continue
        path = log_files.get(src)
        if path and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    file_lines = f.readlines()[-limit:]
                    for l in file_lines:
                        clean = l.strip()
                        if clean:
                            if not search or search.lower() in clean.lower():
                                lines.append({
                                    "source": src,
                                    "text": clean,
                                    "is_error": "error" in clean.lower() or "exception" in clean.lower(),
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                })
            except Exception as e:
                lines.append({"source": src, "text": f"Error reading log: {e}", "is_error": True})

    return {"total": len(lines), "logs": lines[-limit:]}


# -----------------------------------------------------------------------------
# REAL-TIME SSE TELEMETRY STREAM & CONCURRENCY ROUTES
# -----------------------------------------------------------------------------

@app.get("/api/stream")
async def stream_telemetry(request: Request):
    """
    High-performance Server-Sent Events (SSE) telemetry stream for real-time frontend updates.
    Streams heartbeats, live scan cycle updates, signal alerts, and concurrency metrics.
    """
    queue = telemetry_broadcaster.subscribe()

    async def event_generator():
        init_data = {
            "status": "connected",
            "server_time": datetime.now(timezone.utc).isoformat(),
            "active_algos": len(manager._algos),
            "concurrency": manager.get_concurrency_overview(),
        }
        yield f"event: connected\ndata: {json.dumps(init_data)}\n\n"

        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=10.0)
                    yield payload
                except asyncio.TimeoutError:
                    # Periodic heartbeat to keep connection alive and stream fresh telemetry
                    hb = {
                        "type": "heartbeat",
                        "server_time": datetime.now(timezone.utc).isoformat(),
                        "concurrency": manager.get_concurrency_overview(),
                    }
                    yield f"event: heartbeat\ndata: {json.dumps(hb)}\n\n"
        except Exception:
            pass
        finally:
            telemetry_broadcaster.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/concurrency")
def get_concurrency_metrics():
    """
    Returns real-time concurrency metrics, active worker threads, and execution latencies
    across all running AlgoTrades.
    """
    return manager.get_concurrency_overview()


# -----------------------------------------------------------------------------
# PAPER TRADING & ORDER EXECUTION ROUTES
# -----------------------------------------------------------------------------

class ModifyPositionRequest(BaseModel):
    stop_loss: Optional[float] = None
    target: Optional[float] = None
    trailing_sl: Optional[float] = None


class ClosePositionRequest(BaseModel):
    exit_price: Optional[float] = None


class ResetAccountRequest(BaseModel):
    initial_capital: Optional[float] = 1_000_000.0


@app.get("/api/paper/portfolio")
def get_paper_portfolio():
    """Returns real-time paper trading portfolio, margins, and performance."""
    from txcore.execution.paper_engine import get_paper_engine
    return get_paper_engine().get_portfolio_summary()


@app.get("/api/paper/positions")
def get_paper_positions():
    """Returns open paper positions with live mark-to-market valuations."""
    from txcore.execution.paper_engine import get_paper_engine
    return get_paper_engine().get_open_positions()


@app.get("/api/paper/trades")
def get_paper_trades(limit: int = Query(100, ge=1, le=500)):
    """Returns historical closed trade executions."""
    from txcore.execution.paper_engine import get_paper_engine
    return get_paper_engine().get_closed_trades(limit=limit)


@app.post("/api/paper/positions/{position_id}/close")
def close_paper_position(position_id: str, req: Optional[ClosePositionRequest] = None):
    """Manually squares off an open paper trading position."""
    from txcore.execution.paper_engine import get_paper_engine
    exit_price = req.exit_price if req else None
    trade = get_paper_engine().close_position_manually(position_id, exit_price=exit_price)
    if not trade:
        raise HTTPException(status_code=404, detail=f"Open position '{position_id}' not found.")
    return {"status": "SUCCESS", "message": f"Position {position_id} squared off.", "trade": trade}


@app.post("/api/paper/positions/{position_id}/modify")
def modify_paper_position(position_id: str, req: ModifyPositionRequest):
    """Updates stop loss, target, or trailing stop on an open position."""
    from txcore.execution.paper_engine import get_paper_engine
    pos = get_paper_engine().modify_position(
        position_id,
        stop_loss=req.stop_loss,
        target=req.target,
        trailing_sl=req.trailing_sl,
    )
    if not pos:
        raise HTTPException(status_code=404, detail=f"Open position '{position_id}' not found.")
    from dataclasses import asdict
    return {"status": "SUCCESS", "position": asdict(pos)}


@app.post("/api/paper/reset")
def reset_paper_account(req: Optional[ResetAccountRequest] = None):
    """Resets paper trading account to pristine starting capital."""
    from txcore.execution.paper_engine import get_paper_engine
    cap = req.initial_capital if req and req.initial_capital else 1_000_000.0
    get_paper_engine().reset_account(initial_capital=cap)
    return {"status": "SUCCESS", "message": f"Paper trading account reset with capital: {cap}"}


# =============================================================================
# RISK MANAGEMENT & CIRCUIT BREAKER ENDPOINTS (PHASE 7)
# =============================================================================

@app.get("/api/risk/status")
def get_risk_status():
    """Returns current real-time circuit breaker status, drawdown, and limits."""
    from txcore.filters.risk_manager import get_risk_manager
    return get_risk_manager().get_risk_status()


@app.post("/api/risk/config")
def update_risk_config(req: RiskConfigRequest):
    """Updates runtime risk parameters (max daily loss, max open positions, etc.)."""
    from txcore.filters.risk_manager import get_risk_manager
    rm = get_risk_manager()
    rm.update_config(
        max_daily_loss_pct=req.max_daily_loss_pct,
        max_open_positions=req.max_open_positions,
        consecutive_loss_limit=req.consecutive_loss_limit,
        cooldown_minutes=req.cooldown_minutes,
        starting_daily_equity=req.starting_daily_equity,
    )
    return {"status": "SUCCESS", "risk_status": rm.get_risk_status()}


@app.post("/api/risk/emergency-square-off")
def trigger_emergency_square_off(req: Optional[EmergencySquareOffRequest] = None):
    """
    Global Emergency Kill Switch:
    - Halts all trading and trips circuit breaker to EMERGENCY_HALT.
    - Squares off all positions across Paper and Live broker adapters.
    - Pauses/stops running AlgoTrade strategies.
    """
    from txcore.filters.risk_manager import get_risk_manager
    reason = req.reason if req and req.reason else "Operator Panic Action via UI"
    result = get_risk_manager().trigger_emergency_square_off(reason=reason)
    return result


@app.post("/api/risk/reset-breaker")
def reset_circuit_breaker():
    """Restores circuit breaker state to NORMAL after manual review."""
    from txcore.filters.risk_manager import get_risk_manager
    return get_risk_manager().reset_circuit_breaker()


# =============================================================================
# BROKER MANAGEMENT & ROUTING ENDPOINTS (PHASE 7)
# =============================================================================

@app.get("/api/brokers")
def list_brokers():
    """Lists available broker adapters, connection statuses, margins, and active broker."""
    from txcore.execution.broker_adapter import get_broker_manager
    bm = get_broker_manager()
    return {
        "active_broker": bm.active_broker_name,
        "brokers": bm.list_brokers(),
    }


@app.post("/api/brokers/select")
def select_active_broker(req: SelectBrokerRequest):
    """Switches the global default execution broker adapter."""
    from txcore.execution.broker_adapter import get_broker_manager
    bm = get_broker_manager()
    success = bm.set_active_broker(req.broker_name)
    if not success:
        raise HTTPException(status_code=400, detail=f"Broker '{req.broker_name}' is not supported.")
    return {"status": "SUCCESS", "active_broker": bm.active_broker_name}


@app.get("/api/brokers/{broker_name}/positions")
def get_broker_positions(broker_name: str):
    """Returns open positions from a specific broker adapter."""
    from txcore.execution.broker_adapter import get_broker_manager
    from dataclasses import asdict
    bm = get_broker_manager()
    adapter = bm.get_adapter(broker_name)
    positions = adapter.get_positions()
    return [asdict(p) for p in positions]


@app.post("/api/brokers/{broker_name}/orders")
def place_broker_order(broker_name: str, req: BrokerOrderRequest):
    """Manually routes an order through the specified broker adapter."""
    from txcore.execution.broker_adapter import get_broker_manager, OrderSide
    from dataclasses import asdict
    bm = get_broker_manager()
    adapter = bm.get_adapter(broker_name)
    side_enum = OrderSide.BUY if req.side.upper() == "BUY" else OrderSide.SELL
    order = adapter.place_order(
        symbol=req.symbol.upper(),
        side=side_enum,
        quantity=req.quantity,
        price=req.price,
        stop_loss=req.stop_loss,
        target=req.target,
        exchange=req.exchange,
        tag=req.tag,
    )
    return {"status": "SUCCESS", "order": asdict(order)}



# Mount compiled React frontend SPA if dist exists
FRONTEND_DIST = os.path.join(WORKSPACE_DIR, "frontend", "dist")
if os.path.exists(FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")

