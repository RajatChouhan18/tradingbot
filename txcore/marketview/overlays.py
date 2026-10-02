"""
txcore.marketview.overlays
~~~~~~~~~~~~~~~~~~~~~~~~~~
Technical Overlays, Mathematical Indicators, and Candlestick Pattern Engine.
Provides vectorized computation of moving averages, momentum, volatility,
VIX regimes, and price action patterns aligned 1:1 with candlestick time-series.
"""

import logging
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timezone
import numpy as np
import pandas as pd

from txcore.marketview.models import CandleData, PatternMarker, ProviderTechnicals

logger = logging.getLogger("auratrade.marketview.overlays")


def candles_to_dataframe(candles: List[CandleData]) -> pd.DataFrame:
    """Converts list of CandleData models into a pandas DataFrame."""
    if not candles:
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

    records = [
        {
            "timestamp": c.timestamp,
            "open": c.open,
            "high": c.high,
            "low": c.low,
            "close": c.close,
            "volume": c.volume,
        }
        for c in candles
    ]
    df = pd.DataFrame(records)
    return df


def calculate_ema(series: pd.Series, span: int) -> List[Optional[float]]:
    """Vectorized Exponential Moving Average (EMA) with span."""
    if len(series) == 0:
        return []
    ema_series = series.ewm(span=max(1, span), adjust=False).mean()
    return [round(float(v), 4) if pd.notna(v) else None for v in ema_series]


def calculate_sma(series: pd.Series, window: int) -> List[Optional[float]]:
    """Vectorized Simple Moving Average (SMA)."""
    if len(series) == 0:
        return []
    sma_series = series.rolling(window=max(1, window), min_periods=1).mean()
    return [round(float(v), 4) if pd.notna(v) else None for v in sma_series]


def calculate_vwap(df: pd.DataFrame) -> List[Optional[float]]:
    """Vectorized Volume Weighted Average Price (VWAP)."""
    if df.empty or "volume" not in df.columns:
        return []
    typical_price = (df["high"] + df["low"] + df["close"]) / 3.0
    cum_vol_price = (typical_price * df["volume"]).cumsum()
    cum_vol = df["volume"].cumsum().replace(0.0, np.nan)
    vwap_series = (cum_vol_price / cum_vol).fillna(typical_price)
    return [round(float(v), 4) if pd.notna(v) else None for v in vwap_series]


def calculate_rsi(series: pd.Series, period: int = 14) -> List[Optional[float]]:
    """Wilder's smoothed Relative Strength Index (RSI 14)."""
    if len(series) < 2:
        return [50.0] * len(series)

    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=1, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=1, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi_series = (100.0 - (100.0 / (1.0 + rs))).fillna(50.0)
    return [round(float(v), 2) if pd.notna(v) else 50.0 for v in rsi_series]


