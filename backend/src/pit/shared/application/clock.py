from datetime import UTC, date, datetime
from typing import Protocol
from zoneinfo import ZoneInfo


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


def local_date(moment: datetime, timezone: str) -> date:
    """The calendar day a user is living in. Daily deadlines are always in the user's timezone."""
    return moment.astimezone(ZoneInfo(timezone)).date()
