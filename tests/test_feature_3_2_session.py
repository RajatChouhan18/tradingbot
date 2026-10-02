"""
tests.test_feature_3_2_session
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Automated test verification suite for Feature 3.2:
- Market-Closed Detection & Timing Engine.
- Timezone-aware session calendars (Indian Equity, US Equity, Crypto, Forex, MCX).
- Next session opening calculation across market types.
- Institutional market-closed status banner message formatting.
"""

import sys
import os
import pytest
from datetime import datetime, timezone
import zoneinfo

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from txcore.marketview.session import (
    IndianEquityCalendar,
    UsEquityCalendar,
    CryptoCalendar,
    ForexCalendar,
    McxCalendar,
    MarketSessionManager,
    session_manager,
)


def test_indian_equity_calendar_sessions():
    cal = IndianEquityCalendar()
    ist = zoneinfo.ZoneInfo("Asia/Kolkata")

    # 1. Normal Trading Session (Wednesday 10:30 IST)
    dt_open = datetime(2026, 6, 10, 10, 30, 0, tzinfo=ist)
    is_open, sess_name, _ = cal.evaluate_session(dt_open)
    assert is_open is True
    assert sess_name == "REGULAR_SESSION"

    # 2. Pre-market session (Wednesday 09:05 IST)
    dt_pre = datetime(2026, 6, 10, 9, 5, 0, tzinfo=ist)
    is_open_pre, sess_pre, _ = cal.evaluate_session(dt_pre)
    assert is_open_pre is False
    assert sess_pre == "PRE_MARKET"

    # 3. Closed after-hours (Wednesday 18:00 IST)
    dt_closed = datetime(2026, 6, 10, 18, 0, 0, tzinfo=ist)
    is_open_cl, sess_cl, _ = cal.evaluate_session(dt_closed)
    assert is_open_cl is False
    assert sess_cl == "CLOSED"

    # 4. Weekend (Saturday 12:00 IST)
    dt_wknd = datetime(2026, 6, 13, 12, 0, 0, tzinfo=ist)
    is_open_wk, sess_wk, _ = cal.evaluate_session(dt_wknd)
    assert is_open_wk is False
    assert "WEEKEND" in sess_wk

    # 5. Holiday (2026-01-26 Republic Day at 11:00 IST)
    dt_hol = datetime(2026, 1, 26, 11, 0, 0, tzinfo=ist)
    is_open_hol, sess_hol, _ = cal.evaluate_session(dt_hol)
    assert is_open_hol is False
    assert sess_hol == "HOLIDAY"

    # 6. Next open time calculation from Friday evening (2026-06-12 18:00 IST)
    # Must yield Monday 2026-06-15 at 09:15 IST -> 03:45 UTC
    dt_fri_eve = datetime(2026, 6, 12, 18, 0, 0, tzinfo=ist)
    next_open = cal.get_next_open_time(dt_fri_eve)
    next_open_ist = next_open.astimezone(ist)
    assert next_open_ist.weekday() == 0  # Monday
    assert next_open_ist.hour == 9
    assert next_open_ist.minute == 15


def test_us_equity_calendar_sessions():
    cal = UsEquityCalendar()
    et = zoneinfo.ZoneInfo("America/New_York")

    # 1. Regular US Trading Session (Tuesday 11:00 ET)
    dt_open = datetime(2026, 6, 9, 11, 0, 0, tzinfo=et)
    is_open, sess_name, _ = cal.evaluate_session(dt_open)
    assert is_open is True
    assert sess_name == "REGULAR_SESSION"

    # 2. Pre-market session (Tuesday 06:00 ET)
    dt_pre = datetime(2026, 6, 9, 6, 0, 0, tzinfo=et)
    is_open_pre, sess_pre, _ = cal.evaluate_session(dt_pre)
    assert is_open_pre is False
    assert sess_pre == "PRE_MARKET"

    # 3. Post-market session (Tuesday 17:00 ET)
    dt_post = datetime(2026, 6, 9, 17, 0, 0, tzinfo=et)
    is_open_post, sess_post, _ = cal.evaluate_session(dt_post)
    assert is_open_post is False
    assert sess_post == "POST_MARKET"

    # 4. Next open time from Tuesday 06:00 ET -> Tuesday 09:30 ET
    next_open = cal.get_next_open_time(dt_pre)
    next_open_et = next_open.astimezone(et)
    assert next_open_et.hour == 9
    assert next_open_et.minute == 30


def test_crypto_calendar_24x7():
    cal = CryptoCalendar()
    dt_any = datetime(2026, 6, 14, 3, 30, 0, tzinfo=timezone.utc)  # Sunday night
    is_open, sess_name, _ = cal.evaluate_session(dt_any)
    assert is_open is True
    assert "24/7" in sess_name


def test_forex_calendar_24x5():
    cal = ForexCalendar()
    et = zoneinfo.ZoneInfo("America/New_York")

    # Wednesday 14:00 ET -> Open
    dt_wed = datetime(2026, 6, 10, 14, 0, 0, tzinfo=et)
    is_open_wed, _, _ = cal.evaluate_session(dt_wed)
    assert is_open_wed is True

    # Saturday 14:00 ET -> Weekend closed
    dt_sat = datetime(2026, 6, 13, 14, 0, 0, tzinfo=et)
    is_open_sat, sess_sat, _ = cal.evaluate_session(dt_sat)
    assert is_open_sat is False
    assert "WEEKEND" in sess_sat


def test_mcx_commodity_calendar():
    cal = McxCalendar()
    ist = zoneinfo.ZoneInfo("Asia/Kolkata")

    # Evening session (Tuesday 20:00 IST) -> Active
    dt_eve = datetime(2026, 6, 9, 20, 0, 0, tzinfo=ist)
    is_open_eve, sess_eve, _ = cal.evaluate_session(dt_eve)
    assert is_open_eve is True
    assert sess_eve == "REGULAR_SESSION"


def test_market_session_manager_status_banner():
    mgr = MarketSessionManager()
    ist = zoneinfo.ZoneInfo("Asia/Kolkata")

    # Test status when closed with last traded price and time
    dt_closed = datetime(2026, 6, 10, 19, 0, 0, tzinfo=ist)
    last_price = 2845.50
    last_time = datetime(2026, 6, 10, 15, 30, 0, tzinfo=timezone.utc)

    status_info = mgr.get_market_status(
        market="INDIAN_EQUITY",
        last_price=last_price,
        last_time=last_time,
        dt=dt_closed,
        exchange="NSE",
    )

    assert status_info.isOpen is False
    assert status_info.sessionName == "CLOSED"
    assert status_info.lastTradedPrice == 2845.50
    assert "Market Closed • Displaying Last Traded Price: 2845.5" in status_info.message
    assert status_info.nextOpenTime is not None
