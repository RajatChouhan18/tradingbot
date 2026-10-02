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


def calculate_supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> Tuple[List[Optional[float]], List[str]]:
    """Supertrend indicator (Period 10, Multiplier 3.0)."""
    if df.empty:
        return [], []
    high = df["high"].values
    low = df["low"].values
    close = df["close"].values
    n = len(df)
    atr_list = calculate_atr(df, period)
    atr = np.array([v if v is not None else 0.0 for v in atr_list])
    hl2 = (high + low) / 2.0
    basic_upper = hl2 + (multiplier * atr)
    basic_lower = hl2 - (multiplier * atr)
    final_upper = np.zeros(n)
    final_lower = np.zeros(n)
    supertrend = np.zeros(n)
    direction: List[str] = ["BEARISH"] * n

    for i in range(n):
        if i == 0:
            final_upper[i] = basic_upper[i]
            final_lower[i] = basic_lower[i]
            supertrend[i] = basic_upper[i]
            direction[i] = "BEARISH"
            continue
        if basic_upper[i] < final_upper[i - 1] or close[i - 1] > final_upper[i - 1]:
            final_upper[i] = basic_upper[i]
        else:
            final_upper[i] = final_upper[i - 1]

        if basic_lower[i] > final_lower[i - 1] or close[i - 1] < final_lower[i - 1]:
            final_lower[i] = basic_lower[i]
        else:
            final_lower[i] = final_lower[i - 1]

        if supertrend[i - 1] == final_upper[i - 1]:
            if close[i] > final_upper[i]:
                supertrend[i] = final_lower[i]
                direction[i] = "BULLISH"
            else:
                supertrend[i] = final_upper[i]
                direction[i] = "BEARISH"
        else:
            if close[i] < final_lower[i]:
                supertrend[i] = final_upper[i]
                direction[i] = "BEARISH"
            else:
                supertrend[i] = final_lower[i]
                direction[i] = "BULLISH"

    return ([round(float(v), 4) for v in supertrend], direction)


def calculate_keltner_channels(df: pd.DataFrame, ema_period: int = 20, atr_period: int = 10, multiplier: float = 2.0) -> Tuple[List[Optional[float]], List[Optional[float]], List[Optional[float]]]:
    """Keltner Channels (EMA 20, ATR 10, Multiplier 2.0)."""
    if df.empty:
        return [], [], []
    middle = calculate_ema(df["close"], ema_period)
    atr = calculate_atr(df, atr_period)
    upper = []
    lower = []
    for m, a in zip(middle, atr):
        if m is not None and a is not None:
            upper.append(round(m + (multiplier * a), 4))
            lower.append(round(m - (multiplier * a), 4))
        else:
            upper.append(None)
            lower.append(None)
    return upper, middle, lower


def calculate_donchian_channels(df: pd.DataFrame, period: int = 20) -> Tuple[List[Optional[float]], List[Optional[float]], List[Optional[float]]]:
    """Donchian Channels (20-period High/Low Breakout Bands)."""
    if df.empty:
        return [], [], []
    upper_s = df["high"].rolling(window=max(1, period), min_periods=1).max()
    lower_s = df["low"].rolling(window=max(1, period), min_periods=1).min()
    middle_s = (upper_s + lower_s) / 2.0
    return (
        [round(float(v), 4) if pd.notna(v) else None for v in upper_s],
        [round(float(v), 4) if pd.notna(v) else None for v in middle_s],
        [round(float(v), 4) if pd.notna(v) else None for v in lower_s],
    )


def calculate_parabolic_sar(df: pd.DataFrame, step: float = 0.02, max_step: float = 0.20) -> List[Optional[float]]:
    """Wilder's Parabolic SAR (Step 0.02, Max 0.20)."""
    if df.empty:
        return []
    n = len(df)
    if n < 2:
        return [round(float(df["low"].iloc[0]), 4)] * n
    high = df["high"].values
    low = df["low"].values
    psar = np.zeros(n)
    is_bull = high[1] >= high[0]
    af = step
    ep = high[0] if is_bull else low[0]
    psar[0] = low[0] if is_bull else high[0]

    for i in range(1, n):
        prev_psar = psar[i - 1]
        if is_bull:
            cur_psar = prev_psar + af * (ep - prev_psar)
            cur_psar = min(cur_psar, low[i - 1], low[max(0, i - 2)])
            if low[i] < cur_psar:
                is_bull = False
                cur_psar = ep
                ep = low[i]
                af = step
            else:
                if high[i] > ep:
                    ep = high[i]
                    af = min(af + step, max_step)
        else:
            cur_psar = prev_psar + af * (ep - prev_psar)
            cur_psar = max(cur_psar, high[i - 1], high[max(0, i - 2)])
            if high[i] > cur_psar:
                is_bull = True
                cur_psar = ep
                ep = high[i]
                af = step
            else:
                if low[i] < ep:
                    ep = low[i]
                    af = min(af + step, max_step)
        psar[i] = cur_psar

    return [round(float(v), 4) for v in psar]