def calculate_macd(
    series: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> Tuple[List[Optional[float]], List[Optional[float]], List[Optional[float]]]:
    """Vectorized Moving Average Convergence Divergence (MACD)."""
    if len(series) == 0:
        return [], [], []
    fast_ema = series.ewm(span=fast, adjust=False).mean()
    slow_ema = series.ewm(span=slow, adjust=False).mean()
    macd_line = fast_ema - slow_ema
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line

    return (
        [round(float(v), 4) if pd.notna(v) else None for v in macd_line],
        [round(float(v), 4) if pd.notna(v) else None for v in signal_line],
        [round(float(v), 4) if pd.notna(v) else None for v in histogram],
    )


def calculate_bollinger_bands(
    series: pd.Series,
    period: int = 20,
    num_std: float = 2.0,
) -> Tuple[List[Optional[float]], List[Optional[float]], List[Optional[float]]]:
    """Vectorized Bollinger Bands."""
    if len(series) == 0:
        return [], [], []
    middle = series.rolling(window=max(1, period), min_periods=1).mean()
    rolling_std = series.rolling(window=max(1, period), min_periods=1).std().fillna(0.0)
    upper = middle + (rolling_std * num_std)
    lower = middle - (rolling_std * num_std)

    return (
        [round(float(v), 4) if pd.notna(v) else None for v in upper],
        [round(float(v), 4) if pd.notna(v) else None for v in middle],
        [round(float(v), 4) if pd.notna(v) else None for v in lower],
    )


def calculate_atr(df: pd.DataFrame, period: int = 14) -> List[Optional[float]]:
    """Average True Range (ATR 14)."""
    if df.empty:
        return []
    high = df["high"]
    low = df["low"]
    prev_close = df["close"].shift(1).fillna(df["open"])

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr_series = tr.ewm(alpha=1.0 / period, min_periods=1, adjust=False).mean()
    return [round(float(v), 4) if pd.notna(v) else None for v in atr_series]


def classify_vix_regime(vix_value: Optional[float]) -> str:
    """Classifies Volatility Index (VIX) into institutional volatility regime."""
    if vix_value is None or vix_value <= 0:
        return "NORMAL_VOLATILITY"
    if vix_value < 13.0:
        return "LOW_VOLATILITY"
    elif vix_value < 18.0:
        return "NORMAL_VOLATILITY"
    elif vix_value < 24.0:
        return "ELEVATED_VOLATILITY"
    else:
        return "HIGH_VOLATILITY"


def detect_candlestick_patterns(df: pd.DataFrame) -> List[PatternMarker]:
    """Scans DataFrame for major single-bar and multi-bar price action patterns."""
    markers: List[PatternMarker] = []
    n = len(df)
    if n == 0:
        return markers

    for i in range(n):
        row = df.iloc[i]
        o, h, l, c = row["open"], row["high"], row["low"], row["close"]
        ts = row["timestamp"]
        total_range = h - l
        body = abs(c - o)
        if total_range == 0:
            continue

        upper_wick = h - max(o, c)
        lower_wick = min(o, c) - l
        is_bullish = c >= o

        # 1. Doji (Body <= 10% range)
        if body <= (0.10 * total_range):
            markers.append(
                PatternMarker(
                    index=i,
                    timestamp=ts,
                    pattern="DOJI",
                    sentiment="NEUTRAL",
                    description="Indecision candle with tiny body and balanced wicks.",
                )
            )

        # 2. Hammer (Lower wick >= 2x body, tiny upper wick)
        elif lower_wick >= 2.0 * body and upper_wick <= (0.25 * total_range) and is_bullish:
            markers.append(
                PatternMarker(
                    index=i,
                    timestamp=ts,
                    pattern="HAMMER",
                    sentiment="BULLISH",
                    description="Bullish reversal pin bar with long lower rejection wick.",
                )
            )

        # 3. Shooting Star (Upper wick >= 2x body, tiny lower wick)
        elif upper_wick >= 2.0 * body and lower_wick <= (0.25 * total_range) and not is_bullish:
            markers.append(
                PatternMarker(
                    index=i,
                    timestamp=ts,
                    pattern="SHOOTING_STAR",
                    sentiment="BEARISH",
                    description="Bearish reversal pin bar with long upper rejection wick.",
                )
            )

        # 4. Multi-bar patterns (requires i >= 1)
        if i >= 1:
            prev_row = df.iloc[i - 1]
            po, pc = prev_row["open"], prev_row["close"]
            prev_bearish = pc < po
            prev_bullish = pc > po

            # Bullish Engulfing
            if prev_bearish and is_bullish and o <= pc and c >= po:
                markers.append(
                    PatternMarker(
                        index=i,
                        timestamp=ts,
                        pattern="BULLISH_ENGULFING",
                        sentiment="BULLISH",
                        description="Bullish candle completely engulfs prior bearish body.",
                    )
                )

            # Bearish Engulfing
            elif prev_bullish and not is_bullish and o >= pc and c <= po:
                markers.append(
                    PatternMarker(
                        index=i,
                        timestamp=ts,
                        pattern="BEARISH_ENGULFING",
                        sentiment="BEARISH",
                        description="Bearish candle completely engulfs prior bullish body.",
                    )
                )

    return markers


def compute_market_technicals(
    candles: List[CandleData],
    symbol: str,
    timeframe: str = "5m",
    requested_overlays: Optional[List[str]] = None,
    vix_value: Optional[float] = None,
) -> ProviderTechnicals:
    """
    Computes all requested technical overlays and patterns for a given candlestick stream.
    """
    df = candles_to_dataframe(candles)
    if df.empty:
        return ProviderTechnicals(
            symbol=symbol.upper(),
            timeframe=timeframe.lower(),
            timestamp=datetime.now(timezone.utc),
            overlays={},
            patterns=[],
            vixRegime=classify_vix_regime(vix_value),
        )

    overlays: Dict[str, List[Optional[float]]] = {}
    req_set = set([o.upper() for o in requested_overlays]) if requested_overlays else None

    # Calculate Moving Averages
    if req_set is None or "EMA_9" in req_set or "ALL" in req_set:
        overlays["EMA_9"] = calculate_ema(df["close"], 9)
    if req_set is None or "EMA_21" in req_set or "ALL" in req_set:
        overlays["EMA_21"] = calculate_ema(df["close"], 21)
    if req_set is None or "EMA_50" in req_set or "ALL" in req_set:
        overlays["EMA_50"] = calculate_ema(df["close"], 50)
    if req_set is None or "EMA_200" in req_set or "ALL" in req_set:
        overlays["EMA_200"] = calculate_ema(df["close"], 200)
    if req_set is None or "SMA_20" in req_set or "ALL" in req_set:
        overlays["SMA_20"] = calculate_sma(df["close"], 20)

    # Calculate Volume & Volatility Overlays
    if req_set is None or "VWAP" in req_set or "ALL" in req_set:
        overlays["VWAP"] = calculate_vwap(df)
    if req_set is None or "ATR" in req_set or "ATR_14" in req_set or "ALL" in req_set:
        overlays["ATR_14"] = calculate_atr(df, 14)

    # Bollinger Bands
    if req_set is None or "BB" in req_set or "BOLLINGER" in req_set or "ALL" in req_set:
        bb_upper, bb_mid, bb_lower = calculate_bollinger_bands(df["close"], 20, 2.0)
        overlays["BB_UPPER"] = bb_upper
        overlays["BB_MIDDLE"] = bb_mid
        overlays["BB_LOWER"] = bb_lower

    # Momentum
    if req_set is None or "RSI" in req_set or "RSI_14" in req_set or "ALL" in req_set:
        overlays["RSI_14"] = calculate_rsi(df["close"], 14)
    if req_set is None or "MACD" in req_set or "ALL" in req_set:
        macd_line, signal_line, hist = calculate_macd(df["close"], 12, 26, 9)
        overlays["MACD_LINE"] = macd_line
        overlays["MACD_SIGNAL"] = signal_line
        overlays["MACD_HIST"] = hist

    # Candlestick Patterns
    patterns = []
    if req_set is None or "PATTERNS" in req_set or "ALL" in req_set:
        patterns = detect_candlestick_patterns(df)

    vix_regime = classify_vix_regime(vix_value)
    latest_ts = df["timestamp"].iloc[-1] if not df.empty else datetime.now(timezone.utc)

    return ProviderTechnicals(
        symbol=symbol.upper(),
        timeframe=timeframe.lower(),
        timestamp=latest_ts,
        overlays=overlays,
        patterns=patterns,
        vixRegime=vix_regime,
    )
