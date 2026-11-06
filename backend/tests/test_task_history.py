from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import event

from app.core.clock import seoul_day_bounds
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.task_history import TaskHistoryService
from app.services.tasks import TaskService

DAY = date(2026, 11, 2)
START = datetime(2026, 11, 2, 14, 59, tzinfo=UTC)


def timeline(database, monkeypatch, times):
    import app.services.tasks as module
    moments = iter(times)
    monkeypatch.setattr(module, "utc_now", lambda: next(moments))
    with database() as session:
        service = TaskService(session, DAY)
        task = service.create(TaskCreate(title="최초", description="원본", scheduled_date=DAY))
        task_id = task.id
        service.update(task_id, TaskUpdate(title="첫 수정", scheduled_date=date(2026, 11, 3)))
        service.update(task_id, TaskUpdate(title="둘째 수정", description=None))
        service.update(task_id, TaskUpdate(is_completed=True))
        service.update(task_id, TaskUpdate(is_completed=False))
        service.delete(task_id)
    return task_id


def test_reconstruction_of_every_transition_reads_events_not_current_tasks(database, monkeypatch):
    times = [START + timedelta(minutes=index) for index in range(6)]
    task_id = timeline(database, monkeypatch, times)
    statements = []

    def capture(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    with database() as session:
        event.listen(session.bind, "before_cursor_execute", capture)
        try:
            history = TaskHistoryService(session)
            assert history.reconstruct(START) == []  # Cutoff is exclusive.
            assert history.reconstruct(START - timedelta(seconds=1)) == []
            states = [history.reconstruct(moment + timedelta(microseconds=1)) for moment in times]
            assert states[0][0].id == task_id
            assert states[0][0].title == "최초"
            assert states[0][0].description == "원본"
            assert states[0][0].scheduled_date == DAY
            assert states[1][0].title == "첫 수정"
            assert str(states[1][0].scheduled_date) == "2026-11-03"
            assert states[2][0].title == "둘째 수정" and states[2][0].description is None
            assert states[2][0].is_completed is False
            assert states[3][0].is_completed is True
            assert states[3][0].completed_at == times[3]
            assert states[4][0].is_completed is False and states[4][0].completed_at is None
            assert states[5] == []
            # Exactly at the delete timestamp, the state immediately before delete exists.
            assert history.reconstruct(times[5])[0].title == "둘째 수정"
        finally:
            event.remove(session.bind, "before_cursor_execute", capture)
    assert statements
    assert all("FROM tasks" not in statement for statement in statements)


def test_same_timestamp_is_replayed_in_event_id_order(database, monkeypatch):
    timeline(database, monkeypatch, [START] * 5 + [START + timedelta(seconds=1)])
    with database() as session:
        result = TaskHistoryService(session).reconstruct(START + timedelta(microseconds=1))
        assert len(result) == 1
        assert result[0].title == "둘째 수정"
        assert result[0].is_completed is False
        assert result[0].completed_at is None


def test_seoul_boundaries_and_half_open_ranges(database, monkeypatch):
    # Seoul midnight is 15:00 UTC on the previous calendar day.
    midnight = datetime(2026, 11, 2, 15, tzinfo=UTC)
    times = [midnight - timedelta(seconds=1), midnight, midnight + timedelta(seconds=1),
             midnight + timedelta(seconds=2), midnight + timedelta(seconds=3),
             midnight + timedelta(days=1)]
    task_id = timeline(database, monkeypatch, times)
    start, end = seoul_day_bounds(date(2026, 11, 3))
    assert start == midnight
    assert end == midnight + timedelta(days=1)
    with database() as session:
        history = TaskHistoryService(session)
        changes = history.events_between(start, end, task_id)
        assert [item.event_type for item in changes] == ["UPDATED", "UPDATED", "COMPLETED", "UNCOMPLETED"]
        assert history.events_between(start, start) == []
        assert history.events_between(start, end, task_id + 1) == []
        local_cutoff = midnight.astimezone(ZoneInfo("Asia/Seoul"))
        assert history.reconstruct(local_cutoff) == history.reconstruct(midnight)
        assert history.reconstruct(midnight)[0].title == "최초"
        with pytest.raises(ValueError):
            history.events_between(end, start)


def test_naive_cutoffs_are_rejected(database):
    with database() as session:
        history = TaskHistoryService(session)
        with pytest.raises(ValueError, match="timezone-aware"):
            history.reconstruct(datetime(2026, 11, 2))
        with pytest.raises(ValueError, match="timezone-aware"):
            history.events_between(datetime(2026, 11, 2), START)