def calculate_pivot_points(df: pd.DataFrame) -> Dict[str, List[Optional[float]]]:
    """Standard Classic Daily Pivot Points (P, R1, R2, S1, S2)."""
    if df.empty:
        return {"PIVOT_P": [], "PIVOT_R1": [], "PIVOT_R2": [], "PIVOT_S1": [], "PIVOT_S2": []}
    h = df["high"]
    l = df["low"]
    c = df["close"]
    p = (h + l + c) / 3.0
    r1 = (2.0 * p) - l
    s1 = (2.0 * p) - h
    r2 = p + (h - l)
    s2 = p - (h - l)
    return {
        "PIVOT_P": [round(float(v), 4) if pd.notna(v) else None for v in p],
        "PIVOT_R1": [round(float(v), 4) if pd.notna(v) else None for v in r1],
        "PIVOT_R2": [round(float(v), 4) if pd.notna(v) else None for v in r2],
        "PIVOT_S1": [round(float(v), 4) if pd.notna(v) else None for v in s1],
        "PIVOT_S2": [round(float(v), 4) if pd.notna(v) else None for v in s2],
    }


def calculate_zigzag(df: pd.DataFrame, depth: int = 10) -> List[Optional[float]]:
    """ZigZag Swing Pivots connector."""
    if df.empty or len(df) < depth:
        return [round(float(c), 4) for c in df["close"]] if not df.empty else []
    high = df["high"].values
    low = df["low"].values
    n = len(df)
    pivots: List[Optional[float]] = [None] * n
    pivots[0] = low[0]
    trend = 1

    for i in range(depth, n):
        window_high = np.max(high[i - depth:i + 1])
        window_low = np.min(low[i - depth:i + 1])
        if trend == 1:
            if high[i] == window_high:
                pivots[i] = round(float(high[i]), 4)
                trend = -1
        else:
            if low[i] == window_low:
                pivots[i] = round(float(low[i]), 4)
                trend = 1

    s = pd.Series(pivots).interpolate(method="linear").bfill().ffill()
    return [round(float(v), 4) if pd.notna(v) else None for v in s]


def calculate_ichimoku(df: pd.DataFrame, tenkan_p: int = 9, kijun_p: int = 26, senkou_b_p: int = 52) -> Dict[str, List[Optional[float]]]:
    """Ichimoku Kinko Hyo Cloud System (Tenkan, Kijun, Senkou A, Senkou B)."""
    if df.empty:
        return {"ICHIMOKU_TENKAN": [], "ICHIMOKU_KIJUN": [], "ICHIMOKU_SPAN_A": [], "ICHIMOKU_SPAN_B": []}
    tenkan = (df["high"].rolling(tenkan_p, min_periods=1).max() + df["low"].rolling(tenkan_p, min_periods=1).min()) / 2.0
    kijun = (df["high"].rolling(kijun_p, min_periods=1).max() + df["low"].rolling(kijun_p, min_periods=1).min()) / 2.0
    span_a = (tenkan + kijun) / 2.0
    span_b = (df["high"].rolling(senkou_b_p, min_periods=1).max() + df["low"].rolling(senkou_b_p, min_periods=1).min()) / 2.0
    return {
        "ICHIMOKU_TENKAN": [round(float(v), 4) if pd.notna(v) else None for v in tenkan],
        "ICHIMOKU_KIJUN": [round(float(v), 4) if pd.notna(v) else None for v in kijun],
        "ICHIMOKU_SPAN_A": [round(float(v), 4) if pd.notna(v) else None for v in span_a],
        "ICHIMOKU_SPAN_B": [round(float(v), 4) if pd.notna(v) else None for v in span_b],
    }


