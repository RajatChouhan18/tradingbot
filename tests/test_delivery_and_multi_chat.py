"""
tests.test_delivery_and_multi_chat
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Comprehensive tests for:
  1. Unique collision-resistant Signal IDs.
  2. Multi-chat Telegram broadcasting.
  3. DeliveryTracker SQLite database persistence and file logging.
  4. Failure handling, partial failures, and placeholder skipping.
"""

import os
import tempfile
import sqlite3
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
import pytest

from txcore.models.types import Signal, Direction, generate_signal_id
from txcore.audit.delivery_tracker import DeliveryTracker
from txcore.execution.telegram import TelegramNotifier


# =====================================================================
# 1. UNIQUE SIGNAL IDENTIFIER TESTS
# =====================================================================
class TestSignalIdentifier:
    def test_generate_signal_id_format(self):
        t = datetime(2026, 9, 24, 12, 30, 45, tzinfo=timezone.utc)
        sig_id = generate_signal_id("EUR/USD", timestamp=t)
        
        # Must start with SIG-EURUSD-20260924-123045-
        assert sig_id.startswith("SIG-EURUSD-20260924-123045-")
        parts = sig_id.split("-")
        assert len(parts) == 5
        assert parts[0] == "SIG"
        assert parts[1] == "EURUSD"
        assert parts[2] == "20260924"
        assert parts[3] == "123045"
        assert len(parts[4]) == 6  # 6-char hex suffix

    def test_collision_resistance_under_high_concurrency(self):
        t = datetime(2026, 9, 24, 1, 0, 0, tzinfo=timezone.utc)
        generated_ids = {generate_signal_id("GBP/JPY", timestamp=t) for _ in range(1000)}
        # All 1000 IDs generated at the exact same second for the same pair must be distinct
        assert len(generated_ids) == 1000

    def test_signal_auto_generates_id(self):
        sig = Signal(
            pair="AUD/USD",
            direction=Direction.CALL,
            pattern="Bullish Engulfing",
            level=0.6500,
            price=0.6502,
            candle_time=datetime(2026, 9, 24, 10, 0, tzinfo=timezone.utc),
            reason="Test signal",
        )
        assert sig.signal_id.startswith("SIG-AUDUSD-")
        alert_msg = sig.to_alert_message()
        assert f"🆔 ID: {sig.signal_id}" in alert_msg

    def test_signal_preserves_custom_id(self):
        sig = Signal(
            pair="USD/CAD",
            direction=Direction.PUT,
            pattern="Shooting Star",
            level=1.3500,
            price=1.3495,
            candle_time=datetime(2026, 9, 24, 10, 0, tzinfo=timezone.utc),
            reason="Custom ID test",
            signal_id="CUSTOM-SIG-001",
        )
        assert sig.signal_id == "CUSTOM-SIG-001"
        assert "🆔 ID: CUSTOM-SIG-001" in sig.to_alert_message()


