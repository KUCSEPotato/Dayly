from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo


def utc_now() -> datetime:
    return datetime.now(UTC)


def seoul_today() -> date:
    return datetime.now(ZoneInfo("Asia/Seoul")).date()
