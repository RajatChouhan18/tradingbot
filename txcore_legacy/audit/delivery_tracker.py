"""
txcore.audit.delivery_tracker
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Audit logging and SQLite persistence for multi-chat signal deliveries.
Records every dispatch attempt per chat ID with signal identifiers, timestamps, and delivery status.
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Generator

WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_DB_PATH = os.path.join(WORKSPACE_DIR, "trading_audit.db")
DEFAULT_LOG_PATH = os.path.join(WORKSPACE_DIR, "telegram_delivery.log")


class DeliveryTracker:
    """
    Persists signal dispatch records to an SQLite database and human-readable log file.
    Ensures immediate connection closure to avoid Windows file-locking issues.
    """

    def __init__(self, db_path: Optional[str] = None, log_path: Optional[str] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.log_path = log_path or DEFAULT_LOG_PATH
        self._init_db()

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Provides an auto-closing SQLite connection context manager."""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        """Initializes SQLite schema if not already present."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS signal_dispatches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id TEXT NOT NULL,
                    pair TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    pattern TEXT NOT NULL,
                    price REAL NOT NULL,
                    chat_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    sent_at_utc TEXT NOT NULL,
                    sent_at_local TEXT NOT NULL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sig_id ON signal_dispatches(signal_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_id ON signal_dispatches(chat_id)")
            conn.commit()

    def record_dispatch(
        self,
        signal_id: str,
        pair: str,
        direction: str,
        pattern: str,
        price: float,
        chat_id: str,
        status: str,
        error_message: Optional[str] = None,
    ) -> int:
        """
        Records a dispatch attempt to both SQLite DB and the delivery log file.
        Status: 'SENT', 'FAILED', or 'SKIPPED'.
        """
        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        now_local = datetime.now().strftime("%Y-%m-%d %H:%M:%S Local")

        # 1. Insert into SQLite DB
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO signal_dispatches 
                (signal_id, pair, direction, pattern, price, chat_id, status, error_message, sent_at_utc, sent_at_local)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal_id,
                pair,
                direction,
                pattern,
                price,
                chat_id,
                status,
                error_message,
                now_utc,
                now_local,
            ))
            conn.commit()
            record_id = cursor.lastrowid

        # 2. Append to delivery log file
        status_icon = "✅" if status == "SENT" else ("❌" if status == "FAILED" else "⚠️")
        log_line = (
            f"[{now_utc}] {status_icon} DISPATCH | ID: {signal_id} | "
            f"PAIR: {pair} | CHAT_ID: {chat_id} | STATUS: {status}"
        )
        if error_message:
            log_line += f" | ERROR: {error_message}"
        log_line += "\n"

        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(log_line)

        return record_id

    def get_dispatches_for_signal(self, signal_id: str) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM signal_dispatches WHERE signal_id = ? ORDER BY id ASC", (signal_id,))
            return [dict(r) for r in cursor.fetchall()]

    def get_dispatches_for_chat(self, chat_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM signal_dispatches WHERE chat_id = ? ORDER BY id DESC LIMIT ?",
                (chat_id, limit),
            )
            return [dict(r) for r in cursor.fetchall()]

    def get_recent_dispatches(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM signal_dispatches ORDER BY id DESC LIMIT ?", (limit,))
            return [dict(r) for r in cursor.fetchall()]
