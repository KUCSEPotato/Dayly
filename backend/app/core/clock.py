from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo


def utc_now() -> datetime:
    return datetime.now(UTC)


def seoul_today() -> date:
    return datetime.now(ZoneInfo("Asia/Seoul")).date()


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("A timezone-aware timestamp is required")
    return value.astimezone(UTC)


def seoul_day_bounds(day: date) -> tuple[datetime, datetime]:
    """UTC boundaries for a Seoul calendar day: [start, end)."""
    start = datetime.combine(day, time.min, tzinfo=ZoneInfo("Asia/Seoul"))
    return as_utc(start), as_utc(start + timedelta(days=1))
