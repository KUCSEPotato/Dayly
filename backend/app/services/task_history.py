from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import as_utc
from app.models.task_event import TaskEvent
from app.schemas.task import TaskRead


class TaskHistoryService:
    """Read historical truth from events only, including tasks since deleted."""

    def __init__(self, session: Session):
        self.session = session

    def reconstruct(self, as_of: datetime) -> list[TaskRead]:
        """State immediately BEFORE as_of (exclusive), ordered by task ID.

        Tied timestamps are replayed by monotonically increasing event ID.
        There is intentionally no join/query against the current tasks table.
        """
        events = self.session.scalars(
            select(TaskEvent).where(TaskEvent.occurred_at < as_utc(as_of))
            .order_by(TaskEvent.occurred_at, TaskEvent.id)
        )
        states: dict[int, TaskRead] = {}
        for event in events:
            if event.after_state is None:
                states.pop(event.task_id, None)
            else:
                states[event.task_id] = TaskRead.model_validate(event.after_state)
        return [states[task_id] for task_id in sorted(states)]

    def events_between(self, start: datetime, end: datetime, task_id: int | None = None) -> list[TaskEvent]:
        """Changes in [start, end), suitable for future retrospective aggregation."""
        start, end = as_utc(start), as_utc(end)
        if start > end:
            raise ValueError("start must not be after end")
        statement = select(TaskEvent).where(
            TaskEvent.occurred_at >= start, TaskEvent.occurred_at < end,
        ).order_by(TaskEvent.occurred_at, TaskEvent.id)
        if task_id is not None:
            statement = statement.where(TaskEvent.task_id == task_id)
        return list(self.session.scalars(statement))
