"""
tests.test_audit_persistence
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Unit and integration tests for Phase 4:
  - Deep Institutional TradeAuditor (snapshots, latency, MTF/news filters)
  - Structured file logger and JSONL querying
  - Prisma database persistence bridge for AlgoTrades, Signals, PnL, and Audits
  - Auditing & Logging REST API endpoints
"""

import os
import time
import asyncio
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from txcore.audit.auditor import TradeAuditor
from txcore.execution.file_logger import (
    log_structured_event,
    query_structured_logs,
    log_signal_to_file,
    log_market_data_to_file,
)
from txcore.persistence import (
    get_or_create_default_user,
    save_algo_to_db,
    load_algos_from_db,
    update_algo_status_in_db,
    save_signal_to_db,
    save_pnl_trade_to_db,
    save_audit_event_to_db,
    get_audit_events_from_db,
    save_structured_log_to_db,
)
from txcore.algotrade import AlgoTradeConfig, AlgoTrade, AlgoTradeManager, AlgoTradeStatus
from txcore.service import app, manager, seed_default_algos


class TestTradeAuditorDeep:
    def test_auditor_records_indicator_and_level_snapshots(self):
        auditor = TradeAuditor(algo_id="AT-TestAudit-001")
        assert auditor.algo_id == "AT-TestAudit-001"

        indicator_snap = {
            "rsi": 62.4,
            "trend_state": "UPTREND",
            "htf_trend": "BULLISH",
            "support_level": 2500.0,
            "resistance_level": 2580.0,
        }
        level_snap = {
            "entry_price": 2520.0,
            "level": 2500.0,
            "stop_loss": 2490.0,
            "target": 2565.0,
            "atr": 15.2,
        }

        auditor.record_signal(
            symbol="RELIANCE",
            direction="CALL",
            pattern="Bullish Engulfing",
            status="APPROVED",
            reason="Confirmed at Key Support",
            indicator_snapshot=indicator_snap,
            level_snapshot=level_snap,
            latency_ms=18,
        )

        assert auditor.total_scans == 1
        assert auditor.signals_generated == 1
        assert len(auditor.history) == 1

        rec = auditor.history[0]
        assert rec["symbol"] == "RELIANCE"
        assert rec["direction"] == "CALL"
        assert rec["status"] == "APPROVED"
        assert rec["indicator_snapshot"]["rsi"] == 62.4
        assert rec["level_snapshot"]["stop_loss"] == 2490.0
        assert rec["latency_ms"] == 18

    def test_auditor_tracks_filter_rejections(self):
        auditor = TradeAuditor(algo_id="AT-FilterTest-002")

        # Record MTF block
        auditor.record_signal(
            symbol="TCS",
            direction="CALL",
            pattern="Piercing Line",
            status="BLOCKED",
            reason="MTF Filter: Higher timeframe is DOWNTREND",
            latency_ms=12,
        )

        # Record News block
        auditor.record_signal(
            symbol="INFY",
            direction="PUT",
            pattern="Bearish Engulfing",
            status="BLOCKED",
            reason="High impact RBI news release",
            latency_ms=8,
        )

        # Record Risk block
        auditor.record_signal(
            symbol="HDFCBANK",
            direction="CALL",
            pattern="Hammer",
            status="BLOCKED",
            reason="Risk/Reward ratio insufficient",
            latency_ms=10,
        )

        summary = auditor.get_summary()
        assert summary["total_scans"] == 3
        assert summary["signals_generated"] == 0
        assert summary["signals_blocked_by_mtf"] == 1
        assert summary["signals_blocked_by_news"] == 1
        assert summary["signals_blocked_by_risk"] == 1
        assert summary["approval_rate_pct"] == 0.0
        assert summary["avg_latency_ms"] == 10.0

    def test_auditor_get_events_filtering(self):
        auditor = TradeAuditor()
        auditor.record_signal("AAPL", "CALL", "Breakout", "APPROVED")
        auditor.record_signal("MSFT", "PUT", "Breakout", "BLOCKED", reason="MTF Filter")

        approved = auditor.get_events(status="APPROVED")
        blocked = auditor.get_events(status="BLOCKED")

        assert len(approved) == 1
        assert approved[0]["symbol"] == "AAPL"
        assert len(blocked) == 1
        assert blocked[0]["symbol"] == "MSFT"


