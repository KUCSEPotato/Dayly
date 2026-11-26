from datetime import date, datetime

from app.core.periods import Period
from app.services.statistics import completion_rate
from app.services.task_history import TaskHistoryService


def historical_tags(state: dict) -> list[dict]:
    """Deduplicate by stored ID; never look up today's tag metadata."""
    tags = {tag["id"]: {"tag_id": tag["id"], "name": tag["name"], "color": tag["color"]}
            for tag in state.get("tags", [])}
    return list(tags.values()) or [{"tag_id": None, "name": "태그 없음", "color": None}]


class RetrospectiveAnalysisService:
    """Freeze analyses from already reconstructed days and a single event-range read."""

    def __init__(self, history: TaskHistoryService, history_started_at: datetime):
        self.history = history
        self.history_started_at = history_started_at

    def build(self, period: Period, days: list[dict]) -> dict:
        events = (self.history.events_between(self.history_started_at, period.end_at)
                  if self.history_started_at < period.end_at else [])
        # v0.2.2 introduced both tags in every new event state and explicit POSTPONED
        # reasons. Its rollout time was not stored: use the first observable format
        # marker conservatively, rather than inventing zeroes for legacy periods.
        started_at = next((event.occurred_at for event in events
                           if any(state is not None and "tags" in state
                                  for state in (event.before_state, event.after_state))), None)
        status = ("unavailable" if started_at is None else
                  "partial" if started_at > period.start_at else "complete")
        result = {
            "version": "v0.2.3",
            "coverage": {"status": status, "recording_started_at": started_at.isoformat() if started_at else None},
            "tag_activity": [],
            "postponements": {"postponed_tasks": None, "total_postponements": None,
                               "postponed_days": None, "by_tag": []},
        }
        # A partial period is explicitly unavailable for full-period numeric analysis.
        # Main retrospective totals keep their existing partial-coverage policy.
        if status != "complete":
            return result

        activity = {}
        for day in days:
            for field, completed in (("completed_tasks", True), ("incomplete_tasks", False)):
                for task in day[field]:
                    for tag in historical_tags(task):
                        row = activity.setdefault(tag["tag_id"], {**tag, "total": 0, "completed": 0})
                        row.update(tag)
                        row["total"] += 1
                        row["completed"] += int(completed)
        result["tag_activity"] = sorted([
            {**row, "incomplete": row["total"] - row["completed"],
             "completion_rate": completion_rate(row["completed"], row["total"])}
            for row in activity.values()
        ], key=lambda row: (-row["completed"], -row["total"], row["tag_id"] is None, row["tag_id"] or 0))

        task_ids, count, postponed_days, by_tag = set(), 0, 0, {}
        for event in events:
            if (event.occurred_at < period.start_at or event.event_type != "UPDATED"
                    or event.change_reason != "POSTPONED" or not event.before_state or not event.after_state):
                continue
            before, after = event.before_state, event.after_state
            delta = (date.fromisoformat(after["scheduled_date"]) - date.fromisoformat(before["scheduled_date"])).days
            if delta <= 0:
                continue
            task_ids.add(event.task_id)
            count += 1
            postponed_days += delta
            for tag in historical_tags(before):
                row = by_tag.setdefault(tag["tag_id"], {**tag, "task_ids": set(),
                                                       "total_postponements": 0, "postponed_days": 0})
                row.update(tag)
                row["task_ids"].add(event.task_id)
                row["total_postponements"] += 1
                row["postponed_days"] += delta
        result["postponements"] = {
            "postponed_tasks": len(task_ids), "total_postponements": count, "postponed_days": postponed_days,
            "by_tag": sorted([
                {**{key: value for key, value in row.items() if key != "task_ids"},
                 "postponed_tasks": len(row["task_ids"])} for row in by_tag.values()
            ], key=lambda row: (-row["total_postponements"], -row["postponed_tasks"],
                                -row["postponed_days"], row["tag_id"] is None, row["tag_id"] or 0)),
        }
        return result
