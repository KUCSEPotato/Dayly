from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import event, select

from app.models import TaskEvent
from app.services.task_history import TaskHistoryService


def create(client, day='2026-11-02'):
    tag = client.post('/api/tags', json={'name': 'Python'}).json()
    response = client.post('/api/tasks', json={'title': 'keep', 'description': 'same', 'scheduled_date': day, 'tag_ids': [tag['id']]})
    assert response.status_code == 201
    return response.json()


def log(database):
    with database() as session:
        return list(session.scalars(select(TaskEvent).order_by(TaskEvent.id)))


@pytest.mark.parametrize('body', [None, {}])
def test_default_next_day_backwards_compatibility(client, database, body):
    original = create(client)
    path = f"/api/tasks/{original['id']}/postpone"
    response = client.post(path) if body is None else client.post(path, json=body)
    assert response.status_code == 200
    assert response.json()['scheduled_date'] == '2026-11-03'
    assert len(log(database)) == 2


@pytest.mark.parametrize('before,after', [
    ('2026-11-02', '2026-11-05'), ('2026-11-30', '2026-12-03'),
    ('2026-12-31', '2027-01-03'), ('2028-02-28', '2028-03-02'),
    ('2028-02-29', '2028-03-03'), ('2027-02-28', '2027-03-03'),
])
def test_multi_day_move_has_one_event_and_preserves_every_other_field(client, database, before, after):
    original = create(client, before)
    response = client.post(f"/api/tasks/{original['id']}/postpone", json={'target_date': after})
    assert response.status_code == 200
    moved = response.json()
    assert moved == {**original, 'scheduled_date': after, 'updated_at': moved['updated_at']}
    records = log(database)
    assert len(records) == 2
    record = records[-1]
    assert record.change_reason == 'POSTPONED' and record.event_type == 'UPDATED'
    assert record.before_state == original and record.after_state == moved
    with database() as session:
        history = TaskHistoryService(session)
        assert history.reconstruct(record.occurred_at)[0].scheduled_date.isoformat() == before
        assert history.reconstruct(record.occurred_at + timedelta(microseconds=1))[0].scheduled_date.isoformat() == after


@pytest.mark.parametrize('body,status', [
    ({'target_date': '2026-11-02'}, 403), ({'target_date': '2026-11-01'}, 403),
    ({'target_date': 'invalid'}, 422), ({'target_date': '2027-02-29'}, 422),
    ({'target_date': None}, 422), ({'date': '2026-11-05'}, 422),
])
def test_invalid_targets_do_not_change_task_or_create_events(client, database, body, status):
    original = create(client)
    assert client.post(f"/api/tasks/{original['id']}/postpone", json=body).status_code == status
    assert client.get('/api/tasks?date=2026-11-02').json() == [original]
    assert len(log(database)) == 1


def test_completed_restriction_and_event_write_failure_are_atomic(client, database):
    original = create(client)
    path = f"/api/tasks/{original['id']}"
    client.patch(path, json={'is_completed': True})
    assert client.post(path + '/postpone', json={'target_date': '2026-11-05'}).status_code == 403
    client.patch(path, json={'is_completed': False})
    before = client.get('/api/tasks?date=2026-11-02').json()
    count = len(log(database))
    def fail(*args):
        raise RuntimeError('failed event')
    event.listen(TaskEvent, 'before_insert', fail)
    try:
        with pytest.raises(RuntimeError, match='failed event'):
            client.post(path + '/postpone', json={'target_date': '2026-11-05'})
    finally:
        event.remove(TaskEvent, 'before_insert', fail)
    assert client.get('/api/tasks?date=2026-11-02').json() == before
    assert len(log(database)) == count