class TestStructuredLogger:
    def test_structured_log_event_recording(self):
        entry = log_structured_event(
            level="INFO",
            source="pipeline",
            message="Test structured event recording",
            metadata={"cycle": 1, "symbols": 5},
        )
        assert entry["level"] == "INFO"
        assert entry["source"] == "pipeline"
        assert entry["metadata"]["cycle"] == 1

        logs = query_structured_logs(source="pipeline", limit=10)
        assert any("Test structured event recording" in l.get("text", "") for l in logs)

    def test_log_signal_and_market_data(self):
        sig_file = log_signal_to_file("ALERT: RELIANCE CALL 2520")
        assert os.path.exists(sig_file)

        mkt_file = log_market_data_to_file("RELIANCE")
        assert os.path.exists(mkt_file)


class TestPersistenceBridge:
    def test_user_and_structured_log_persistence(self):
        async def run():
            uid = await get_or_create_default_user()
            assert uid is not None

            log_id = await save_structured_log_to_db("INFO", "test_runner", "Pytest DB execution", {"ok": True})
            assert log_id is not None

        asyncio.run(run())

    def test_algo_persistence_and_status_update(self):
        async def run():
            uid = await get_or_create_default_user()
            cfg = AlgoTradeConfig(
                algo_name="Pytest Test Scalper",
                market="INDIAN_EQUITY",
                timeframe="5m",
                symbols=["RELIANCE", "TCS"],
            )
            algo = AlgoTrade(cfg)

            db_id = await save_algo_to_db(algo, user_id=uid)
            assert db_id is not None

            # Update status
            ok = await update_algo_status_in_db(algo.algo_id, "RUNNING")
            assert ok is True

        asyncio.run(run())

    def test_audit_event_persistence_and_retrieval(self):
        async def run():
            uid = await get_or_create_default_user()
            cfg = AlgoTradeConfig(algo_name="Pytest Audit Target", symbols=["RELIANCE"])
            algo = AlgoTrade(cfg)
            await save_algo_to_db(algo, user_id=uid)

            ev = {
                "algo_id": algo.algo_id,
                "symbol": "RELIANCE",
                "event_type": "SIGNAL_APPROVED",
                "indicator_snapshot": {"rsi": 58.2, "trend": "UPTREND"},
                "level_snapshot": {"entry": 2500.0, "target": 2550.0},
                "decision_reason": "Strategy Rulebook Confirmed",
                "latency_ms": 15,
            }
            saved_id = await save_audit_event_to_db(ev)
            assert saved_id is not None

            records = await get_audit_events_from_db(algo_id=algo.algo_id, limit=5)
            assert len(records) >= 1
            assert records[0]["symbol"] == "RELIANCE"
            assert records[0]["indicator_snapshot"]["rsi"] == 58.2

        asyncio.run(run())


class TestServiceAuditEndpoints:
    @classmethod
    def setup_class(cls):
        seed_default_algos()
        cls.client = TestClient(app)

    def test_get_audits_endpoint(self):
        res = self.client.get("/api/audits")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        if len(data) > 0:
            first = data[0]
            assert "algo_name" in first
            assert "approved_signals" in first
            assert "signals_blocked_by_mtf" in first

    def test_get_algo_audit_detail_endpoint(self):
        algos = manager.list_algos()
        assert len(algos) > 0
        target = algos[0]["algo_name"]

        res = self.client.get(f"/api/audits/{target}")
        assert res.status_code == 200
        data = res.json()
        assert data["algo_name"] == target
        assert "signals" in data
        assert "audit_events" in data
        assert "summary" in data

    def test_get_persisted_audit_events_endpoint(self):
        res = self.client.get("/api/audits-events?limit=20")
        assert res.status_code == 200
        data = res.json()
        assert "events" in data
        assert isinstance(data["events"], list)

    def test_get_logs_endpoint(self):
        res = self.client.get("/api/logs?source=all&limit=50")
        assert res.status_code == 200
        data = res.json()
        assert "logs" in data
        assert "total" in data
        assert isinstance(data["logs"], list)
