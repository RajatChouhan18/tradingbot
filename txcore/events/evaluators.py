"""
AuraTrade Standalone Signal Rule Evaluators (txcore.events.evaluators)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Evaluates raw and technical market data against user-configured trigger rules:
- Candlestick Patterns (17 recognized patterns)
- Price Spike / Crash (% movement in N bars)
- Volume Spike (multiplier vs 20-period SMA)
- Support / Resistance Breaks (Breakout / Breakdown with tolerance buffer)
- Indicator Crosses (RSI thresholds, EMA crossovers, VWAP crosses)
"""

import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
from pydantic import BaseModel, Field

from txcore.marketview.models import CandleData, ProviderTechnicals
from txcore.marketview.overlays import (
    compute_market_technicals,
    candles_to_dataframe,
    calculate_ema,
    calculate_sma,
    calculate_vwap,
    calculate_rsi,
)
from txcore.events.models import TriggerType

logger = logging.getLogger("auratrade.events.evaluators")


class EvaluationResult(BaseModel):
    matched: bool
    trigger_type: str
    trigger_price: float
    conditions_met: Dict[str, Any] = Field(default_factory=dict)
    evaluation_message: str = ""
    latency_ms: float = 0.0


def evaluate_candle_pattern(
    candles: List[CandleData],
    config: Dict[str, Any],
    technicals: Optional[ProviderTechnicals] = None,
) -> EvaluationResult:
    """
    Evaluates whether the latest closed candle contains one of the configured candlestick patterns.
    """
    if not candles:
        return EvaluationResult(
            matched=False,
            trigger_type=TriggerType.CANDLE_PATTERN.value,
            trigger_price=0.0,
            evaluation_message="No candles provided for evaluation.",
        )

    last_candle = candles[-1]
    trigger_price = float(last_candle.close)

    # Compute technicals if not passed
    if technicals is None:
        technicals = compute_market_technicals(candles, symbol="EVAL")

    target_patterns = config.get("patterns", [])
    if isinstance(target_patterns, str):
        target_patterns = [p.strip() for p in target_patterns.split(",") if p.strip()]

    sentiment_filter = config.get("sentiment", "ANY").upper()

    # Check pattern markers detected on the last bar
    detected_patterns = technicals.candles or technicals.patterns or []
    last_idx = len(candles) - 1

    matched_patterns = []
    for p in detected_patterns:
        if p.index == last_idx:
            # Check pattern match
            if not target_patterns or "ALL" in target_patterns or p.pattern in target_patterns:
                # Check sentiment match
                if sentiment_filter == "ANY" or p.sentiment.upper() == sentiment_filter:
                    matched_patterns.append({
                        "pattern": p.pattern,
                        "sentiment": p.sentiment,
                        "description": p.description,
                    })

    if matched_patterns:
        pattern_names = ", ".join([p["pattern"] for p in matched_patterns])
        return EvaluationResult(
            matched=True,
            trigger_type=TriggerType.CANDLE_PATTERN.value,
            trigger_price=trigger_price,
            conditions_met={
                "matched_patterns": matched_patterns,
                "candle_time": last_candle.timestamp.isoformat(),
            },
            evaluation_message=f"Candlestick pattern '{pattern_names}' detected on latest candle at {trigger_price}.",
        )

    return EvaluationResult(
        matched=False,
        trigger_type=TriggerType.CANDLE_PATTERN.value,
        trigger_price=trigger_price,
        evaluation_message=f"No matching candlestick pattern found on latest candle (targets: {target_patterns}).",
    )


