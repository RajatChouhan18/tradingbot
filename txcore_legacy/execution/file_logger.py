"""
txcore.execution.file_logger
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Thread-safe, non-blocking institutional logging subsystem for the TxBot platform.
Provides dual-layer logging:
  1. Human-Readable Rotating Logs: `signals_history.log`, `tv_market_data.log`
  2. High-Performance JSON Lines (JSONL): `logs/signals.jsonl`, `logs/market_data.jsonl`, `logs/app.jsonl`
  3. Asynchronous PostgreSQL Persistence: writes to `StructuredLog` table via Prisma ORM
"""

import os
import json
import threading
from datetime import datetime, timezone
from typing import Optional, Union, Any, Dict, List
import pandas as pd

from txcore.persistence import dispatch_save_log

# Anchor default logs to workspace root and dedicated logs/ directory
WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOGS_DIR = os.path.join(WORKSPACE_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

DEFAULT_SIGNALS_LOG = os.path.join(WORKSPACE_DIR, "signals_history.log")
DEFAULT_MARKET_DATA_LOG = os.path.join(WORKSPACE_DIR, "tv_market_data.log")
SIGNALS_JSONL_LOG = os.path.join(LOGS_DIR, "signals.jsonl")
MARKET_DATA_JSONL_LOG = os.path.join(LOGS_DIR, "market_data.jsonl")
APP_JSONL_LOG = os.path.join(LOGS_DIR, "app.jsonl")

# Thread lock for safe concurrent file writes
_file_lock = threading.Lock()
MAX_LOG_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB per file before simple rotation


def _rotate_if_needed(filepath: str):
    """Rotates log file if it exceeds size limit to avoid unbounded disk consumption."""
    try:
        if os.path.exists(filepath) and os.path.getsize(filepath) > MAX_LOG_SIZE_BYTES:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            rotated = f"{filepath}.{ts}.bak"
            os.rename(filepath, rotated)
    except Exception:
        pass


def log_structured_event(
    level: str,
    source: str,
    message: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Appends a structured event to JSONL log and dispatches non-blocking DB persistence.
    """
    now = datetime.now(timezone.utc)
    entry = {
        "timestamp": now.isoformat(),
        "level": level.upper(),
        "source": source.lower(),
        "message": message,
        "metadata": metadata or {},
    }

    with _file_lock:
        try:
            _rotate_if_needed(APP_JSONL_LOG)
            with open(APP_JSONL_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass

    # Asynchronous non-blocking persistence to Prisma ORM
    try:
        dispatch_save_log(level, source, message, metadata)
    except Exception:
        pass

    return entry


def log_signal_to_file(
    content: str,
    filename: Optional[str] = None,
    signal_metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Appends signal alerts with UTC and Local timestamps to the log file and JSONL stream.
    """
    if filename is None:
        filename = DEFAULT_SIGNALS_LOG

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    now_local = datetime.now().strftime("%H:%M:%S Local")
    entry = (
        "================================================================================\n"
        f"🕒 LOG TIMESTAMP: {now_utc} ({now_local}) | TIMEFRAME: Universal Pipeline\n"
        "--------------------------------------------------------------------------------\n"
        f"{content}\n"
        "================================================================================\n\n"
    )

    with _file_lock:
        _rotate_if_needed(filename)
        with open(filename, "a", encoding="utf-8") as f:
            f.write(entry)

        # Also write structured JSONL record
        try:
            _rotate_if_needed(SIGNALS_JSONL_LOG)
            jsonl_record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": "INFO",
                "source": "signals",
                "text": content.replace("\n", " | ")[:300],
                "metadata": signal_metadata or {},
            }
            with open(SIGNALS_JSONL_LOG, "a", encoding="utf-8") as jf:
                jf.write(json.dumps(jsonl_record) + "\n")
        except Exception:
            pass

    return filename


def log_market_data_to_file(
    symbol_or_content: Union[str, Any],
    df: Optional[pd.DataFrame] = None,
    filename: Optional[str] = None,
    provider_name: str = "HYBRID DATA PROVIDER",
) -> str:
    """
    Appends recent market data rows to the market data log file and JSONL stream.
    """
    if filename is None:
        filename = DEFAULT_MARKET_DATA_LOG

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    now_local = datetime.now().strftime("%H:%M:%S Local")

    structured_bars = []
    if df is not None and isinstance(df, pd.DataFrame) and not df.empty:
        symbol = str(symbol_or_content)
        last_closed = df.iloc[-2] if len(df) >= 2 else df.iloc[-1]
        forming = df.iloc[-1]

        recent_bars = []
        recent_slice = df.iloc[-4:-1] if len(df) >= 4 else df.iloc[:-1]
        for _, row in recent_slice.iterrows():
            t_str = str(row["time"])
            recent_bars.append(
                f"   • {t_str} | O: {float(row['open']):.5f} | H: {float(row['high']):.5f} | L: {float(row['low']):.5f} | C: {float(row['close']):.5f}"
            )
            structured_bars.append({
                "time": t_str,
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
            })
        recent_text = "\n".join(recent_bars) if recent_bars else "   (No prior bars)"

        content = (
            f"💱 ASSET: {symbol} | 📡 SOURCE: {provider_name}\n"
            f"📊 TOTAL BARS: {len(df)}\n\n"
            f"🕯 LATEST CLOSED BAR:\n"
            f"   Time:  {last_closed['time']}\n"
            f"   Open:  {float(last_closed['open']):.5f}\n"
            f"   High:  {float(last_closed['high']):.5f}\n"
            f"   Low:   {float(last_closed['low']):.5f}\n"
            f"   Close: {float(last_closed['close']):.5f}\n\n"
            f"⏳ IN-PROGRESS (FORMING) BAR:\n"
            f"   Time:  {forming['time']}\n"
            f"   Open:  {float(forming['open']):.5f} | Current: {float(forming['close']):.5f}\n\n"
            f"📋 RECENT CLOSED BARS:\n"
            f"{recent_text}"
        )
    else:
        symbol = "N/A"
        content = str(symbol_or_content)

    entry = (
        "================================================================================\n"
        f"🕒 LOG TIMESTAMP: {now_utc} ({now_local}) | ASSET: {symbol}\n"
        "--------------------------------------------------------------------------------\n"
        f"{content}\n"
        "================================================================================\n\n"
    )

    with _file_lock:
        _rotate_if_needed(filename)
        with open(filename, "a", encoding="utf-8") as f:
            f.write(entry)

        # Write to market_data.jsonl
        try:
            _rotate_if_needed(MARKET_DATA_JSONL_LOG)
            jsonl_record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": "INFO",
                "source": "market",
                "symbol": symbol,
                "bars_count": len(df) if df is not None else 0,
                "bars": structured_bars,
            }
            with open(MARKET_DATA_JSONL_LOG, "a", encoding="utf-8") as jf:
                jf.write(json.dumps(jsonl_record) + "\n")
        except Exception:
            pass

    return filename


def query_structured_logs(
    source: Optional[str] = None,
    level: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 150,
) -> List[Dict[str, Any]]:
    """
    Retrieves and filters structured log entries across JSONL and text files.
    """
    results: List[Dict[str, Any]] = []

    # Read from APP_JSONL_LOG if available
    if os.path.exists(APP_JSONL_LOG):
        with _file_lock:
            try:
                with open(APP_JSONL_LOG, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            item = json.loads(line)
                            if source and source != "all" and item.get("source", "").lower() != source.lower():
                                continue
                            if level and item.get("level", "").upper() != level.upper():
                                continue
                            if search:
                                q = search.lower()
                                msg = item.get("message", "").lower()
                                if q not in msg:
                                    continue
                            results.append({
                                "source": item.get("source", "app"),
                                "level": item.get("level", "INFO"),
                                "text": item.get("message", ""),
                                "metadata": item.get("metadata", {}),
                                "is_error": item.get("level", "").upper() in ("ERROR", "CRITICAL"),
                                "timestamp": item.get("timestamp", ""),
                            })
                        except Exception:
                            continue
            except Exception:
                pass

    return results[-limit:]