def calculate_stochastic_rsi(df: pd.DataFrame, rsi_period: int = 14, stoch_period: int = 14, k_period: int = 3, d_period: int = 3) -> Tuple[List[Optional[float]], List[Optional[float]]]:
    """Stochastic RSI (%K, %D with 14/14/3/3 parameters)."""
    if df.empty:
        return [], []
    rsi_vals = calculate_rsi(df["close"], rsi_period)
    rsi_s = pd.Series([v if v is not None else 50.0 for v in rsi_vals])
    min_rsi = rsi_s.rolling(stoch_period, min_periods=1).min()
    max_rsi = rsi_s.rolling(stoch_period, min_periods=1).max()
    denom = (max_rsi - min_rsi).replace(0.0, np.nan)
    stoch_rsi = (((rsi_s - min_rsi) / denom) * 100.0).fillna(50.0)
    k_line = stoch_rsi.rolling(k_period, min_periods=1).mean()
    d_line = k_line.rolling(d_period, min_periods=1).mean()
    return (
        [round(float(v), 2) if pd.notna(v) else 50.0 for v in k_line],
        [round(float(v), 2) if pd.notna(v) else 50.0 for v in d_line],
    )


def calculate_adx_dmi(df: pd.DataFrame, period: int = 14) -> Tuple[List[Optional[float]], List[Optional[float]], List[Optional[float]]]:
    """Average Directional Index (ADX 14) & Directional Movement (+DI, -DI)."""
    if df.empty:
        return [], [], []
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1).fillna(df["open"])
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    tr_smoothed = tr.ewm(alpha=1.0 / period, min_periods=1, adjust=False).mean().replace(0.0, np.nan)
    plus_dm_smoothed = pd.Series(plus_dm).ewm(alpha=1.0 / period, min_periods=1, adjust=False).mean()
    minus_dm_smoothed = pd.Series(minus_dm).ewm(alpha=1.0 / period, min_periods=1, adjust=False).mean()
    plus_di = (plus_dm_smoothed / tr_smoothed) * 100.0
    minus_di = (minus_dm_smoothed / tr_smoothed) * 100.0
    dx_denom = (plus_di + minus_di).replace(0.0, np.nan)
    dx = ((plus_di - minus_di).abs() / dx_denom) * 100.0
    adx = dx.ewm(alpha=1.0 / period, min_periods=1, adjust=False).mean().fillna(20.0)
    return (
        [round(float(v), 2) if pd.notna(v) else 20.0 for v in adx],
        [round(float(v), 2) if pd.notna(v) else 25.0 for v in plus_di],
        [round(float(v), 2) if pd.notna(v) else 25.0 for v in minus_di],
    )