def evaluate_price_spike(
    candles: List[CandleData],
    config: Dict[str, Any],
) -> EvaluationResult:
    """
    Evaluates whether price moved by >= spike_pct over lookback_bars.
    """
    if len(candles) < 2:
        return EvaluationResult(
            matched=False,
            trigger_type=TriggerType.PRICE_SPIKE.value,
            trigger_price=candles[-1].close if candles else 0.0,
            evaluation_message="Insufficient candle history for price spike evaluation (minimum 2 bars required).",
        )

    lookback_bars = int(config.get("lookback_bars", config.get("lookback", 3)))
    spike_pct = float(config.get("spike_pct", config.get("percentage", 1.5)))
    direction = str(config.get("direction", "ANY")).upper()

    available_bars = min(lookback_bars, len(candles) - 1)
    ref_candle = candles[-1 - available_bars]
    latest_candle = candles[-1]
    trigger_price = float(latest_candle.close)

    if ref_candle.open == 0 or ref_candle.close == 0:
        return EvaluationResult(
            matched=False,
            trigger_type=TriggerType.PRICE_SPIKE.value,
            trigger_price=trigger_price,
            evaluation_message="Invalid reference candle price (zero).",
        )

    # Calculate percentage change from reference open (or close) to latest close
    ref_price = float(ref_candle.open)
    price_change_pct = ((trigger_price - ref_price) / ref_price) * 100.0
    abs_change_pct = abs(price_change_pct)

    is_bullish = price_change_pct >= spike_pct
    is_bearish = price_change_pct <= -spike_pct

    matched = False
    if direction == "BULLISH" and is_bullish:
        matched = True
    elif direction == "BEARISH" and is_bearish:
        matched = True
    elif direction == "ANY" and abs_change_pct >= spike_pct:
        matched = True

    conditions = {
        "calculated_change_pct": round(price_change_pct, 3),
        "required_spike_pct": spike_pct,
        "lookback_bars": available_bars,
        "reference_price": ref_price,
        "latest_price": trigger_price,
        "direction": direction,
    }

    if matched:
        dir_label = "Surge" if price_change_pct > 0 else "Drop"
        return EvaluationResult(
            matched=True,
            trigger_type=TriggerType.PRICE_SPIKE.value,
            trigger_price=trigger_price,
            conditions_met=conditions,
            evaluation_message=f"Price {dir_label} of {price_change_pct:+.2f}% detected over {available_bars} bars (threshold: {spike_pct}%).",
        )

    return EvaluationResult(
        matched=False,
        trigger_type=TriggerType.PRICE_SPIKE.value,
        trigger_price=trigger_price,
        conditions_met=conditions,
        evaluation_message=f"Price movement {price_change_pct:+.2f}% did not meet threshold of {spike_pct}%.",
    )


def evaluate_volume_spike(
    candles: List[CandleData],
    config: Dict[str, Any],
) -> EvaluationResult:
    """
    Evaluates whether current volume >= volume_multiplier * 20-period SMA volume.
    """
    if len(candles) < 5:
        return EvaluationResult(
            matched=False,
            trigger_type=TriggerType.VOLUME_SPIKE.value,
            trigger_price=candles[-1].close if candles else 0.0,
            evaluation_message="Insufficient candle history for volume spike evaluation (minimum 5 bars required).",
        )

    volume_multiplier = float(config.get("volume_multiplier", config.get("multiplier", 2.0)))
    sma_period = int(config.get("sma_period", config.get("period", 20)))

    df = candles_to_dataframe(candles)
    sma_vol_series = df["volume"].rolling(window=sma_period, min_periods=3).mean()
    
    current_vol = float(df["volume"].iloc[-1])
    avg_vol = float(sma_vol_series.iloc[-2]) if len(sma_vol_series) > 1 and not pd.isna(sma_vol_series.iloc[-2]) else float(df["volume"].mean())

    if avg_vol <= 0:
        return EvaluationResult(
            matched=False,
            trigger_type=TriggerType.VOLUME_SPIKE.value,
            trigger_price=float(candles[-1].close),
            evaluation_message="Average volume baseline is zero.",
        )

    current_multiplier = current_vol / avg_vol
    matched = current_multiplier >= volume_multiplier

    conditions = {
        "current_volume": current_vol,
        "average_volume": round(avg_vol, 2),
        "volume_multiplier_achieved": round(current_multiplier, 2),
        "required_multiplier": volume_multiplier,
        "sma_period": sma_period,
    }

    trigger_price = float(candles[-1].close)

    if matched:
        return EvaluationResult(
            matched=True,
            trigger_type=TriggerType.VOLUME_SPIKE.value,
            trigger_price=trigger_price,
            conditions_met=conditions,
            evaluation_message=f"Volume surge of {current_multiplier:.1f}x average volume detected (threshold: {volume_multiplier}x).",
        )

    return EvaluationResult(
        matched=False,
        trigger_type=TriggerType.VOLUME_SPIKE.value,
        trigger_price=trigger_price,
        conditions_met=conditions,
        evaluation_message=f"Current volume ({current_multiplier:.1f}x) is below the required {volume_multiplier}x multiplier.",
    )


