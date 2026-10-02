"""
tests.test_phase7_broker_and_risk
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Comprehensive unit and integration test suite for Phase 7:
  - Universal Broker Abstraction Layer (Paper, Zerodha Kite, Interactive Brokers)
  - BrokerManager registry & dynamic broker routing
  - Account-Level RiskManager & Circuit Breaker Engine
  - Multi-tier safety guards (Daily drawdown limit, max open exposure, consecutive losses cooldown)
  - Global Emergency Kill Switch & automatic portfolio liquidation
  - Multi-channel dispatchers (Discord rich embeds & Webhook JSON relays)
  - REST API endpoints for Risk and Broker management
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from txcore.execution.broker_adapter import (
    OrderSide,
    OrderType,
    OrderStatus,
    PaperBrokerAdapter,
    ZerodhaKiteBrokerAdapter,
    InteractiveBrokersAdapter,
    BrokerManager,
    get_broker_manager,
)
from txcore.filters.risk_manager import (
    RiskManager,
    CircuitBreakerStatus,
    get_risk_manager,
)
from txcore.execution.discord import DiscordNotifier
from txcore.execution.webhook import WebhookNotifier
from txcore.models.types import Signal, Direction
from txcore.service import app


# =============================================================================
# 1. BROKER ADAPTER TESTS
# =============================================================================

def test_paper_broker_adapter_lifecycle():
    adapter = PaperBrokerAdapter()
    assert adapter.broker_name == "PAPER"
    assert adapter.is_connected() is True

    profile = adapter.get_account_profile()
    assert profile["broker"] == "PAPER_SIMULATOR"
    assert profile["status"] == "ACTIVE"

    margins = adapter.get_margins()
    assert "available_cash" in margins
    assert "total_equity" in margins

    # Place order
    order = adapter.place_order(
        symbol="INFY",
        side=OrderSide.BUY,
        quantity=10,
        price=1500.0,
        stop_loss=1450.0,
        target=1600.0,
        tag="TEST_ALGO",
    )
    assert order.status == OrderStatus.FILLED
    assert order.symbol == "INFY"
    assert order.filled_quantity > 0

    # Get positions
    positions = adapter.get_positions()
    assert any(p.symbol == "INFY" for p in positions)

    # Close position
    closed = adapter.close_position("INFY")
    assert closed is True


def test_zerodha_kite_broker_adapter():
    kite = ZerodhaKiteBrokerAdapter(api_key="mock_key", access_token="mock_token")
    assert kite.broker_name == "ZERODHA"
    assert kite.is_connected() is True

    profile = kite.get_account_profile()
    assert profile["broker"] == "ZERODHA_KITE"
    assert "MIS" in profile["products"]

    # Place order
    order = kite.place_order(
        symbol="RELIANCE",
        side=OrderSide.BUY,
        quantity=5,
        price=2500.0,
        stop_loss=2450.0,
        target=2600.0,
        tag="KITE_TEST",
    )
    assert order.status == OrderStatus.FILLED
    assert order.symbol == "RELIANCE"

    # Verify positions
    positions = kite.get_positions()
    assert len(positions) == 1
    assert positions[0].symbol == "RELIANCE"

    # Emergency square off
    closed_list = kite.square_off_all()
    assert len(closed_list) == 1
    assert len(kite.get_positions()) == 0


def test_interactive_brokers_adapter():
    ibkr = InteractiveBrokersAdapter()
    assert ibkr.broker_name == "INTERACTIVE_BROKERS"
    assert ibkr.is_connected() is True

    profile = ibkr.get_account_profile()
    assert profile["currency"] == "USD"

    order = ibkr.place_order(
        symbol="AAPL",
        side=OrderSide.BUY,
        quantity=10,
        price=220.0,
    )
    assert order.status == OrderStatus.FILLED
    assert len(ibkr.get_positions()) == 1

    ibkr.close_position("AAPL")
    assert len(ibkr.get_positions()) == 0


def test_broker_manager_registry():
    bm = get_broker_manager()
    assert bm.active_broker_name in ("PAPER", "ZERODHA", "INTERACTIVE_BROKERS")

    # Adapter retrieval
    paper_adapter = bm.get_adapter("PAPER")
    assert isinstance(paper_adapter, PaperBrokerAdapter)

    kite_adapter = bm.get_adapter("ZERODHA")
    assert isinstance(kite_adapter, ZerodhaKiteBrokerAdapter)

    # Fallback to PAPER for unknown broker
    fallback = bm.get_adapter("UNKNOWN_BROKER")
    assert isinstance(fallback, PaperBrokerAdapter)

    # Active broker switching
    bm.set_active_broker("ZERODHA")
    assert bm.active_broker_name == "ZERODHA"
    bm.set_active_broker("PAPER")
    assert bm.active_broker_name == "PAPER"

    # Broker listing
    brokers = bm.list_brokers()
    assert len(brokers) >= 3
    assert any(b["name"] == "PAPER" for b in brokers)


# =============================================================================
# 2. RISK MANAGER & CIRCUIT BREAKER TESTS
# =============================================================================

@pytest.fixture
def fresh_risk_manager():
    rm = RiskManager(
        starting_daily_equity=1_000_000.0,
        max_daily_loss_pct=0.03,        # 3% max loss = 30,000 INR
        max_open_positions=3,
        consecutive_loss_limit=3,
        cooldown_minutes=15,
    )
    return rm


def test_risk_manager_normal_state(fresh_risk_manager):
    rm = fresh_risk_manager
    assert rm.status == CircuitBreakerStatus.NORMAL

    # Within limits -> trade allowed
    allowed, reason = rm.is_allowed("TCS", active_positions_count=1)
    assert allowed is True
    assert reason is None


def test_risk_manager_max_positions_limit(fresh_risk_manager):
    rm = fresh_risk_manager
    # 3 positions active >= limit of 3
    allowed, reason = rm.is_allowed("INFY", active_positions_count=3)
    assert allowed is False
    assert "Max open positions limit" in reason


def test_risk_manager_daily_drawdown_limit(fresh_risk_manager):
    rm = fresh_risk_manager
    # Equity drops from 1,000,000 to 965,000 (35,000 loss = 3.5% > 3%)
    rm.update_current_equity(965_000.0)
    assert rm.status == CircuitBreakerStatus.TRIPPED_MAX_LOSS

    allowed, reason = rm.is_allowed("RELIANCE", active_positions_count=0)
    assert allowed is False
    assert "Max daily loss limit breached" in reason or "Drawdown" in reason


def test_risk_manager_consecutive_losses_cooldown(fresh_risk_manager):
    rm = fresh_risk_manager
    rm.record_trade_result("LOSS", -2000.0)
    assert rm.consecutive_losses == 1
    assert rm.status == CircuitBreakerStatus.NORMAL

    rm.record_trade_result("LOSS", -2000.0)
    assert rm.consecutive_losses == 2

    # 3rd consecutive loss trips cooldown
    rm.record_trade_result("LOSS", -2000.0)
    assert rm.consecutive_losses == 3
    assert rm.status == CircuitBreakerStatus.TRIPPED_CONSECUTIVE_LOSS

    allowed, reason = rm.is_allowed("SBIN", active_positions_count=0)
    assert allowed is False
    assert "cooling off" in reason

    # Manual reset restores to NORMAL
    rm.reset_circuit_breaker()
    assert rm.status == CircuitBreakerStatus.NORMAL
    assert rm.consecutive_losses == 0


def test_risk_manager_emergency_kill_switch(fresh_risk_manager):
    rm = fresh_risk_manager
    res = rm.trigger_emergency_square_off("Testing Operator Panic")
    assert res["status"] == "EMERGENCY_HALT_ACTIVE"
    assert rm.status == CircuitBreakerStatus.EMERGENCY_HALT

    allowed, reason = rm.is_allowed("WIPRO", active_positions_count=0)
    assert allowed is False
    assert "Global Emergency Kill Switch active" in reason

    # Reset
    rm.reset_circuit_breaker()
    assert rm.status == CircuitBreakerStatus.NORMAL


# =============================================================================
# 3. NOTIFIERS (DISCORD & WEBHOOK) TESTS
# =============================================================================

def test_discord_notifier_formatting_and_send():
    notifier = DiscordNotifier(webhook_url="https://discord.com/api/webhooks/mock/test")
    assert notifier.is_configured is True

    sig = Signal(
        pair="RELIANCE",
        direction=Direction.CALL,
        pattern="Bullish Engulfing",
        level=2480.0,
        price=2500.0,
        stop_loss=2450.0,
        target=2600.0,
    )

    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 204
        mock_post.return_value = mock_resp

        success = notifier.send("Bullish alert", signal=sig)
        assert success is True
        assert mock_post.called
        args, kwargs = mock_post.call_args
        assert "json" in kwargs
        embeds = kwargs["json"]["embeds"]
        assert len(embeds) == 1
        assert embeds[0]["color"] == 0x10B981  # Emerald green


def test_webhook_notifier_json_relay():
    webhook = WebhookNotifier(endpoint_url="https://api.external.com/trade-relay")
    assert webhook.is_configured is True

    sig = Signal(
        pair="INFY",
        direction=Direction.PUT,
        pattern="Bearish Engulfing",
        level=1520.0,
        price=1500.0,
        stop_loss=1530.0,
        target=1440.0,
    )

    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        success = webhook.send("Short signal", signal=sig)
        assert success is True
        assert mock_post.called
        args, kwargs = mock_post.call_args
        data = kwargs["json"]
        assert data["symbol"] == "INFY"
        assert data["direction"] == "PUT"


# =============================================================================
# 4. REST API ENDPOINT INTEGRATION TESTS
# =============================================================================

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_api_risk_status_and_config(client):
    # 1. Get status
    res = client.get("/api/risk/status")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "drawdown_pct" in data
    assert "max_open_positions" in data

    # 2. Update config
    cfg_res = client.post("/api/risk/config", json={
        "max_daily_loss_pct": 0.04,
        "max_open_positions": 6,
    })
    assert cfg_res.status_code == 200
    assert cfg_res.json()["risk_status"]["max_open_positions"] == 6

    # 3. Emergency square-off & reset
    panic_res = client.post("/api/risk/emergency-square-off", json={"reason": "Integration Test Panic"})
    assert panic_res.status_code == 200
    assert panic_res.json()["status"] == "EMERGENCY_HALT_ACTIVE"

    reset_res = client.post("/api/risk/reset-breaker")
    assert reset_res.status_code == 200
    assert reset_res.json()["current_status"] == "NORMAL"


def test_api_broker_endpoints(client):
    # 1. List brokers
    res = client.get("/api/brokers")
    assert res.status_code == 200
    data = res.json()
    assert "active_broker" in data
    assert len(data["brokers"]) >= 3

    # 2. Select broker
    sel_res = client.post("/api/brokers/select", json={"broker_name": "ZERODHA"})
    assert sel_res.status_code == 200
    assert sel_res.json()["active_broker"] == "ZERODHA"

    # 3. Place order via broker API
    ord_res = client.post("/api/brokers/ZERODHA/orders", json={
        "symbol": "HDFCBANK",
        "side": "BUY",
        "quantity": 10,
        "price": 1600.0,
        "stop_loss": 1580.0,
        "target": 1650.0,
    })
    assert ord_res.status_code == 200
    assert ord_res.json()["status"] == "SUCCESS"
    assert ord_res.json()["order"]["symbol"] == "HDFCBANK"

    # 4. Get positions
    pos_res = client.get("/api/brokers/ZERODHA/positions")
    assert pos_res.status_code == 200
    positions = pos_res.json()
    assert any(p["symbol"] == "HDFCBANK" for p in positions)

    # Restore default broker
    client.post("/api/brokers/select", json={"broker_name": "PAPER"})
