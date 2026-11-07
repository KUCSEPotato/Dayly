from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from threading import Barrier

import pytest
from sqlalchemy import event, select, text
from sqlalchemy.exc import IntegrityError

from app.models import EventType, Task, TaskEvent
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate
from app.services.tasks import TaskService

DAY = date(2026, 11, 2)


def create(client):
    response = client.post("/api/tasks", json={"title": "처음 제목", "scheduled_date": str(DAY)})
    assert response.status_code == 201
    return response.json()


def log(database):
    with database() as session:
        return list(session.scalars(select(TaskEvent).order_by(TaskEvent.id)))


def test_all_event_types_full_snapshots_and_deleted_history_survives(client, database):
    created = create(client)
    path = f"/api/tasks/{created['id']}"
    updated = client.patch(path, json={"title": "수정 제목", "description": "설명", "scheduled_date": "2026-11-03"}).json()
    completed = client.patch(path, json={"is_completed": True}).json()
    uncompleted = client.patch(path, json={"is_completed": False}).json()
    assert client.delete(path).status_code == 204
    events = log(database)
    assert [item.event_type for item in events] == list(EventType)[:5]
    assert events[0].before_state is None
    assert events[0].after_state == created
    for previous, current in zip(events, events[1:]):
        assert current.before_state == previous.after_state
        assert current.id > previous.id
    assert [item.after_state for item in events] == [created, updated, completed, uncompleted, None]
    assert all(item.task_id == created["id"] and item.occurred_at.tzinfo == UTC for item in events)
    assert events[-1].before_state == uncompleted
    with database() as session:
        assert session.get(Task, created["id"]) is None


def test_no_change_does_not_touch_updated_at_or_create_events(client, database):
    task = create(client)
    path = f"/api/tasks/{task['id']}"
    for changes in ({"title": "  처음 제목  "}, {"is_completed": False},
                    {"description": None}, {"scheduled_date": str(DAY)}):
        response = client.patch(path, json=changes)
        assert response.status_code == 200
        assert response.json() == task
    assert len(log(database)) == 1
    completed = client.patch(path, json={"is_completed": True}).json()
    assert client.patch(path, json={"is_completed": True}).json() == completed
    assert len(log(database)) == 2


def test_combined_patch_is_one_completion_event_containing_all_changes(client, database):
    task = create(client)
    updated = client.patch(f"/api/tasks/{task['id']}", json={"title": "한 요청", "is_completed": True}).json()
    events = log(database)
    assert len(events) == 2
    assert events[-1].event_type == "COMPLETED"
    assert events[-1].before_state == task
    assert events[-1].after_state == updated


@pytest.mark.parametrize("operation", ["create", "update", "delete"])
def test_event_insert_failure_rolls_back_task_change(client, database, operation):
    original = create(client) if operation != "create" else None
    before = len(log(database))

    def fail(*args):
        raise RuntimeError("event write failed")

    event.listen(TaskEvent, "before_insert", fail)
    try:
        with pytest.raises(RuntimeError, match="event write failed"):
            if operation == "create":
                create(client)
            elif operation == "update":
                client.patch(f"/api/tasks/{original['id']}", json={"title": "취소될 수정"})
            else:
                client.delete(f"/api/tasks/{original['id']}")
    finally:
        event.remove(TaskEvent, "before_insert", fail)
    assert len(log(database)) == before
    assert client.get(f"/api/tasks?date={DAY}").json() == ([original] if original else [])


@pytest.mark.parametrize("operation,hook", [("create", "before_insert"), ("update", "before_update"), ("delete", "before_delete")])
def test_task_write_failure_rolls_back_event(client, database, operation, hook):
    original = create(client) if operation != "create" else None
    before = len(log(database))

    def fail(*args):
        raise RuntimeError("task write failed")

    event.listen(Task, hook, fail)
    try:
        with pytest.raises(RuntimeError, match="task write failed"):
            if operation == "create":
                create(client)
            elif operation == "update":
                client.patch(f"/api/tasks/{original['id']}", json={"title": "취소"})
            else:
                client.delete(f"/api/tasks/{original['id']}")
    finally:
        event.remove(Task, hook, fail)
    assert len(log(database)) == before
    assert client.get(f"/api/tasks?date={DAY}").json() == ([original] if original else [])


@pytest.mark.parametrize("sql", ["UPDATE task_events SET event_type='UPDATED'", "DELETE FROM task_events"])
def test_database_blocks_event_mutation_even_through_raw_sql(client, database, sql):
    create(client)
    with database() as session:
        with pytest.raises(IntegrityError, match="append-only"):
            session.execute(text(sql))
        session.rollback()
    assert len(log(database)) == 1


def test_orm_blocks_event_changes(client, database):
    create(client)
    with database() as session:
        record = session.scalar(select(TaskEvent))
        record.event_type = "UPDATED"
        with pytest.raises(ValueError, match="append-only"):
            session.commit()
        session.rollback()
        session.delete(session.scalar(select(TaskEvent)))
        with pytest.raises(ValueError, match="append-only"):
            session.commit()
        session.rollback()


def test_deleted_ids_are_not_reused(client, database):
    first = create(client)
    client.delete(f"/api/tasks/{first['id']}")
    second = create(client)
    assert second["id"] > first["id"]
    assert [item.task_id for item in log(database)] == [first["id"], first["id"], second["id"]]


def test_concurrent_writers_have_an_unbroken_snapshot_chain(database):
    with database() as session:
        task = TaskService(session, DAY).create(TaskCreate(title="시작", scheduled_date=DAY))
        task_id = task.id
    barrier = Barrier(2)

    def update(title):
        with database() as session:
            barrier.wait(timeout=5)
            TaskService(session, DAY).update(task_id, TaskUpdate(title=title))

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(update, ["첫 요청", "두 번째 요청"]))
    events = log(database)
    assert len(events) == 3
    assert events[1].before_state == events[0].after_state
    assert events[2].before_state == events[1].after_state
    with database() as session:
        assert TaskRead.model_validate(session.get(Task, task_id)).model_dump(mode="json") == events[-1].after_state
