from calendar import monthrange
from datetime import date, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.task import Task
from app.schemas.statistics import CalendarSummary, DailyStatistics, WeeklyStatistics
from app.services.policy import ensure_accessible


def completion_rate(completed: int, total: int) -> float | None:
    return round(completed / total * 100, 2) if total else None


class StatisticsService:
    def __init__(self, session: Session, today: date):
        self.session = session
        self.today = today

    def _days(self, start: date, end: date) -> list[DailyStatistics]:
        # One grouped query, rather than loading every Task or querying once per day.
        rows = self.session.execute(
            select(Task.scheduled_date, func.count(Task.id),
                   func.sum(case((Task.is_completed.is_(True), 1), else_=0)))
            .where(Task.scheduled_date.between(start, end))
            .group_by(Task.scheduled_date)
        )
        counts = {day: (total, completed) for day, total, completed in rows}
        result = []
        for offset in range((end - start).days + 1):
            day = start + timedelta(days=offset)
            total, completed = counts.get(day, (0, 0))
            result.append(DailyStatistics(
                date=day, total=total, completed=completed, incomplete=total - completed,
                completion_rate=completion_rate(completed, total),
            ))
        return result

    def daily(self, day: date) -> DailyStatistics:
        ensure_accessible(day, self.today)
        return self._days(day, day)[0]

    def weekly(self) -> WeeklyStatistics:
        start = self.today - timedelta(days=6)
        days = self._days(start, self.today)
        total = sum(day.total for day in days)
        completed = sum(day.completed for day in days)
        return WeeklyStatistics(
            start_date=start, end_date=self.today, days=days, total=total,
            completed=completed, incomplete=total - completed,
            completion_rate=completion_rate(completed, total),
        )

    def calendar(self, year: int, month: int) -> CalendarSummary:
        return CalendarSummary(
            year=year, month=month,
            days=self._days(date(year, month, 1), date(year, month, monthrange(year, month)[1])),
        )
