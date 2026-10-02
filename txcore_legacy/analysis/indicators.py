"""
txcore.analysis.indicators
~~~~~~~~~~~~~~~~~~~~~~~~~~
Pure mathematical indicator calculations and trend analysis functions operating on DataFrames.
Market-agnostic: works across Forex, Equities, Commodities, and Crypto.
"""

from typing import Optional, Dict, Any, Tuple
import pandas as pd
import numpy as np

from txcore.analysis.levels import key_levels


def calculate_ema(series: pd.Series, span: int) -> pd.Series:
    """Calculates Exponential Moving Average (EMA) for a price series."""
    return series.ewm(span=max(1, span), adjust=False).mean()


def calculate_sma(series: pd.Series, window: int) -> pd.Series:
    """Calculates Simple Moving Average (SMA) for a price series."""
    return series.rolling(window=max(1, window), min_periods=1).mean()


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculates Relative Strength Index (RSI) using standard Wilder's smoothing.
    Returns values between 0.0 and 100.0.
    """
    if len(series) < 2:
        return pd.Series(50.0, index=series.index)

    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    # Wilder's exponential smoothing (alpha = 1 / period)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.fillna(50.0)


def calculate_macd(
    series: pd.Series,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculates MACD (Moving Average Convergence Divergence).
    Returns (macd_line, signal_line, histogram).
    """
    fast_ema = calculate_ema(series, fast_period)
    slow_ema = calculate_ema(series, slow_period)
    macd_line = fast_ema - slow_ema
    signal_line = calculate_ema(macd_line, signal_period)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def calculate_bollinger_bands(
    series: pd.Series,
    period: int = 20,
    num_std: float = 2.0,
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculates Bollinger Bands.
    Returns (upper_band, middle_band, lower_band).
    """
    middle_band = calculate_sma(series, period)
    rolling_std = series.rolling(window=max(1, period), min_periods=1).std().fillna(0.0)
    upper_band = middle_band + (rolling_std * num_std)
    lower_band = middle_band - (rolling_std * num_std)
    return upper_band, middle_band, lower_band


def calculate_vwap(df: pd.DataFrame) -> pd.Series:
    """
    Calculates Volume Weighted Average Price (VWAP).
    Requires 'high', 'low', 'close', and 'volume' columns in df.
    """
    if df.empty or "volume" not in df.columns:
        return df["close"] if "close" in df.columns else pd.Series(dtype=float)

    typical_price = (df["high"] + df["low"] + df["close"]) / 3.0
    cum_vol_price = (typical_price * df["volume"]).cumsum()
    cum_vol = df["volume"].cumsum().replace(0.0, np.nan)
    vwap = cum_vol_price / cum_vol
    return vwap.fillna(typical_price)


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calculates Average True Range (ATR) using Wilder's smoothing.
    TR = max(High - Low, abs(High - PrevClose), abs(Low - PrevClose))
    Pure mathematical function operating vectorially on DataFrame columns.
    """
    if df is None or df.empty:
        return pd.Series(dtype=float)
    if len(df) < 2 or "high" not in df.columns or "low" not in df.columns or "close" not in df.columns:
        return pd.Series(0.0, index=df.index)

    high = df["high"].astype(float)
    low = df["low"].astype(float)
    prev_close = df["close"].astype(float).shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    # First bar TR is simply high - low
    tr.iloc[0] = high.iloc[0] - low.iloc[0]

    # Wilder's exponential smoothing: alpha = 1 / period
    effective_period = max(1, period)
    atr = tr.ewm(alpha=1.0 / effective_period, min_periods=min(len(df), effective_period), adjust=False).mean()
    return atr.bfill().fillna(tr)


def analyze_trend(
    df: pd.DataFrame,
    symbol: str = "",
    timeframe: str = "5m",
    lookback_bars: int = 100,
) -> Dict[str, Any]:
    """
    Analyzes directional trend structure, dynamic key levels, and moving average momentum
    for any asset class (Forex, Equities, Crypto, Commodities).

    Returns structured trend dictionary with:
      - symbol, timeframe, current_price
      - trend classification (STRONG_UPTREND, MODERATE_UPTREND, STRONG_DOWNTREND, MODERATE_DOWNTREND, SIDEWAYS / CONSOLIDATION)
      - ema20, ema50
      - support, resistance levels and percentage distances
      - window_change_pct, summary text
    """
    if df is None or len(df) < 5:
        return {
            "symbol": symbol.upper(),
            "timeframe": timeframe,
            "trend": "INSUFFICIENT_DATA",
            "summary": "Less than 5 bars available for trend analysis",
        }

    closes = df["close"]
    curr_price = float(closes.iloc[-1])
    first_price = float(closes.iloc[0])

    # Rolling EMAs (reuse precalculated columns if present to save computation)
    if "ema_20" in df.columns:
        ema20 = float(df["ema_20"].iloc[-1])
    else:
        ema20_series = calculate_ema(closes, min(20, len(df)))
        ema20 = float(ema20_series.iloc[-1])

    if "ema_50" in df.columns:
        ema50 = float(df["ema_50"].iloc[-1])
    else:
        ema50_series = calculate_ema(closes, min(50, len(df)))
        ema50 = float(ema50_series.iloc[-1])

    # Dynamic Support & Resistance levels from swing points
    supp, res = key_levels(df, len(df) - 1, lookback=min(20, len(df)))

    # Trend Determination
    if curr_price > ema20 > ema50:
        trend = "STRONG_UPTREND"
    elif curr_price > ema20:
        trend = "MODERATE_UPTREND"
    elif curr_price < ema20 < ema50:
        trend = "STRONG_DOWNTREND"
    elif curr_price < ema20:
        trend = "MODERATE_DOWNTREND"
    else:
        trend = "SIDEWAYS / CONSOLIDATION"

    dist_to_supp = ((curr_price - supp) / curr_price) * 100.0 if curr_price > 0 else 0.0
    dist_to_res = ((res - curr_price) / curr_price) * 100.0 if curr_price > 0 else 0.0
    pct_change_window = ((curr_price - first_price) / first_price) * 100.0 if first_price > 0 else 0.0

    return {
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "current_price": round(curr_price, 2),
        "trend": trend,
        "ema20": round(ema20, 2),
        "ema50": round(ema50, 2),
        "support": round(supp, 2),
        "resistance": round(res, 2),
        "dist_to_support_pct": round(dist_to_supp, 2),
        "dist_to_resistance_pct": round(dist_to_res, 2),
        "window_change_pct": round(pct_change_window, 2),
        "summary": (
            f"[{symbol.upper()} | {timeframe}] Price: {curr_price:.2f} | Trend: {trend} | "
            f"Support: {supp:.2f} (-{dist_to_supp:.2f}%) | Resistance: {res:.2f} (+{dist_to_res:.2f}%)"
        ),
    }