def calculate_obv(df: pd.DataFrame) -> List[Optional[float]]:
    """On-Balance Volume (OBV)."""
    if df.empty or "volume" not in df.columns:
        return []
    close = df["close"]
    vol = df["volume"]
    change = close.diff().fillna(0.0)
    direction = np.where(change > 0, 1.0, np.where(change < 0, -1.0, 0.0))
    obv_series = (direction * vol).cumsum()
    return [round(float(v), 2) if pd.notna(v) else 0.0 for v in obv_series]


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
    """
    Institutional candlestick pattern recognition engine implementing standard
    OHLC mathematical geometry across single-bar, 2-bar, and 3-bar formations.
    """
    markers: List[PatternMarker] = []
    n = len(df)
    if n == 0:
        return markers

    # Compute rolling average body size for adaptive scale thresholding
    body_series = (df["close"] - df["open"]).abs()
    avg_body = body_series.rolling(14, min_periods=1).mean().values

    for i in range(n):
        row = df.iloc[i]
        o, h, l, c = float(row["open"]), float(row["high"]), float(row["low"]), float(row["close"])
        ts = row["timestamp"]
        total_range = h - l
        if total_range <= 1e-6:
            continue

        body = abs(c - o)
        upper_wick = h - max(o, c)
        lower_wick = min(o, c) - l
        is_bullish = c >= o
        ref_body = avg_body[i] if avg_body[i] > 0 else (total_range * 0.5)

        # -------------------------------------------------------------
        # 1. DOJI VARIETIES (Body <= 10% of total bar range)
        # -------------------------------------------------------------
        if body <= 0.10 * total_range:
            # 1a. Dragonfly Doji (Long lower shadow >= 60% range, negligible upper shadow <= 12% range)
            if lower_wick >= 0.60 * total_range and upper_wick <= 0.12 * total_range:
                markers.append(PatternMarker(
                    index=i, timestamp=ts, pattern="DRAGONFLY_DOJI", sentiment="BULLISH",
                    description="Bullish Dragonfly Doji: Open and close near high with massive lower wick rejection."
                ))
            # 1b. Gravestone Doji (Long upper shadow >= 60% range, negligible lower shadow <= 12% range)
            elif upper_wick >= 0.60 * total_range and lower_wick <= 0.12 * total_range:
                markers.append(PatternMarker(
                    index=i, timestamp=ts, pattern="GRAVESTONE_DOJI", sentiment="BEARISH",
                    description="Bearish Gravestone Doji: Open and close near low with massive upper wick rejection."
                ))
            # 1c. Standard Doji (Balanced shadows, indecision)
            else:
                markers.append(PatternMarker(
                    index=i, timestamp=ts, pattern="DOJI", sentiment="NEUTRAL",
                    description="Standard Doji: Open and close virtually identical, signaling market equilibrium/indecision."
                ))

        # -------------------------------------------------------------
        # 2. MARUBOZU (Full solid body >= 75% range, wicks <= 12% range)
        # -------------------------------------------------------------
        elif body >= 0.75 * total_range and body >= 0.70 * ref_body:
            if is_bullish and upper_wick <= 0.12 * total_range and lower_wick <= 0.12 * total_range:
                markers.append(PatternMarker(
                    index=i, timestamp=ts, pattern="MARUBOZU_BULLISH", sentiment="BULLISH",
                    description="Bullish Marubozu: Strong unidirectional buying pressure with minimal wicks."
                ))
            elif not is_bullish and upper_wick <= 0.12 * total_range and lower_wick <= 0.12 * total_range:
                markers.append(PatternMarker(
                    index=i, timestamp=ts, pattern="MARUBOZU_BEARISH", sentiment="BEARISH",
                    description="Bearish Marubozu: Strong unidirectional selling pressure with minimal wicks."
                ))

        # -------------------------------------------------------------
        # 3. PIN BARS: HAMMER & HANGING MAN (Lower shadow >= 2x body)
        # -------------------------------------------------------------
        elif lower_wick >= 2.0 * body and upper_wick <= 0.25 * total_range and body >= 0.08 * total_range:
            is_downtrend = i >= 2 and (df["close"].iloc[i - 1] < df["close"].iloc[i - 2])
            if is_downtrend or is_bullish:
                markers.append(PatternMarker(
                    index=i, timestamp=ts, pattern="HAMMER", sentiment="BULLISH",
                    description="Hammer: Bullish pin bar with lower rejection wick >= 2x body size."
                ))
            else:
                markers.append(PatternMarker(
                    index=i, timestamp=ts, pattern="HANGING_MAN", sentiment="BEARISH",
                    description="Hanging Man: Bearish warning pin bar at local highs with extended lower shadow."
                ))

        # -------------------------------------------------------------
        # 4. INVERTED PIN BARS: INVERTED HAMMER & SHOOTING STAR (Upper shadow >= 2x body)
        # -------------------------------------------------------------
        elif upper_wick >= 2.0 * body and lower_wick <= 0.25 * total_range and body >= 0.08 * total_range:
            is_uptrend = i >= 2 and (df["close"].iloc[i - 1] > df["close"].iloc[i - 2])
            if is_uptrend or not is_bullish:
                markers.append(PatternMarker(
                    index=i, timestamp=ts, pattern="SHOOTING_STAR", sentiment="BEARISH",
                    description="Shooting Star: Bearish rejection pin bar with upper shadow >= 2x body size."
                ))
            else:
                markers.append(PatternMarker(
                    index=i, timestamp=ts, pattern="INVERTED_HAMMER", sentiment="BULLISH",
                    description="Inverted Hammer: Bullish reversal pin bar with strong upper wick buying attempt."
                ))

        # -------------------------------------------------------------
        # 5. TWO-BAR PATTERNS (Requires i >= 1)
        # -------------------------------------------------------------
        if i >= 1:
            prev_row = df.iloc[i - 1]
            po, ph, pl, pc = float(prev_row["open"]), float(prev_row["high"]), float(prev_row["low"]), float(prev_row["close"])
            prev_body = abs(pc - po)
            prev_bearish = pc < po
            prev_bullish = pc > po

            # 5a. Bullish Engulfing
            if prev_bearish and is_bullish:
                if (o <= pc * 1.002 or o <= po) and c >= po and body >= prev_body:
                    markers.append(PatternMarker(
                        index=i, timestamp=ts, pattern="ENGULFING_BULLISH", sentiment="BULLISH",
                        description="Bullish Engulfing: Green candle body completely covers prior red body."
                    ))

            # 5b. Bearish Engulfing
            elif prev_bullish and not is_bullish:
                if (o >= pc * 0.998 or o >= po) and c <= po and body >= prev_body:
                    markers.append(PatternMarker(
                        index=i, timestamp=ts, pattern="ENGULFING_BEARISH", sentiment="BEARISH",
                        description="Bearish Engulfing: Red candle body completely covers prior green body."
                    ))

            # 5c. Bullish Harami (Inside bar: Prior large red body contains current small green body)
            if prev_bearish and is_bullish and prev_body >= 0.4 * (ph - pl):
                if o >= pc and c <= po and body <= 0.65 * prev_body:
                    markers.append(PatternMarker(
                        index=i, timestamp=ts, pattern="HARAMI_BULLISH", sentiment="BULLISH",
                        description="Bullish Harami: Small green inside bar contained within prior large red candle."
                    ))

            # 5d. Bearish Harami (Inside bar: Prior large green body contains current small red body)
            elif prev_bullish and not is_bullish and prev_body >= 0.4 * (ph - pl):
                if o <= pc and c >= po and body <= 0.65 * prev_body:
                    markers.append(PatternMarker(
                        index=i, timestamp=ts, pattern="HARAMI_BEARISH", sentiment="BEARISH",
                        description="Bearish Harami: Small red inside bar contained within prior large green candle."
                    ))

            # 5e. Piercing Line (Prior red candle, current opens low and penetrates > 50% into prior body)
            if prev_bearish and is_bullish and prev_body >= 0.35 * (ph - pl):
                mid_prev = (po + pc) / 2.0
                if o <= pc and c > mid_prev and c < po:
                    markers.append(PatternMarker(
                        index=i, timestamp=ts, pattern="PIERCING_LINE", sentiment="BULLISH",
                        description="Piercing Line: Bullish penetration closing above 50% midpoint of prior red candle."
                    ))

            # 5f. Dark Cloud Cover (Prior green candle, current opens high and penetrates > 50% into prior body)
            elif prev_bullish and not is_bullish and prev_body >= 0.35 * (ph - pl):
                mid_prev = (po + pc) / 2.0
                if o >= pc and c < mid_prev and c > po:
                    markers.append(PatternMarker(
                        index=i, timestamp=ts, pattern="DARK_CLOUD_COVER", sentiment="BEARISH",
                        description="Dark Cloud Cover: Bearish penetration closing below 50% midpoint of prior green candle."
                    ))

        # -------------------------------------------------------------
        # 6. THREE-BAR PATTERNS (Requires i >= 2)
        # -------------------------------------------------------------
        if i >= 2:
            p2_row = df.iloc[i - 2]
            p1_row = df.iloc[i - 1]
            p2_o, p2_c = float(p2_row["open"]), float(p2_row["close"])
            p1_o, p1_c = float(p1_row["open"]), float(p1_row["close"])
            p2_body = abs(p2_c - p2_o)
            p1_body = abs(p1_c - p1_o)

            # 6a. Morning Star: Tall Bearish (C1) + Small Star/Doji (C2) + Strong Bullish (C3) > 50% of C1
            if p2_c < p2_o and is_bullish:
                if p1_body <= 0.45 * p2_body and body >= 0.45 * p2_body:
                    mid_p2 = (p2_o + p2_c) / 2.0
                    if c >= mid_p2:
                        markers.append(PatternMarker(
                            index=i, timestamp=ts, pattern="MORNING_STAR", sentiment="BULLISH",
                            description="Morning Star: 3-bar bullish reversal bottoming pattern."
                        ))

            # 6b. Evening Star: Tall Bullish (C1) + Small Star/Doji (C2) + Strong Bearish (C3) < 50% of C1
            elif p2_c > p2_o and not is_bullish:
                if p1_body <= 0.45 * p2_body and body >= 0.45 * p2_body:
                    mid_p2 = (p2_o + p2_c) / 2.0
                    if c <= mid_p2:
                        markers.append(PatternMarker(
                            index=i, timestamp=ts, pattern="EVENING_STAR", sentiment="BEARISH",
                            description="Evening Star: 3-bar bearish reversal topping pattern."
                        ))

    return markers


