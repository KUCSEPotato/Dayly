from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum

from app.core.clock import seoul_day_bounds


class PeriodKind(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass(frozen=True)
class Period:
    kind: PeriodKind
    start: date
    end: date  # Exclusive, including for API date fields.

    @property
    def start_at(self) -> datetime:
        return seoul_day_bounds(self.start)[0]

    @property
    def end_at(self) -> datetime:
        return seoul_day_bounds(self.end)[0]


def resolve_period(kind: PeriodKind, today: date, anchor: date | None = None) -> Period:
    if anchor is None:
        if kind == PeriodKind.DAILY:
            anchor = today - timedelta(days=1)
        elif kind == PeriodKind.WEEKLY:
            anchor = today - timedelta(days=today.weekday() + 7)
        else:
            anchor = today.replace(day=1) - timedelta(days=1)
    if kind == PeriodKind.DAILY:
        return Period(kind, anchor, anchor + timedelta(days=1))
    if kind == PeriodKind.WEEKLY:
        start = anchor - timedelta(days=anchor.weekday())
        return Period(kind, start, start + timedelta(days=7))
    start = anchor.replace(day=1)
    return Period(kind, start, start + timedelta(days=monthrange(start.year, start.month)[1]))