def evaluate_sr_break(
    candles: List[CandleData],
    config: Dict[str, Any],
) -> EvaluationResult:
    """
    Evaluates Support/Resistance Level Breakout or Breakdown.
    """
    if not candles:
        return EvaluationResult(
            matched=False,
            trigger_type=TriggerType.SR_BREAK.value,
            trigger_price=0.0,
            evaluation_message="No candle data available for S/R break evaluation.",
        )

    level = float(config.get("level", 0.0))
    if level <= 0:
        return EvaluationResult(
            matched=False,
            trigger_type=TriggerType.SR_BREAK.value,
            trigger_price=float(candles[-1].close),
            evaluation_message="Invalid or missing S/R level price.",
        )

    break_type = str(config.get("break_type", config.get("direction", "BREAKOUT"))).upper()
    buffer_pct = float(config.get("buffer_pct", config.get("buffer", 0.0)))

    latest_close = float(candles[-1].close)
    prev_close = float(candles[-2].close) if len(candles) > 1 else latest_close

    breakout_level = level * (1.0 + (buffer_pct / 100.0))
    breakdown_level = level * (1.0 - (buffer_pct / 100.0))

    matched = False
    if break_type in ["BREAKOUT", "ABOVE"]:
        # Price closes above resistance
        matched = latest_close >= breakout_level and prev_close < breakout_level
    elif break_type in ["BREAKDOWN", "BELOW"]:
        # Price closes below support
        matched = latest_close <= breakdown_level and prev_close > breakdown_level

    conditions = {
        "sr_level": level,
        "break_type": break_type,
        "buffer_pct": buffer_pct,
        "target_break_level": breakout_level if break_type in ["BREAKOUT", "ABOVE"] else breakdown_level,
        "latest_close": latest_close,
        "prev_close": prev_close,
    }

    if matched:
        return EvaluationResult(
            matched=True,
            trigger_type=TriggerType.SR_BREAK.value,
            trigger_price=latest_close,
            conditions_met=conditions,
            evaluation_message=f"S/R {break_type} confirmed: close at {latest_close} crossed level {level} (buffer: {buffer_pct}%).",
        )

    return EvaluationResult(
        matched=False,
        trigger_type=TriggerType.SR_BREAK.value,
        trigger_price=latest_close,
        conditions_met=conditions,
        evaluation_message=f"Price {latest_close} did not break {break_type} level of {level}.",
    )