def compute_market_technicals(
    candles: List[CandleData],
    symbol: str,
    timeframe: str = "5m",
    requested_overlays: Optional[List[str]] = None,
    requested_indicators: Optional[List[str]] = None,
    vix_value: Optional[float] = None,
) -> ProviderTechnicals:
    """
    Computes all requested technical indicators/overlays and candles/patterns for a given candlestick stream.
    """
    df = candles_to_dataframe(candles)
    if df.empty:
        return ProviderTechnicals(
            symbol=symbol.upper(),
            timeframe=timeframe.lower(),
            timestamp=datetime.now(timezone.utc),
            indicators={},
            overlays={},
            candles=[],
            patterns=[],
            vixRegime=classify_vix_regime(vix_value),
        )

    indicators: Dict[str, List[Optional[float]]] = {}

    # 1. Moving Averages
    indicators["EMA_9"] = calculate_ema(df["close"], 9)
    indicators["EMA_21"] = calculate_ema(df["close"], 21)
    indicators["EMA_50"] = calculate_ema(df["close"], 50)
    indicators["EMA_200"] = calculate_ema(df["close"], 200)
    indicators["SMA_20"] = calculate_sma(df["close"], 20)
    indicators["SMA_50"] = calculate_sma(df["close"], 50)
    indicators["SMA_200"] = calculate_sma(df["close"], 200)

    # 2. Volume & Volatility Indicators
    indicators["VWAP"] = calculate_vwap(df)
    indicators["ATR_14"] = calculate_atr(df, 14)
    indicators["ATR"] = indicators["ATR_14"]

    # 3. Bollinger Bands
    bb_upper, bb_mid, bb_lower = calculate_bollinger_bands(df["close"], 20, 2.0)
    indicators["BB_UPPER"] = bb_upper
    indicators["BB_MIDDLE"] = bb_mid
    indicators["BB_LOWER"] = bb_lower

    # 4. Supertrend
    st_vals, st_dirs = calculate_supertrend(df, 10, 3.0)
    indicators["SUPERTREND"] = st_vals
    indicators["SUPERTREND_DIRECTION"] = [1.0 if d == "BULLISH" else (-1.0 if d == "BEARISH" else 0.0) for d in st_dirs]

    # 5. Keltner Channels
    k_upper, k_mid, k_lower = calculate_keltner_channels(df, 20, 10, 2.0)
    indicators["KELTNER_UPPER"] = k_upper
    indicators["KELTNER_MIDDLE"] = k_mid
    indicators["KELTNER_LOWER"] = k_lower

    # 6. Donchian Channels
    d_upper, d_mid, d_lower = calculate_donchian_channels(df, 20)
    indicators["DONCHIAN_UPPER"] = d_upper
    indicators["DONCHIAN_MIDDLE"] = d_mid
    indicators["DONCHIAN_LOWER"] = d_lower

    # 7. Parabolic SAR
    indicators["PSAR"] = calculate_parabolic_sar(df, 0.02, 0.20)

    # 8. Pivot Points
    pivots = calculate_pivot_points(df)
    indicators.update(pivots)

    # 9. ZigZag
    indicators["ZIGZAG"] = calculate_zigzag(df, 10)

    # 10. Ichimoku Cloud
    ichimoku = calculate_ichimoku(df, 9, 26, 52)
    indicators.update(ichimoku)

    # 11. Momentum & Oscillators
    indicators["RSI_14"] = calculate_rsi(df["close"], 14)
    indicators["RSI"] = indicators["RSI_14"]

    macd_line, signal_line, hist = calculate_macd(df["close"], 12, 26, 9)
    indicators["MACD_LINE"] = macd_line
    indicators["MACD_SIGNAL"] = signal_line
    indicators["MACD_HIST"] = hist

    stoch_k, stoch_d = calculate_stochastic_rsi(df, 14, 14, 3, 3)
    indicators["STOCH_RSI_K"] = stoch_k
    indicators["STOCH_RSI_D"] = stoch_d

    adx, p_di, m_di = calculate_adx_dmi(df, 14)
    indicators["ADX_14"] = adx
    indicators["ADX"] = adx
    indicators["PLUS_DI_14"] = p_di
    indicators["MINUS_DI_14"] = m_di

    indicators["OBV"] = calculate_obv(df)

    # 12. Candlestick Recognition Patterns
    candles_patterns = detect_candlestick_patterns(df)

    vix_regime = classify_vix_regime(vix_value)
    latest_ts = df["timestamp"].iloc[-1] if not df.empty else datetime.now(timezone.utc)

    return ProviderTechnicals(
        symbol=symbol.upper(),
        timeframe=timeframe.lower(),
        timestamp=latest_ts,
        indicators=indicators,
        overlays=indicators,
        candles=candles_patterns,
        patterns=candles_patterns,
        vixRegime=vix_regime,
    )
