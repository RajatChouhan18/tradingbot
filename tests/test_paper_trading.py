"""
tests.test_paper_trading
~~~~~~~~~~~~~~~~~~~~~~~~
Unit and integration tests for Phase 6 Paper Trading & Simulated Order Execution Engine:
  - Account capital, margins, and equity tracking
  - Opening simulated positions from approved Signals
  - Mark-to-market valuation & trailing stop-loss ratcheting
  - Target Hit & Stop Loss Hit automatic exits
  - Manual square-off & bracket modification
  - FastAPI Paper Trading REST API endpoints
  - Integration with AlgoTrade.execute_pipeline
"""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from txcore.models.types import Direction, Signal
from txcore.execution.paper_engine import (
    PaperTradingEngine,
    get_paper_engine,
    PositionStatus,
)
from txcore.service import app


@pytest.fixture
def fresh_engine():
    """Provides a fresh PaperTradingEngine with 1,000,000 INR starting capital."""
    engine = PaperTradingEngine(initial_capital=1_000_000.0, currency="INR")
    return engine


def test_paper_engine_initialization(fresh_engine):
    summary = fresh_engine.get_portfolio_summary()
    assert summary["initial_capital"] == 1_000_000.0
    assert summary["cash_balance"] == 1_000_000.0
    assert summary["total_equity"] == 1_000_000.0
    assert summary["used_margin"] == 0.0
    assert summary["open_positions_count"] == 0
    assert summary["closed_trades_count"] == 0
    assert summary["currency"] == "INR"


def test_open_call_position_from_signal(fresh_engine):
    signal = Signal(
        symbol="RELIANCE",
        direction=Direction.CALL,
        pattern="bullish_engulfing",
        price=2500.0,
        level=2480.0,
        stop_loss=2450.0,
        target=2600.0,
        timeframe="5m",
        candle_time=datetime.now(timezone.utc),
    )

    pos = fresh_engine.open_position_from_signal(
        signal=signal,
        algo_id="AT-Test-01",
        algo_name="Test Strategy",
        risk_capital_pct=0.05,
    )

    assert pos is not None
    assert pos.symbol == "RELIANCE"
    assert pos.direction == "CALL"
    assert pos.side == "BUY"
    assert pos.entry_price > 2500.0  # Slippage added
    assert pos.quantity > 0
    assert pos.stop_loss == 2450.0
    assert pos.target == 2600.0
    assert pos.trailing_sl == 2450.0

    summary = fresh_engine.get_portfolio_summary()
    assert summary["open_positions_count"] == 1
    assert summary["used_margin"] > 0
    assert summary["cash_balance"] < 1_000_000.0


def test_open_put_position_from_signal(fresh_engine):
    signal = Signal(
        symbol="INFY",
        direction=Direction.PUT,
        pattern="bearish_engulfing",
        price=1500.0,
        level=1520.0,
        stop_loss=1530.0,
        target=1440.0,
        timeframe="5m",
        candle_time=datetime.now(timezone.utc),
    )

    pos = fresh_engine.open_position_from_signal(
        signal=signal,
        algo_id="AT-Test-02",
        algo_name="Test Strategy Put",
        risk_capital_pct=0.05,
    )

    assert pos is not None
    assert pos.symbol == "INFY"
    assert pos.direction == "PUT"
    assert pos.side == "SELL"
    assert pos.entry_price < 1500.0  # Slippage subtracted for short


def test_mark_to_market_and_target_hit(fresh_engine):
    signal = Signal(
        symbol="TCS",
        direction=Direction.CALL,
        pattern="piercing_line",
        price=3500.0,
        level=3480.0,
        stop_loss=3400.0,
        target=3600.0,
        timeframe="5m",
        candle_time=datetime.now(timezone.utc),
    )

    pos = fresh_engine.open_position_from_signal(signal, "AT-01", "Strategy 1")
    assert pos is not None

    # Tick 1: Price rises to 3550 (favorable, trailing SL ratchets)
    fresh_engine.update_price_tick("TCS", ltp=3550.0)
    assert pos.current_price == 3550.0
    assert pos.unrealized_pnl > 0
    assert pos.trailing_sl > pos.stop_loss

    # Tick 2: Price hits Target 3600 -> Position auto-closes as WIN
    closed = fresh_engine.update_price_tick("TCS", ltp=3605.0, high=3610.0)
    assert len(closed) == 1
    trade = closed[0]
    assert trade["outcome"] == "WIN"
    assert trade["reason"] == "TARGET_HIT"
    assert trade["exit_price"] == 3600.0
    assert trade["pnl_points"] > 0
    assert fresh_engine.win_trades == 1

    # Open positions should now be empty
    assert len(fresh_engine.get_open_positions()) == 0