# =====================================================================
# 2. DELIVERY TRACKER (SQLITE & LOGGING) TESTS
# =====================================================================
class TestDeliveryTracker:
    @pytest.fixture
    def tracker_env(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_audit.db")
            log_path = os.path.join(tmpdir, "test_delivery.log")
            tracker = DeliveryTracker(db_path=db_path, log_path=log_path)
            yield tracker, db_path, log_path

    def test_record_and_query_dispatches(self, tracker_env):
        tracker, db_path, log_path = tracker_env

        row_id_1 = tracker.record_dispatch(
            signal_id="SIG-001",
            pair="EUR/USD",
            direction="CALL",
            pattern="Bullish Engulfing",
            price=1.0850,
            chat_id="111111",
            status="SENT",
        )
        assert row_id_1 == 1

        row_id_2 = tracker.record_dispatch(
            signal_id="SIG-001",
            pair="EUR/USD",
            direction="CALL",
            pattern="Bullish Engulfing",
            price=1.0850,
            chat_id="222222",
            status="FAILED",
            error_message="HTTP 403 Forbidden",
        )
        assert row_id_2 == 2

        row_id_3 = tracker.record_dispatch(
            signal_id="SIG-002",
            pair="GBP/USD",
            direction="PUT",
            pattern="Dark Cloud Cover",
            price=1.2750,
            chat_id="111111",
            status="SENT",
        )
        assert row_id_3 == 3

        # Query by signal_id
        sig_dispatches = tracker.get_dispatches_for_signal("SIG-001")
        assert len(sig_dispatches) == 2
        assert sig_dispatches[0]["chat_id"] == "111111"
        assert sig_dispatches[0]["status"] == "SENT"
        assert sig_dispatches[1]["chat_id"] == "222222"
        assert sig_dispatches[1]["status"] == "FAILED"
        assert "403" in sig_dispatches[1]["error_message"]

        # Query by chat_id
        chat_dispatches = tracker.get_dispatches_for_chat("111111")
        assert len(chat_dispatches) == 2
        assert {d["signal_id"] for d in chat_dispatches} == {"SIG-001", "SIG-002"}

        # Query recent dispatches
        recent = tracker.get_recent_dispatches(limit=10)
        assert len(recent) == 3

        # Verify log file contents
        assert os.path.exists(log_path)
        with open(log_path, "r", encoding="utf-8") as f:
            log_content = f.read()
        assert "✅ DISPATCH | ID: SIG-001 | PAIR: EUR/USD | CHAT_ID: 111111 | STATUS: SENT" in log_content
        assert "❌ DISPATCH | ID: SIG-001 | PAIR: EUR/USD | CHAT_ID: 222222 | STATUS: FAILED" in log_content
        assert "HTTP 403 Forbidden" in log_content


# =====================================================================
# 3. TELEGRAM MULTI-CHAT NOTIFIER TESTS
# =====================================================================
class TestTelegramNotifierMultiChat:
    @pytest.fixture
    def test_setup(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_audit.db")
            log_path = os.path.join(tmpdir, "test_delivery.log")
            tracker = DeliveryTracker(db_path=db_path, log_path=log_path)
            yield tracker

    def test_chat_ids_initialization(self, test_setup):
        tracker = test_setup

        # Single chat_id
        notifier_single = TelegramNotifier(bot_token="test_tok", chat_id="12345", tracker=tracker)
        assert notifier_single.chat_ids == ["12345"]

        # Multiple chat_ids list
        notifier_multi = TelegramNotifier(bot_token="test_tok", chat_ids=["111", "222", "  333  "], tracker=tracker)
        assert notifier_multi.chat_ids == ["111", "222", "333"]

        # Both chat_id and chat_ids deduplicated
        notifier_both = TelegramNotifier(bot_token="test_tok", chat_id="111", chat_ids=["111", "222"], tracker=tracker)
        assert notifier_both.chat_ids == ["111", "222"]

    def test_is_configured_check(self, test_setup):
        tracker = test_setup
        assert TelegramNotifier("", chat_ids=["123"], tracker=tracker).is_configured is False
        assert TelegramNotifier("token", chat_ids=[], tracker=tracker).is_configured is False
        assert TelegramNotifier("token", chat_ids=["dummy_chat_id"], tracker=tracker).is_configured is False
        assert TelegramNotifier("token", chat_ids=["123456"], tracker=tracker).is_configured is True

    @patch("requests.post")
    def test_multi_chat_broadcast_success(self, mock_post, test_setup):
        tracker = test_setup
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        notifier = TelegramNotifier(
            bot_token="dummy_token_123",
            chat_ids=["chat_A", "chat_B", "chat_C"],
            tracker=tracker,
        )

        sig = Signal(
            pair="EUR/JPY",
            direction=Direction.CALL,
            pattern="Bullish Engulfing",
            level=160.50,
            price=160.55,
            candle_time=datetime(2026, 9, 24, 8, 0, tzinfo=timezone.utc),
            reason="Bounce off S&R",
        )

        results = notifier.send("Test Alert", signal=sig)
        assert results == {"chat_A": True, "chat_B": True, "chat_C": True}
        assert mock_post.call_count == 3

        # Verify DB entries
        dispatches = tracker.get_dispatches_for_signal(sig.signal_id)
        assert len(dispatches) == 3
        for d in dispatches:
            assert d["status"] == "SENT"
            assert d["pair"] == "EUR/JPY"

    @patch("requests.post")
    def test_partial_failure_continues_to_other_chats(self, mock_post, test_setup):
        tracker = test_setup

        def side_effect(url, data, timeout):
            if data["chat_id"] == "bad_chat":
                err_resp = MagicMock()
                err_resp.raise_for_status.side_effect = Exception("Chat not found")
                return err_resp
            ok_resp = MagicMock()
            ok_resp.raise_for_status.return_value = None
            return ok_resp

        mock_post.side_effect = side_effect

        notifier = TelegramNotifier(
            bot_token="token_xyz",
            chat_ids=["good_chat_1", "bad_chat", "good_chat_2"],
            tracker=tracker,
        )

        sig = Signal(
            pair="CAD/JPY",
            direction=Direction.PUT,
            pattern="Bearish Engulfing",
            level=110.20,
            price=110.15,
            candle_time=datetime(2026, 9, 24, 9, 0, tzinfo=timezone.utc),
            reason="Resistance drop",
        )

        results = notifier.send("Test Partial Alert", signal=sig)
        assert results == {
            "good_chat_1": True,
            "bad_chat": False,
            "good_chat_2": True,
        }

        # Check DB tracking
        dispatches = tracker.get_dispatches_for_signal(sig.signal_id)
        assert len(dispatches) == 3
        status_map = {d["chat_id"]: d["status"] for d in dispatches}
        assert status_map["good_chat_1"] == "SENT"
        assert status_map["bad_chat"] == "FAILED"
        assert status_map["good_chat_2"] == "SENT"

    def test_skips_dummy_chat_id(self, test_setup):
        tracker = test_setup
        notifier = TelegramNotifier(
            bot_token="token_xyz",
            chat_ids=["dummy_chat_id", ""],
            tracker=tracker,
        )

        sig = Signal(
            pair="EUR/USD",
            direction=Direction.CALL,
            pattern="Piercing Line",
            level=1.0500,
            price=1.0505,
            candle_time=datetime(2026, 9, 24, 9, 0, tzinfo=timezone.utc),
            reason="Support level",
        )

        with patch("requests.post") as mock_post:
            results = notifier.send("Alert", signal=sig)
            assert mock_post.call_count == 0
            assert results.get("dummy_chat_id") is False

        dispatches = tracker.get_dispatches_for_signal(sig.signal_id)
        assert len(dispatches) == 1
        assert dispatches[0]["status"] == "SKIPPED"
        assert "placeholder" in dispatches[0]["error_message"].lower()

    @patch("requests.post")
    def test_send_with_chart_attachment(self, mock_post, test_setup, tmp_path):
        tracker = test_setup
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        # Create dummy chart file
        chart_file = tmp_path / "chart_EUR_USD_20260924.html"
        chart_file.write_text("<html>TradingView Chart</html>", encoding="utf-8")

        notifier = TelegramNotifier(
            bot_token="token_123",
            chat_ids=["chat_100", "chat_200"],
            tracker=tracker,
        )

        sig = Signal(
            pair="EUR/USD",
            direction=Direction.CALL,
            pattern="Bullish Engulfing",
            level=1.1000,
            price=1.1005,
            candle_time=datetime(2026, 9, 24, 10, 0, tzinfo=timezone.utc),
            reason="Support level test",
        )

        notifier.send("Signal Alert", signal=sig, chart_path=str(chart_file))

        # 2 sendMessage calls + 2 sendDocument calls = 4 POST calls
        assert mock_post.call_count == 4
        calls = mock_post.call_args_list
        urls = [c[0][0] for c in calls]
        assert urls.count("https://api.telegram.org/bottoken_123/sendMessage") == 2
        assert urls.count("https://api.telegram.org/bottoken_123/sendDocument") == 2

