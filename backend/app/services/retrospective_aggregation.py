from collections import defaultdict
from datetime import date, timedelta

from app.core.periods import Period
from app.models import HistoryCoverage
from app.schemas.task import TaskRead
from app.services.statistics import completion_rate
from app.services.task_history import TaskHistoryService


class RetrospectiveAggregator:
    """Per-date end-of-day truth, shared by snapshots and daily XP bonuses."""

    def __init__(self, session):
        self.session = session
        self.history = TaskHistoryService(session)
        self._days: dict[date, dict] = {}

    @property
    def started_at(self):
        return self.session.get(HistoryCoverage, 1).started_at

    def day(self, day: date) -> dict:
        if day in self._days:
            return self._days[day]
        from app.core.clock import seoul_day_bounds
        start, end = seoul_day_bounds(day)
        coverage = "unavailable" if end <= self.started_at else "partial" if start < self.started_at else "complete"
        tasks = [] if coverage == "unavailable" else [task for task in self.history.reconstruct(end) if task.scheduled_date == day]
        completed = [task for task in tasks if task.is_completed]
        incomplete = [task for task in tasks if not task.is_completed]
        known = coverage != "unavailable"
        result = {
            "date": day.isoformat(), "coverage": coverage,
            "total": len(tasks) if known else None,
            "completed": len(completed) if known else None,
            "incomplete": len(incomplete) if known else None,
            "completion_rate": completion_rate(len(completed), len(tasks)) if known else None,
            "completed_tasks": [task.model_dump(mode="json") for task in completed],
            "incomplete_tasks": [task.model_dump(mode="json") for task in incomplete],
        }
        self._days[day] = result
        return result

    def aggregate(self, period: Period) -> dict:
        days = [self.day(period.start + timedelta(days=index)) for index in range((period.end - period.start).days)]
        known = [day for day in days if day["coverage"] != "unavailable"]
        total = sum(day["total"] for day in known)
        completed = sum(day["completed"] for day in known)
        if not known:
            status = "unavailable"
        elif any(day["coverage"] != "complete" for day in days):
            status = "partial"
        else:
            status = "ready" if total else "no_activity"
        weeks = defaultdict(lambda: {"completed": 0, "total": 0})
        for day in known:
            value = date.fromisoformat(day["date"])
            monday = value - timedelta(days=value.weekday())
            weeks[monday]["completed"] += day["completed"]
            weeks[monday]["total"] += day["total"]
        week_stats = [{"start": max(start, period.start).isoformat(),
                       "end": min(start + timedelta(days=7), period.end).isoformat(), **counts,
                       "completion_rate": completion_rate(counts["completed"], counts["total"])}
                      for start, counts in sorted(weeks.items())]
        best = max(known, key=lambda item: item["completed"], default=None)
        best_week = max(week_stats, key=lambda item: item["completed"], default=None)
        return {
            "status": status, "total": total if known else None,
            "completed": completed if known else None, "incomplete": total - completed if known else None,
            "completion_rate": completion_rate(completed, total) if known else None,
            "data": {
                "completed_tasks": [task for day in days for task in day["completed_tasks"]],
                "incomplete_tasks": [task for day in days for task in day["incomplete_tasks"]],
                "days": [{key: value for key, value in day.items() if not key.endswith("_tasks")} for day in days],
                "weeks": week_stats,
                "best_day": best["date"] if best and best["completed"] else None,
                "best_week": best_week["start"] if best_week and best_week["completed"] else None,
                "recording_started_at": self.started_at.isoformat(),
            },
        }
