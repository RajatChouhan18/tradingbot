"""
txcore.providers.session_manager
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Timezone-aware market session calculator, holiday checker, and trading status evaluator.
Currently supports Indian Exchanges (NSE/BSE) with extensibility for Forex, Crypto, etc.
"""

from datetime import datetime, time, timedelta, timezone
from typing import Optional, List
import zoneinfo

from txcore.models.types import MarketStatus, MarketSessionInfo


class MarketSessionManager:
    """
    Evaluates real-time trading state, market timings, and holidays for exchanges.
    Configurable for any market's timezone, session hours, and holiday calendar.
    """

    def __init__(
        self,
        timezone_name: str = "Asia/Kolkata",
        pre_market_open: tuple = (9, 0),
        market_open: tuple = (9, 15),
        market_close: tuple = (15, 30),
        post_market_close: tuple = (16, 0),
        holidays: Optional[List[str]] = None,
        market_label: str = "Indian",
    ):
        self.market_label = market_label
        self.pre_market_open = pre_market_open
        self.market_open = market_open
        self.market_close = market_close
        self.post_market_close = post_market_close
        self.holidays = set(holidays or [])
        try:
            self.tz = zoneinfo.ZoneInfo(timezone_name)
        except Exception:
            # Fallback for systems without complete tzdata
            self.tz = timezone(timedelta(hours=5, minutes=30), name="IST")

    def get_current_time(self, dt: Optional[datetime] = None) -> datetime:
        """Returns the given datetime or current time in the market's timezone."""
        if dt is None:
            return datetime.now(self.tz)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=self.tz)
        return dt.astimezone(self.tz)

    def is_holiday(self, dt: Optional[datetime] = None) -> bool:
        """Checks if the date is an exchange-declared trading holiday."""
        mkt_dt = self.get_current_time(dt)
        date_str = mkt_dt.strftime("%Y-%m-%d")
        return date_str in self.holidays

    def is_weekend(self, dt: Optional[datetime] = None) -> bool:
        """Checks if the date falls on Saturday (5) or Sunday (6)."""
        mkt_dt = self.get_current_time(dt)
        return mkt_dt.weekday() in (5, 6)

    def is_trading_day(self, dt: Optional[datetime] = None) -> bool:
        """Checks if the day is an active trading weekday (not weekend, not holiday)."""
        return not self.is_weekend(dt) and not self.is_holiday(dt)

    def is_market_open(self, dt: Optional[datetime] = None) -> bool:
        """Returns True if the market is currently in normal trading session."""
        info = self.get_session_info(dt)
        return info.status == MarketStatus.OPEN

    def is_pre_market(self, dt: Optional[datetime] = None) -> bool:
        """Returns True if the market is in pre-open auction session."""
        info = self.get_session_info(dt)
        return info.status == MarketStatus.PRE_OPEN

    def get_session_info(self, dt: Optional[datetime] = None) -> MarketSessionInfo:
        """
        Determines comprehensive market status and session details for any given timestamp.
        """
        mkt_dt = self.get_current_time(dt)
        curr_time = mkt_dt.time()
        time_str = mkt_dt.strftime("%H:%M:%S")

        # Check weekend
        if self.is_weekend(mkt_dt):
            day_name = mkt_dt.strftime("%A")
            return MarketSessionInfo(
                status=MarketStatus.WEEKEND,
                is_trading_active=False,
                current_time_ist=time_str,
                session_name=f"Weekend ({day_name})",
                message=f"{self.market_label} markets are closed on weekends.",
            )

        # Check holiday
        if self.is_holiday(mkt_dt):
            return MarketSessionInfo(
                status=MarketStatus.HOLIDAY,
                is_trading_active=False,
                current_time_ist=time_str,
                session_name="Trading Holiday",
                message=f"{self.market_label} markets are closed today ({mkt_dt.strftime('%Y-%m-%d')}) for exchange holiday.",
            )

        # Define boundary times
        t_pre_open = time(self.pre_market_open[0], self.pre_market_open[1])
        t_norm_open = time(self.market_open[0], self.market_open[1])
        t_norm_close = time(self.market_close[0], self.market_close[1])
        t_post_close = time(self.post_market_close[0], self.post_market_close[1])

        # Minutes helper
        def time_to_minutes(t: time) -> int:
            return t.hour * 60 + t.minute

        curr_mins = time_to_minutes(curr_time)
        norm_open_mins = time_to_minutes(t_norm_open)
        norm_close_mins = time_to_minutes(t_norm_close)

        if curr_time < t_pre_open:
            mins_to_open = norm_open_mins - curr_mins
            return MarketSessionInfo(
                status=MarketStatus.CLOSED,
                is_trading_active=False,
                current_time_ist=time_str,
                session_name="Pre-Market Overnight / Morning Wait",
                time_to_open_minutes=mins_to_open,
                message=f"Market opens in {mins_to_open} minutes at {t_norm_open.strftime('%H:%M')}.",
            )
        elif t_pre_open <= curr_time < t_norm_open:
            mins_to_open = norm_open_mins - curr_mins
            return MarketSessionInfo(
                status=MarketStatus.PRE_OPEN,
                is_trading_active=False,
                current_time_ist=time_str,
                session_name="Pre-Open Call Auction Session",
                time_to_open_minutes=mins_to_open,
                message=f"Pre-open price discovery underway. Normal trading begins in {mins_to_open}m.",
            )
        elif t_norm_open <= curr_time < t_norm_close:
            mins_to_close = norm_close_mins - curr_mins
            return MarketSessionInfo(
                status=MarketStatus.OPEN,
                is_trading_active=True,
                current_time_ist=time_str,
                session_name="Regular Continuous Trading",
                time_to_close_minutes=mins_to_close,
                message=f"Market is LIVE and active. Normal close in {mins_to_close} minutes.",
            )
        elif t_norm_close <= curr_time < t_post_close:
            return MarketSessionInfo(
                status=MarketStatus.POST_CLOSE,
                is_trading_active=False,
                current_time_ist=time_str,
                session_name="Closing & Post-Market Session",
                message=f"Normal trading closed at {t_norm_close.strftime('%H:%M')}. Post-market settlements.",
            )
        else:
            # After post-market close
            return MarketSessionInfo(
                status=MarketStatus.CLOSED,
                is_trading_active=False,
                current_time_ist=time_str,
                session_name="After Market Hours",
                message=f"{self.market_label} markets closed for the day. Re-opens next trading day at {t_norm_open.strftime('%H:%M')}.",
            )


# =========================================================================
# Pre-configured Session Managers for Common Markets
# =========================================================================

def create_indian_session_manager(holidays: Optional[List[str]] = None) -> MarketSessionManager:
    """Creates a session manager pre-configured for Indian NSE/BSE exchanges."""
    from config.settings import (
        INDIAN_TIMEZONE,
        INDIAN_PRE_MARKET_OPEN,
        INDIAN_NORMAL_MARKET_OPEN,
        INDIAN_NORMAL_MARKET_CLOSE,
        INDIAN_POST_MARKET_CLOSE,
        INDIAN_HOLIDAYS_2026,
    )
    return MarketSessionManager(
        timezone_name=INDIAN_TIMEZONE,
        pre_market_open=INDIAN_PRE_MARKET_OPEN,
        market_open=INDIAN_NORMAL_MARKET_OPEN,
        market_close=INDIAN_NORMAL_MARKET_CLOSE,
        post_market_close=INDIAN_POST_MARKET_CLOSE,
        holidays=holidays or INDIAN_HOLIDAYS_2026,
        market_label="Indian",
    )


# Backward-compatible alias for existing code
IndianMarketSessionManager = MarketSessionManager
