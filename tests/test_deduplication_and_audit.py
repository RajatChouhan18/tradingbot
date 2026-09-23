"""
tests.test_deduplication_and_audit
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for signal deduplication, memory pruning, and trade audit trails.
"""

from datetime import datetime, timezone
import time
import pytest

from txcore.audit.deduplicator import SignalDeduplicator
from txcore.audit.auditor import TradeAuditor

t0 = datetime(2026, 9, 24, 0, 0, tzinfo=timezone.utc)
t1 = datetime(2026, 9, 24, 0, 1, tzinfo=timezone.utc)


class TestDeduplication:
    def test_deduplicator_blocks_identical_setup(self):
        dedup = SignalDeduplicator(max_age_seconds=86400.0)

        # First time seen
        assert dedup.is_duplicate("EUR/USD", "Bullish Engulfing", t0) is False

        # Record signal
        dedup.record("EUR/USD", "Bullish Engulfing", t0)

        # Second time seen (same candle time) -> Duplicate
        assert dedup.is_duplicate("EUR/USD", "Bullish Engulfing", t0) is True

    def test_deduplicator_allows_new_candle_time(self):
        dedup = SignalDeduplicator(max_age_seconds=86400.0)
        dedup.record("EUR/USD", "Bullish Engulfing", t0)

        # New candle time -> Not duplicate
        assert dedup.is_duplicate("EUR/USD", "Bullish Engulfing", t1) is False

    def test_deduplicator_allows_different_pair(self):
        dedup = SignalDeduplicator(max_age_seconds=86400.0)
        dedup.record("EUR/USD", "Bullish Engulfing", t0)
        assert dedup.is_duplicate("GBP/USD", "Bullish Engulfing", t0) is False

    def test_pruning_removes_old_keys(self):
        # Cache with 1.0 second max age
        dedup = SignalDeduplicator(max_age_seconds=1.0)
        dedup.record("EUR/USD", "Bullish Engulfing", t0)
        assert dedup.size == 1

        time.sleep(1.1)
        pruned_count = dedup.prune()
        assert pruned_count == 1
        assert dedup.size == 0


class TestAuditor:
    def test_auditor_records_metrics(self):
        auditor = TradeAuditor()
        auditor.cycle_count = 5

        auditor.record_signal("EUR/USD", "CALL", "Bullish Engulfing", "APPROVED")
        auditor.record_signal("USD/JPY", "PUT", "Bearish Engulfing", "BLOCKED", reason="High impact news")

        summary = auditor.get_summary()
        assert summary["cycle_count"] == 5
        assert summary["total_scans"] == 2
        assert summary["signals_generated"] == 1
        assert summary["signals_blocked_by_news"] == 1
        assert len(auditor.history) == 2
