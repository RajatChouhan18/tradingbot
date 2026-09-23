"""
txcore.execution.file_logger
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Independent file loggers for trade signals and provider market data.
Anchored to project workspace with UTF-8 encoding and timestamp formatting.
"""

import os
from datetime import datetime, timezone
from typing import Optional, Union
import pandas as pd

# Anchor default logs to workspace root
WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_SIGNALS_LOG = os.path.join(WORKSPACE_DIR, "signals_history.log")
DEFAULT_MARKET_DATA_LOG = os.path.join(WORKSPACE_DIR, "tv_market_data.log")


def log_signal_to_file(content: str, filename: Optional[str] = None) -> str:
    """
    Appends signal alerts with UTC and Local timestamps to the log file.
    """
    if filename is None:
        filename = DEFAULT_SIGNALS_LOG

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    now_local = datetime.now().strftime("%H:%M:%S Local")
    entry = (
        "================================================================================\n"
        f"🕒 LOG TIMESTAMP: {now_utc} ({now_local}) | TIMEFRAME: 1-Minute\n"
        "--------------------------------------------------------------------------------\n"
        f"{content}\n"
        "================================================================================\n\n"
    )

    with open(filename, "a", encoding="utf-8") as f:
        f.write(entry)
    print(f"💾 [LOGGED TO FILE] Signal output appended to {filename}")
    return filename


def log_market_data_to_file(
    symbol_or_content: Union[str, Any],
    df: Optional[pd.DataFrame] = None,
    filename: Optional[str] = None,
    provider_name: str = "TRADINGVIEW (FX_IDC)",
) -> str:
    """
    Appends recent market data rows to the market data log file.
    """
    if filename is None:
        filename = DEFAULT_MARKET_DATA_LOG

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    now_local = datetime.now().strftime("%H:%M:%S Local")

    if df is not None and isinstance(df, pd.DataFrame) and not df.empty:
        symbol = str(symbol_or_content)
        last_closed = df.iloc[-2] if len(df) >= 2 else df.iloc[-1]
        forming = df.iloc[-1]

        # Recent closed bars summary
        recent_bars = []
        recent_slice = df.iloc[-4:-1] if len(df) >= 4 else df.iloc[:-1]
        for _, row in recent_slice.iterrows():
            t_str = str(row["time"])
            recent_bars.append(
                f"   • {t_str} | O: {row['open']:.5f} | H: {row['high']:.5f} | L: {row['low']:.5f} | C: {row['close']:.5f}"
            )
        recent_text = "\n".join(recent_bars) if recent_bars else "   (No prior bars)"

        content = (
            f"💱 PAIR: {symbol} | 📡 SOURCE: {provider_name}\n"
            f"📊 TOTAL BARS: {len(df)}\n\n"
            f"🕯 LATEST CLOSED BAR:\n"
            f"   Time:  {last_closed['time']}\n"
            f"   Open:  {last_closed['open']:.5f}\n"
            f"   High:  {last_closed['high']:.5f}\n"
            f"   Low:   {last_closed['low']:.5f}\n"
            f"   Close: {last_closed['close']:.5f}\n\n"
            f"⏳ IN-PROGRESS (FORMING) BAR:\n"
            f"   Time:  {forming['time']}\n"
            f"   Open:  {forming['open']:.5f} | Current: {forming['close']:.5f}\n\n"
            f"📋 RECENT CLOSED BARS:\n"
            f"{recent_text}"
        )
    else:
        content = str(symbol_or_content)

    entry = (
        "================================================================================\n"
        f"🕒 LOG TIMESTAMP: {now_utc} ({now_local}) | TIMEFRAME: 1-Minute\n"
        "--------------------------------------------------------------------------------\n"
        f"{content}\n"
        "================================================================================\n\n"
    )

    with open(filename, "a", encoding="utf-8") as f:
        f.write(entry)
    print(f"📥 [TV DATA LOGGED] Market data appended to {filename}")
    return filename
