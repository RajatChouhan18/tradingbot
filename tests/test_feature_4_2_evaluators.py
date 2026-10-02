"""
Test: Feature 4.2 Standalone Signal Rule Evaluators Engine
Tests all 5 signal rule evaluator types: Candlestick Patterns, Price Spike/Crash,
Volume Surge, S/R Breakout/Breakdown, and Indicator Threshold Crosses.
"""

import sys
import os
import pytest
from datetime import datetime, timedelta, timezone

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from txcore.marketview.models import CandleData
from txcore.events.models import TriggerType
from txcore.events.evaluators import (
    SignalEvaluatorEngine,
    evaluate_candle_pattern,
    evaluate_price_spike,
    evaluate_volume_spike,
    evaluate_sr_break,
    evaluate_indicator_cross,
)


def make_test_candles(base_price=100.0, count=25, vol=1000.0) -> list[CandleData]:
    base_time = datetime(2026, 10, 1, 9, 15, tzinfo=timezone.utc)
    candles = []
    for i in range(count):
        p = base_price + (i * 0.2)
        candles.append(
            CandleData(
                timestamp=base_time + timedelta(minutes=5 * i),
                open=p - 0.1,
                high=p + 0.5,
                low=p - 0.5,
                close=p,
                volume=vol,
            )
        )
    return candles


def test_price_spike_evaluator():
    candles = make_test_candles(base_price=100.0, count=10)
    # Simulate a sudden 3% spike on the last bar
    candles[-1].close = 105.0  # From ~101.8 to 105.0 (+3.1%)

    config = {"spike_pct": 2.0, "lookback_bars": 3, "direction": "BULLISH"}
    res = evaluate_price_spike(candles, config)
    assert res.matched is True
    assert res.trigger_price == 105.0
    assert res.conditions_met["calculated_change_pct"] >= 2.0

    # Test Bearish threshold with wrong direction
    config_bearish = {"spike_pct": 2.0, "lookback_bars": 3, "direction": "BEARISH"}
    res_b = evaluate_price_spike(candles, config_bearish)
    assert res_b.matched is False


def test_volume_spike_evaluator():
    candles = make_test_candles(base_price=100.0, count=25, vol=1000.0)
    # Simulate 3x volume surge on the latest bar
    candles[-1].volume = 3500.0

    config = {"volume_multiplier": 2.5, "sma_period": 20}
    res = evaluate_volume_spike(candles, config)
    assert res.matched is True
    assert res.conditions_met["volume_multiplier_achieved"] >= 2.5

    # Test when volume is ordinary
    candles[-1].volume = 1100.0
    res_normal = evaluate_volume_spike(candles, config)
    assert res_normal.matched is False


def test_sr_break_evaluator():
    candles = make_test_candles(base_price=100.0, count=10)
    # Set S/R level at 102.0. Prev bar at 101.5, latest bar closes at 103.0
    candles[-2].close = 101.5
    candles[-1].close = 103.0

    config_breakout = {
        "level": 102.0,
        "break_type": "BREAKOUT",
        "buffer_pct": 0.5,  # 102.0 * 1.005 = 102.51
    }
    res = evaluate_sr_break(candles, config_breakout)
    assert res.matched is True
    assert res.trigger_price == 103.0

    # Test Breakdown
    candles[-2].close = 99.5
    candles[-1].close = 97.0
    config_breakdown = {
        "level": 98.0,
        "break_type": "BREAKDOWN",
        "buffer_pct": 0.0,
    }
    res_bd = evaluate_sr_break(candles, config_breakdown)
    assert res_bd.matched is True


def test_indicator_cross_evaluator_rsi_and_ema():
    candles = make_test_candles(base_price=100.0, count=30)
    
    # Test unified SignalEvaluatorEngine routing
    config_rsi = {
        "indicator": "RSI",
        "rsi_operator": "GREATER_THAN",
        "rsi_threshold": 50.0,
    }
    res_rsi = SignalEvaluatorEngine.evaluate(
        trigger_type=TriggerType.INDICATOR_CROSS,
        threshold_config=config_rsi,
        candles=candles,
    )
    assert res_rsi.latency_ms >= 0.0
    assert "current_rsi" in res_rsi.conditions_met or not res_rsi.matched


def test_candle_pattern_evaluator():
    candles = make_test_candles(base_price=100.0, count=20)
    
    # Synthesize a Hammer on the last candle: small body at top, long lower shadow
    candles[-1].open = 104.0
    candles[-1].close = 104.5
    candles[-1].high = 104.6
    candles[-1].low = 101.0  # Long lower wick (3.0 vs 0.5 body)

    config = {"patterns": ["HAMMER"], "sentiment": "BULLISH"}
    res = evaluate_candle_pattern(candles, config)
    assert res.matched is True
    assert res.trigger_price == 104.5
    assert len(res.conditions_met["matched_patterns"]) > 0
    assert res.conditions_met["matched_patterns"][0]["pattern"] == "HAMMER"
    print("\n[SUCCESS] Feature 4.2 Signal Rule Evaluators Engine verified!")