def test_stop_loss_hit(fresh_engine):
    signal = Signal(
        symbol="HDFCBANK",
        direction=Direction.CALL,
        pattern="bullish_engulfing",
        price=1600.0,
        level=1590.0,
        stop_loss=1570.0,
        target=1660.0,
        timeframe="5m",
        candle_time=datetime.now(timezone.utc),
    )

    pos = fresh_engine.open_position_from_signal(signal, "AT-01", "Strategy 1")
    assert pos is not None

    # Price drops to 1565 (SL hit)
    closed = fresh_engine.update_price_tick("HDFCBANK", ltp=1568.0, low=1565.0)
    assert len(closed) == 1
    trade = closed[0]
    assert trade["outcome"] == "LOSS"
    assert trade["reason"] == "SL_HIT"
    assert trade["pnl_points"] < 0
    assert fresh_engine.loss_trades == 1


def test_manual_square_off(fresh_engine):
    signal = Signal(
        symbol="SBIN",
        direction=Direction.CALL,
        pattern="piercing_line",
        price=750.0,
        level=740.0,
        stop_loss=730.0,
        target=800.0,
        timeframe="5m",
        candle_time=datetime.now(timezone.utc),
    )

    pos = fresh_engine.open_position_from_signal(signal, "AT-01", "Strategy 1")
    assert pos is not None

    # Manual square off at 760
    trade = fresh_engine.close_position_manually(pos.position_id, exit_price=760.0)
    assert trade is not None
    assert trade["reason"] == "MANUAL_SQUARE_OFF"
    assert trade["outcome"] == "WIN"
    assert trade["exit_price"] == 760.0


def test_modify_position_brackets(fresh_engine):
    signal = Signal(
        symbol="WIPRO",
        direction=Direction.CALL,
        pattern="bullish_engulfing",
        price=450.0,
        level=445.0,
        stop_loss=435.0,
        target=480.0,
        timeframe="5m",
        candle_time=datetime.now(timezone.utc),
    )

    pos = fresh_engine.open_position_from_signal(signal, "AT-01", "Strategy 1")
    assert pos is not None

    modified = fresh_engine.modify_position(pos.position_id, stop_loss=440.0, target=490.0)
    assert modified is not None
    assert modified.stop_loss == 440.0
    assert modified.target == 490.0


def test_reset_paper_account(fresh_engine):
    signal = Signal(
        symbol="TATAMOTORS",
        direction=Direction.CALL,
        pattern="bullish_engulfing",
        price=900.0,
        level=890.0,
        stop_loss=870.0,
        target=960.0,
        timeframe="5m",
        candle_time=datetime.now(timezone.utc),
    )

    fresh_engine.open_position_from_signal(signal, "AT-01", "Strategy 1")
    assert len(fresh_engine.open_positions) == 1

    fresh_engine.reset_account(initial_capital=500_000.0)
    assert fresh_engine.cash_balance == 500_000.0
    assert len(fresh_engine.open_positions) == 0
    assert len(fresh_engine.closed_trades) == 0


# =============================================================================
# REST API ENDPOINT TESTS
# =============================================================================

@pytest.fixture(scope="module")
def api_client():
    with TestClient(app) as c:
        yield c


def test_paper_api_portfolio_and_positions(api_client):
    # 1. Reset paper account
    res = api_client.post("/api/paper/reset", json={"initial_capital": 1000000.0})
    assert res.status_code == 200

    # 2. Get portfolio
    p_res = api_client.get("/api/paper/portfolio")
    assert p_res.status_code == 200
    p_data = p_res.json()
    assert "total_equity" in p_data
    assert "cash_balance" in p_data
    assert "open_positions_count" in p_data

    # 3. Get positions
    pos_res = api_client.get("/api/paper/positions")
    assert pos_res.status_code == 200
    assert isinstance(pos_res.json(), list)

    # 4. Get trades
    trd_res = api_client.get("/api/paper/trades")
    assert trd_res.status_code == 200
    assert isinstance(trd_res.json(), list)


def test_paper_api_open_modify_close(api_client):
    pe = get_paper_engine()
    signal = Signal(
        symbol="BAJFINANCE",
        direction=Direction.CALL,
        pattern="bullish_engulfing",
        price=7000.0,
        level=6950.0,
        stop_loss=6850.0,
        target=7300.0,
        timeframe="5m",
        candle_time=datetime.now(timezone.utc),
    )
    pos = pe.open_position_from_signal(signal, algo_id="AT-API-01", algo_name="API Algo")
    assert pos is not None
    pos_id = pos.position_id

    # 1. Verify visible in API
    pos_res = api_client.get("/api/paper/positions")
    assert pos_res.status_code == 200
    positions = pos_res.json()
    assert any(p["position_id"] == pos_id for p in positions)

    # 2. Modify position via API
    mod_res = api_client.post(
        f"/api/paper/positions/{pos_id}/modify",
        json={"stop_loss": 6900.0, "target": 7400.0},
    )
    assert mod_res.status_code == 200
    assert mod_res.json()["position"]["stop_loss"] == 6900.0

    # 3. Square off via API
    close_res = api_client.post(
        f"/api/paper/positions/{pos_id}/close",
        json={"exit_price": 7050.0},
    )
    assert close_res.status_code == 200
    assert close_res.json()["status"] == "SUCCESS"
    assert close_res.json()["trade"]["outcome"] == "WIN"
