"""
txcore.marketview.session
~~~~~~~~~~~~~~~~~~~~~~~~~
Timezone-aware Market Session, Trading Hours, and Holiday Engine for AuraTrade.
Provides real-time open/closed status, session timing, and market banner messages
across Indian Equities (NSE/BSE), US Equities, Crypto, Forex, and MCX Commodities.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Set, Tuple
from datetime import datetime, time, timedelta, timezone
import zoneinfo

from txcore.marketview.models import MarketStatusInfo


class BaseMarketCalendar(ABC):
    """Abstract calendar and session evaluator for a financial market."""

    def __init__(self, market_code: str, timezone_name: str, holidays: Optional[Set[str]] = None):
        self.market_code = market_code.upper()
        self.timezone_name = timezone_name
        self.holidays = set(holidays or [])
        try:
            self.tz = zoneinfo.ZoneInfo(timezone_name)
        except Exception:
            self.tz = timezone.utc

    def to_market_time(self, dt: Optional[datetime] = None) -> datetime:
        """Converts datetime to market localized timezone."""
        if dt is None:
            return datetime.now(self.tz)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=self.tz)
        return dt.astimezone(self.tz)

    def is_holiday(self, dt: datetime) -> bool:
        """Checks whether date string YYYY-MM-DD is a declared trading holiday."""
        return dt.strftime("%Y-%m-%d") in self.holidays

    def is_weekend(self, dt: datetime) -> bool:
        """Checks whether day is Saturday (5) or Sunday (6)."""
        return dt.weekday() in (5, 6)

    @abstractmethod
    def evaluate_session(self, dt: Optional[datetime] = None) -> Tuple[bool, str, str]:
        """
        Returns (is_open: bool, session_name: str, status_message: str).
        """
        pass

    @abstractmethod
    def get_next_open_time(self, dt: Optional[datetime] = None) -> datetime:
        """Calculates the upcoming regular session opening in UTC."""
        pass


class IndianEquityCalendar(BaseMarketCalendar):
    """
    NSE & BSE Indian Equities & Indices Calendar.
    Hours (IST):
    - Pre-open: 09:00 - 09:08
    - Normal / Regular: 09:15 - 15:30
    - Post-market: 15:40 - 16:00
    - Weekends & NSE Holidays: Closed
    """

    # Major NSE Holidays for 2026/2027
    DEFAULT_HOLIDAYS = {
        "2026-01-26", "2026-03-03", "2026-03-26", "2026-04-03", "2026-04-14",
        "2026-05-01", "2026-08-15", "2026-10-02", "2026-10-20", "2026-11-08",
        "2026-11-10", "2026-12-25",
    }

    def __init__(self):
        super().__init__(
            market_code="INDIAN_EQUITY",
            timezone_name="Asia/Kolkata",
            holidays=self.DEFAULT_HOLIDAYS,
        )

    def evaluate_session(self, dt: Optional[datetime] = None) -> Tuple[bool, str, str]:
        local_dt = self.to_market_time(dt)
        curr_time = local_dt.time()
        time_str = local_dt.strftime("%H:%M:%S IST")

        if self.is_weekend(local_dt):
            day_name = local_dt.strftime("%A")
            return False, f"WEEKEND ({day_name})", f"Indian markets closed on weekends ({time_str})."

        if self.is_holiday(local_dt):
            return False, "HOLIDAY", f"Indian markets closed for exchange holiday ({time_str})."

        if time(9, 0) <= curr_time < time(9, 8):
            return False, "PRE_MARKET", f"Pre-open order collection session ({time_str})."
        elif time(9, 8) <= curr_time < time(9, 15):
            return False, "PRE_OPEN_BUFFER", f"Pre-market price matching buffer ({time_str})."
        elif time(9, 15) <= curr_time <= time(15, 30):
            return True, "REGULAR_SESSION", f"Normal trading session active ({time_str})."
        elif time(15, 40) <= curr_time <= time(16, 0):
            return False, "POST_MARKET", f"Post-market closing session ({time_str})."
        else:
            return False, "CLOSED", f"Indian markets closed for the day ({time_str})."

    def get_next_open_time(self, dt: Optional[datetime] = None) -> datetime:
        local_dt = self.to_market_time(dt)
        curr_time = local_dt.time()

        # If today is trading day and before 09:15, next open is today at 09:15
        if not self.is_weekend(local_dt) and not self.is_holiday(local_dt) and curr_time < time(9, 15):
            target = local_dt.replace(hour=9, minute=15, second=0, microsecond=0)
            return target.astimezone(timezone.utc)

        # Otherwise step day by day
        candidate = (local_dt + timedelta(days=1)).replace(hour=9, minute=15, second=0, microsecond=0)
        while self.is_weekend(candidate) or self.is_holiday(candidate):
            candidate += timedelta(days=1)

        return candidate.astimezone(timezone.utc)


class UsEquityCalendar(BaseMarketCalendar):
    """
    US Equities (NASDAQ / NYSE) Calendar.
    Hours (US Eastern):
    - Pre-market: 04:00 - 09:30
    - Regular Session: 09:30 - 16:00
    - Post-market: 16:00 - 20:00
    """

    DEFAULT_HOLIDAYS = {
        "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25",
        "2026-06-19", "2026-07-03", "2026-09-07", "2026-11-26", "2026-12-25",
    }

    def __init__(self):
        super().__init__(
            market_code="US_EQUITY",
            timezone_name="America/New_York",
            holidays=self.DEFAULT_HOLIDAYS,
        )

    def evaluate_session(self, dt: Optional[datetime] = None) -> Tuple[bool, str, str]:
        local_dt = self.to_market_time(dt)
        curr_time = local_dt.time()
        time_str = local_dt.strftime("%H:%M:%S ET")

        if self.is_weekend(local_dt):
            day_name = local_dt.strftime("%A")
            return False, f"WEEKEND ({day_name})", f"US markets closed on weekends ({time_str})."

        if self.is_holiday(local_dt):
            return False, "HOLIDAY", f"US markets closed for federal/market holiday ({time_str})."

        if time(4, 0) <= curr_time < time(9, 30):
            return False, "PRE_MARKET", f"US pre-market trading session ({time_str})."
        elif time(9, 30) <= curr_time <= time(16, 0):
            return True, "REGULAR_SESSION", f"US regular trading session active ({time_str})."
        elif time(16, 0) < curr_time <= time(20, 0):
            return False, "POST_MARKET", f"US after-hours trading session ({time_str})."
        else:
            return False, "CLOSED", f"US markets closed ({time_str})."

    def get_next_open_time(self, dt: Optional[datetime] = None) -> datetime:
        local_dt = self.to_market_time(dt)
        curr_time = local_dt.time()

        if not self.is_weekend(local_dt) and not self.is_holiday(local_dt) and curr_time < time(9, 30):
            target = local_dt.replace(hour=9, minute=30, second=0, microsecond=0)
            return target.astimezone(timezone.utc)

        candidate = (local_dt + timedelta(days=1)).replace(hour=9, minute=30, second=0, microsecond=0)
        while self.is_weekend(candidate) or self.is_holiday(candidate):
            candidate += timedelta(days=1)

        return candidate.astimezone(timezone.utc)


class CryptoCalendar(BaseMarketCalendar):
    """
    Cryptocurrency Market Calendar (24/7/365 continuous trading).
    Always open with zero holidays or weekend closures.
    """

    def __init__(self):
        super().__init__(market_code="CRYPTO", timezone_name="UTC")

    def evaluate_session(self, dt: Optional[datetime] = None) -> Tuple[bool, str, str]:
        local_dt = self.to_market_time(dt)
        return True, "REGULAR_SESSION (24/7)", f"Crypto market is continuously open ({local_dt.strftime('%H:%M:%S UTC')})."

    def get_next_open_time(self, dt: Optional[datetime] = None) -> datetime:
        # Always open, next open is current time
        return datetime.now(timezone.utc)


class ForexCalendar(BaseMarketCalendar):
    """
    Global Forex 24/5 Calendar.
    Opens Sunday 17:00 EST / 22:00 UTC and closes Friday 17:00 EST / 22:00 UTC.
    """

    def __init__(self):
        super().__init__(market_code="FOREX", timezone_name="America/New_York")

    def evaluate_session(self, dt: Optional[datetime] = None) -> Tuple[bool, str, str]:
        local_dt = self.to_market_time(dt)
        weekday = local_dt.weekday()  # Monday=0, ..., Saturday=5, Sunday=6
        curr_time = local_dt.time()
        time_str = local_dt.strftime("%H:%M:%S ET")

        if weekday == 5:  # Saturday
            return False, "WEEKEND", f"Forex market closed for weekend ({time_str})."
        elif weekday == 6:  # Sunday
            if curr_time < time(17, 0):
                return False, "WEEKEND", f"Forex opens Sunday at 17:00 ET ({time_str})."
            return True, "REGULAR_SESSION", f"Forex session active ({time_str})."
        elif weekday == 4:  # Friday
            if curr_time > time(17, 0):
                return False, "WEEKEND_CLOSE", f"Forex closed for weekend after 17:00 ET ({time_str})."
            return True, "REGULAR_SESSION", f"Forex session active ({time_str})."
        else:
            return True, "REGULAR_SESSION", f"Forex session active ({time_str})."

    def get_next_open_time(self, dt: Optional[datetime] = None) -> datetime:
        local_dt = self.to_market_time(dt)
        weekday = local_dt.weekday()
        curr_time = local_dt.time()

        if weekday in [0, 1, 2, 3]:  # Mon-Thu
            return datetime.now(timezone.utc)
        elif weekday == 4 and curr_time <= time(17, 0):  # Fri before close
            return datetime.now(timezone.utc)
        elif weekday == 6 and curr_time >= time(17, 0):  # Sun after open
            return datetime.now(timezone.utc)

        # Calculate upcoming Sunday at 17:00 ET
        days_ahead = (6 - weekday) % 7
        if days_ahead == 0 and curr_time < time(17, 0):
            days_ahead = 0
        elif days_ahead == 0:
            days_ahead = 7

        target = (local_dt + timedelta(days=days_ahead)).replace(hour=17, minute=0, second=0, microsecond=0)
        return target.astimezone(timezone.utc)


class McxCalendar(BaseMarketCalendar):
    """
    MCX India Commodities Calendar.
    Hours (IST):
    - Session: 09:00 - 23:30 (or 23:55 during US daylight saving)
    - Weekends: Closed
    """

    DEFAULT_HOLIDAYS = {
        "2026-01-26", "2026-03-03", "2026-04-03", "2026-05-01",
        "2026-08-15", "2026-10-02", "2026-10-20", "2026-11-10", "2026-12-25",
    }

    def __init__(self):
        super().__init__(market_code="MCX", timezone_name="Asia/Kolkata", holidays=self.DEFAULT_HOLIDAYS)

    def evaluate_session(self, dt: Optional[datetime] = None) -> Tuple[bool, str, str]:
        local_dt = self.to_market_time(dt)
        curr_time = local_dt.time()
        time_str = local_dt.strftime("%H:%M:%S IST")

        if self.is_weekend(local_dt):
            return False, "WEEKEND", f"MCX commodities closed on weekends ({time_str})."
        if self.is_holiday(local_dt):
            return False, "HOLIDAY", f"MCX closed for holiday ({time_str})."

        if time(9, 0) <= curr_time <= time(23, 30):
            return True, "REGULAR_SESSION", f"MCX commodity trading active ({time_str})."
        else:
            return False, "CLOSED", f"MCX closed for the night ({time_str})."

    def get_next_open_time(self, dt: Optional[datetime] = None) -> datetime:
        local_dt = self.to_market_time(dt)
        curr_time = local_dt.time()

        if not self.is_weekend(local_dt) and not self.is_holiday(local_dt) and curr_time < time(9, 0):
            target = local_dt.replace(hour=9, minute=0, second=0, microsecond=0)
            return target.astimezone(timezone.utc)

        candidate = (local_dt + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
        while self.is_weekend(candidate) or self.is_holiday(candidate):
            candidate += timedelta(days=1)

        return candidate.astimezone(timezone.utc)


class MarketSessionManager:
    """
    Central Manager managing session evaluators and status reporting across all platforms.
    """

    def __init__(self):
        self._calendars: Dict[str, BaseMarketCalendar] = {
            "INDIAN_EQUITY": IndianEquityCalendar(),
            "US_EQUITY": UsEquityCalendar(),
            "CRYPTO": CryptoCalendar(),
            "FOREX": ForexCalendar(),
            "MCX": McxCalendar(),
            "NSE": IndianEquityCalendar(),
            "BSE": IndianEquityCalendar(),
            "NASDAQ": UsEquityCalendar(),
            "NYSE": UsEquityCalendar(),
        }

    def get_calendar(self, market: str) -> BaseMarketCalendar:
        """Returns calendar evaluator for the given market code."""
        return self._calendars.get(market.upper(), self._calendars["INDIAN_EQUITY"])

    def get_market_status(
        self,
        market: str,
        last_price: Optional[float] = None,
        last_time: Optional[datetime] = None,
        dt: Optional[datetime] = None,
        exchange: Optional[str] = None,
    ) -> MarketStatusInfo:
        """
        Determines market status, session info, and creates user-friendly institutional banner message.
        """
        calendar = self.get_calendar(market)
        is_open, session_name, message = calendar.evaluate_session(dt=dt)
        next_open = calendar.get_next_open_time(dt=dt) if not is_open else None

        # Format institutional closed overlay banner if closed
        if not is_open:
            if last_price is not None and last_time is not None:
                formatted_time = last_time.strftime("%d %b %Y, %H:%M:%S UTC")
                banner_message = f"Market Closed • Displaying Last Traded Price: {last_price} as of {formatted_time}"
            else:
                banner_message = f"Market Closed • {message}"
        else:
            banner_message = message

        return MarketStatusInfo(
            market=market.upper(),
            exchange=exchange.upper() if exchange else market.upper(),
            isOpen=is_open,
            sessionName=session_name,
            lastTradedPrice=last_price,
            lastTradedTime=last_time,
            nextOpenTime=next_open,
            message=banner_message,
        )


# Global singleton instance
session_manager = MarketSessionManager()