def evaluate_indicator_cross(
    candles: List[CandleData],
    config: Dict[str, Any],
    technicals: Optional[ProviderTechnicals] = None,
) -> EvaluationResult:
    """
    Evaluates indicator cross conditions: RSI thresholds, EMA crossovers, VWAP crosses.
    """
    if len(candles) < 5:
        return EvaluationResult(
            matched=False,
            trigger_type=TriggerType.INDICATOR_CROSS.value,
            trigger_price=candles[-1].close if candles else 0.0,
            evaluation_message="Insufficient candle history for indicator cross evaluation (minimum 5 bars required).",
        )

    if technicals is None:
        technicals = compute_market_technicals(candles, symbol="EVAL")

    indicators = technicals.indicators or technicals.overlays or {}
    indicator_name = str(config.get("indicator", "RSI")).upper()
    latest_close = float(candles[-1].close)

    # --- 1. RSI Threshold Evaluation ---
    if "RSI" in indicator_name:
        rsi_series = indicators.get("RSI_14") or indicators.get("RSI") or []
        if not rsi_series or len(rsi_series) < 2:
            return EvaluationResult(
                matched=False,
                trigger_type=TriggerType.INDICATOR_CROSS.value,
                trigger_price=latest_close,
                evaluation_message="RSI series could not be calculated.",
            )

        current_rsi = rsi_series[-1]
        prev_rsi = rsi_series[-2]
        if current_rsi is None or prev_rsi is None:
            return EvaluationResult(
                matched=False,
                trigger_type=TriggerType.INDICATOR_CROSS.value,
                trigger_price=latest_close,
                evaluation_message="RSI value is None for the latest bar.",
            )

        operator = str(config.get("rsi_operator", config.get("operator", "GREATER_THAN"))).upper()
        threshold = float(config.get("rsi_threshold", config.get("threshold", 70.0)))

        matched = False
        if operator in ["GREATER_THAN", "ABOVE", "OVERBOUGHT"]:
            matched = current_rsi >= threshold and prev_rsi < threshold
        elif operator in ["LESS_THAN", "BELOW", "OVERSOLD"]:
            matched = current_rsi <= threshold and prev_rsi > threshold

        conditions = {
            "current_rsi": round(float(current_rsi), 2),
            "prev_rsi": round(float(prev_rsi), 2),
            "threshold": threshold,
            "operator": operator,
        }

        if matched:
            return EvaluationResult(
                matched=True,
                trigger_type=TriggerType.INDICATOR_CROSS.value,
                trigger_price=latest_close,
                conditions_met=conditions,
                evaluation_message=f"RSI {operator} {threshold} triggered (Current: {current_rsi:.1f}, Previous: {prev_rsi:.1f}).",
            )

        return EvaluationResult(
            matched=False,
            trigger_type=TriggerType.INDICATOR_CROSS.value,
            trigger_price=latest_close,
            conditions_met=conditions,
            evaluation_message=f"RSI ({current_rsi:.1f}) did not cross {operator} threshold of {threshold}.",
        )

    # --- 2. EMA Cross Evaluation ---
    elif "EMA" in indicator_name:
        fast_period = int(config.get("ema_fast", config.get("fast_period", 9)))
        slow_period = int(config.get("ema_slow", config.get("slow_period", 21)))
        cross_direction = str(config.get("cross_direction", config.get("direction", "GOLDEN"))).upper()

        fast_key = f"EMA_{fast_period}"
        slow_key = f"EMA_{slow_period}"

        df = candles_to_dataframe(candles)
        fast_series = calculate_ema(df["close"], fast_period)
        slow_series = calculate_ema(df["close"], slow_period)

        if len(fast_series) < 2 or len(slow_series) < 2:
            return EvaluationResult(
                matched=False,
                trigger_type=TriggerType.INDICATOR_CROSS.value,
                trigger_price=latest_close,
                evaluation_message="Insufficient data for EMA crossover.",
            )

        f_curr, f_prev = fast_series[-1], fast_series[-2]
        s_curr, s_prev = slow_series[-1], slow_series[-2]

        if None in [f_curr, f_prev, s_curr, s_prev]:
            return EvaluationResult(
                matched=False,
                trigger_type=TriggerType.INDICATOR_CROSS.value,
                trigger_price=latest_close,
                evaluation_message="EMA series contains NaN values.",
            )

        matched = False
        if cross_direction in ["GOLDEN", "BULLISH", "ABOVE"]:
            # Fast crosses above Slow
            matched = f_curr >= s_curr and f_prev < s_prev
        elif cross_direction in ["DEATH", "BEARISH", "BELOW"]:
            # Fast crosses below Slow
            matched = f_curr <= s_curr and f_prev > s_prev

        conditions = {
            "fast_ema_current": round(float(f_curr), 4),
            "fast_ema_prev": round(float(f_prev), 4),
            "slow_ema_current": round(float(s_curr), 4),
            "slow_ema_prev": round(float(s_prev), 4),
            "fast_period": fast_period,
            "slow_period": slow_period,
            "cross_direction": cross_direction,
        }

        if matched:
            return EvaluationResult(
                matched=True,
                trigger_type=TriggerType.INDICATOR_CROSS.value,
                trigger_price=latest_close,
                conditions_met=conditions,
                evaluation_message=f"EMA {fast_period} {cross_direction} cross over EMA {slow_period} confirmed (Fast: {f_curr}, Slow: {s_curr}).",
            )

        return EvaluationResult(
            matched=False,
            trigger_type=TriggerType.INDICATOR_CROSS.value,
            trigger_price=latest_close,
            conditions_met=conditions,
            evaluation_message=f"No EMA crossover detected (Fast: {f_curr}, Slow: {s_curr}).",
        )

    # --- 3. VWAP Cross Evaluation ---
    elif "VWAP" in indicator_name:
        vwap_series = indicators.get("VWAP") or []
        if not vwap_series or len(vwap_series) < 2:
            return EvaluationResult(
                matched=False,
                trigger_type=TriggerType.INDICATOR_CROSS.value,
                trigger_price=latest_close,
                evaluation_message="VWAP series not available.",
            )

        v_curr, v_prev = vwap_series[-1], vwap_series[-2]
        p_curr, p_prev = latest_close, float(candles[-2].close)

        cross_dir = str(config.get("cross_direction", config.get("direction", "ABOVE"))).upper()
        matched = False
        if cross_dir in ["ABOVE", "BULLISH"]:
            matched = p_curr >= v_curr and p_prev < v_prev
        elif cross_dir in ["BELOW", "BEARISH"]:
            matched = p_curr <= v_curr and p_prev > v_prev

        conditions = {
            "vwap_current": v_curr,
            "price_current": p_curr,
            "price_prev": p_prev,
            "cross_direction": cross_dir,
        }

        if matched:
            return EvaluationResult(
                matched=True,
                trigger_type=TriggerType.INDICATOR_CROSS.value,
                trigger_price=latest_close,
                conditions_met=conditions,
                evaluation_message=f"Price {cross_dir} VWAP cross confirmed at {latest_close} (VWAP: {v_curr}).",
            )

        return EvaluationResult(
            matched=False,
            trigger_type=TriggerType.INDICATOR_CROSS.value,
            trigger_price=latest_close,
            conditions_met=conditions,
            evaluation_message=f"No VWAP cross detected (Price: {latest_close}, VWAP: {v_curr}).",
        )

    return EvaluationResult(
        matched=False,
        trigger_type=TriggerType.INDICATOR_CROSS.value,
        trigger_price=latest_close,
        evaluation_message=f"Unsupported indicator: '{indicator_name}'.",
    )


