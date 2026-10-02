"""
tests.test_service_api
~~~~~~~~~~~~~~~~~~~~~~
Unit & integration tests for TxBot FastAPI backend HTTP endpoints:
  - System status and session information
  - AlgoTrade creation, copy, pause, stop, and delete
  - Signals, PnL, Market Data, Auditing, and Logs endpoints
"""

import pytest
from fastapi.testclient import TestClient

from txcore.service import app, seed_default_algos, manager


@pytest.fixture(scope="module")
def client():
    seed_default_algos()
    with TestClient(app) as c:
        yield c


def test_get_system_status(client):
    res = client.get("/api/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("ONLINE", "ERROR")
    assert "session" in data
    assert "vix" in data
    assert "breadth" in data
    assert "algos_count" in data


def test_list_and_create_algo(client):
    # 1. List initial algos
    res = client.get("/api/algos")
    assert res.status_code == 200
    algos = res.json()
    assert isinstance(algos, list)
    assert len(algos) >= 3

    # 2. Create a new custom AlgoTrade
    payload = {
        "algo_name": "Test Api Scalper",
        "market": "INDIAN_EQUITY",
        "timeframe": "5m",
        "symbols": ["RELIANCE", "INFY"],
        "indices": ["NIFTY 50"],
        "patterns": ["bullish_engulfing"],
        "indicators": ["EMA_20", "RSI"],
        "creator": "Tester",
        "start_time": "09:15:00",
        "stop_time": "15:30:00",
        "risk_reward_ratio": 1.5,
    }
    create_res = client.post("/api/algos", json=payload)
    assert create_res.status_code == 200
    created = create_res.json()["algo"]
    assert created["algo_name"] == "Test Api Scalper"
    assert created["creator"] == "Tester"
    algo_id = created["algo_id"]

    # 3. Get detail
    det_res = client.get(f"/api/algos/{algo_id}")
    assert det_res.status_code == 200
    assert det_res.json()["algo_id"] == algo_id

    # 4. Copy Algo
    copy_res = client.post(f"/api/algos/{algo_id}/copy")
    assert copy_res.status_code == 200
    assert "Copy of Test Api Scalper" in copy_res.json()["algo"]["algo_name"]

    # 5. Pause & Stop
    pause_res = client.post(f"/api/algos/{algo_id}/pause")
    assert pause_res.status_code == 200
    stop_res = client.post(f"/api/algos/{algo_id}/stop")
    assert stop_res.status_code == 200

    # 6. Delete
    del_res = client.delete(f"/api/algos/{algo_id}")
    assert del_res.status_code == 200


def test_signals_and_pnl_endpoints(client):
    # Signals list
    res = client.get("/api/signals")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # PnL summary
    pnl_res = client.get("/api/pnl")
    assert pnl_res.status_code == 200
    pnl = pnl_res.json()
    assert "total_trades" in pnl
    assert "win_rate_pct" in pnl
    assert "total_pnl_pct" in pnl


def test_market_history_and_audits_endpoints(client):
    # Market history
    hist_res = client.get("/api/market/history")
    assert hist_res.status_code == 200
    assert isinstance(hist_res.json(), list)

    # Audits list
    audit_res = client.get("/api/audits")
    assert audit_res.status_code == 200
    audits = audit_res.json()
    assert isinstance(audits, list)
    assert len(audits) >= 1
    algo_name = audits[0]["algo_name"]

    # Audit detail
    detail_res = client.get(f"/api/audits/{algo_name}")
    assert detail_res.status_code == 200
    assert detail_res.json()["algo_name"] == algo_name


def test_logs_endpoint(client):
    log_res = client.get("/api/logs?limit=50")
    assert log_res.status_code == 200
    data = log_res.json()
    assert "total" in data
    assert "logs" in data


def test_frontend_root(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "html" in res.headers.get("content-type", "").lower()
    assert "TxBot" in res.text or "vite" in res.text.lower()


def test_fetch_market_data_with_empty_dates(client):
    res = client.post("/api/market/fetch", json={
        "symbol": "RELIANCE",
        "market": "INDIAN_EQUITY",
        "timeframe": "5m",
        "lookback_bars": 60,
        "start_date": "",
        "end_date": ""
    })
    assert res.status_code == 200
    data = res.json()
    assert data["symbol"] == "RELIANCE"
    assert data["total_bars"] >= 50
    assert "candles" in data
    assert len(data["candles"]) > 0


def test_catalog_endpoints(client):
    """Tests the newly implemented Prisma catalog endpoints."""
    # 1. Groups
    g_res = client.get("/api/catalog/groups")
    assert g_res.status_code == 200
    groups = g_res.json()
    assert len(groups) >= 8
    group_ids = [g["groupId"] for g in groups]
    assert "NSE" in group_ids
    assert "DOW_JONES" in group_ids
    assert "FOREX" in group_ids

    # 2. Filtered Symbols by Group
    nse_res = client.get("/api/catalog/symbols?group=NSE")
    assert nse_res.status_code == 200
    nse_syms = nse_res.json()
    assert len(nse_syms) > 0
    assert any(s["symbol"] == "RELIANCE" for s in nse_syms)

    # 3. Fuzzy search
    search_res = client.get("/api/catalog/symbols?search=Apple")
    assert search_res.status_code == 200
    apple_syms = search_res.json()
    assert len(apple_syms) > 0
    assert apple_syms[0]["symbol"] == "AAPL"

    # 4. Markets taxonomy
    m_res = client.get("/api/catalog/markets")
    assert m_res.status_code == 200
    markets = m_res.json()
    assert len(markets) >= 5
    market_ids = [m["id"] for m in markets]
    assert "INDIAN_EQUITY" in market_ids
    assert "US_EQUITY" in market_ids


def test_concurrency_endpoint(client):
    """Tests the concurrency telemetry overview endpoint."""
    res = client.get("/api/concurrency")
    assert res.status_code == 200
    data = res.json()
    assert "total_algos_active" in data
    assert "total_max_workers" in data
    assert "total_active_threads" in data
    assert "algos_breakdown" in data
    assert data["total_max_workers"] >= 4


def test_algo_metrics_concurrency(client):
    """Verifies each algo exposes transparent concurrency metrics."""
    res = client.get("/api/algos")
    assert res.status_code == 200
    algos = res.json()
    first = algos[0]
    assert "concurrency" in first
    conc = first["concurrency"]
    assert "max_workers" in conc
    assert "active_worker_threads" in conc
    assert "queue_depth" in conc
    assert "last_cycle_duration_ms" in conc

def test_create_algo_with_phase5_mtf_and_atr_options(client):
    """Verifies that Phase 5 MTF and dynamic ATR risk controls are honored when creating an algo."""
    payload = {
        "algo_name": "Phase 5 MTF Scalper",
        "market": "INDIAN_EQUITY",
        "timeframe": "3m",
        "symbols": ["RELIANCE", "TCS"],
        "indices": ["NIFTY 50"],
        "patterns": ["bullish_engulfing", "bearish_engulfing"],
        "indicators": ["EMA_20", "VWAP"],
        "risk_reward_ratio": 2.0,
        "enable_mtf": True,
        "higher_timeframe": "15m",
        "strict_mtf": True,
        "use_atr_risk": True,
        "atr_period": 10,
        "atr_multiplier": 1.2,
        "max_workers": 6,
        "lookback_bars": 80,
        "creator": "Ishaq",
        "description": "MTF-confirmed 3m scalper with dynamic ATR brackets",
    }
    create_res = client.post("/api/algos", json=payload)
    assert create_res.status_code == 200
    data = create_res.json()
    assert "algo" in data
    created = data["algo"]
    assert created["algo_name"] == "Phase 5 MTF Scalper"
    
    cfg = created.get("config", {})
    assert cfg.get("enable_mtf") is True
    assert cfg.get("higher_timeframe") == "15m"
    assert cfg.get("strict_mtf") is True
    assert cfg.get("use_atr_risk") is True
    assert cfg.get("atr_period") == 10
    assert cfg.get("atr_multiplier") == 1.2
    assert cfg.get("max_workers") == 6
    assert cfg.get("lookback_bars") == 80