class SignalEvaluatorEngine:
    """
    Unified signal evaluator routing incoming bar data to the appropriate trigger rule evaluator.
    """

    @staticmethod
    def evaluate(
        trigger_type: TriggerType,
        threshold_config: Dict[str, Any],
        candles: List[CandleData],
        technicals: Optional[ProviderTechnicals] = None,
    ) -> EvaluationResult:
        start_time = time.perf_counter()
        t_type = TriggerType(trigger_type) if isinstance(trigger_type, str) else trigger_type

        if t_type == TriggerType.CANDLE_PATTERN:
            result = evaluate_candle_pattern(candles, threshold_config, technicals)
        elif t_type == TriggerType.PRICE_SPIKE:
            result = evaluate_price_spike(candles, threshold_config)
        elif t_type == TriggerType.VOLUME_SPIKE:
            result = evaluate_volume_spike(candles, threshold_config)
        elif t_type == TriggerType.SR_BREAK:
            result = evaluate_sr_break(candles, threshold_config)
        elif t_type == TriggerType.INDICATOR_CROSS:
            result = evaluate_indicator_cross(candles, threshold_config, technicals)
        else:
            result = EvaluationResult(
                matched=False,
                trigger_type=str(t_type),
                trigger_price=candles[-1].close if candles else 0.0,
                evaluation_message=f"Unknown trigger type: {t_type}",
            )

        result.latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        return result
