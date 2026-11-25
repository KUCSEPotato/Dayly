from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import event, select, text
from sqlalchemy.exc import IntegrityError

from app.models import Tag, Task, TaskEvent
from app.schemas.tag import TagCreate
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate
from app.services.tags import TagService
from app.services.tasks import TaskService
from app.services.task_history import TaskHistoryService
from tests.test_retrospectives_growth import scenario  # shared historical clock fixture

DAY = date(2026, 11, 2)


def tag(client, name='Python', color='#7c956b'):
    response = client.post('/api/tags', json={'name': name, 'color': color})
    assert response.status_code == 201, response.text
    return response.json()


def task(client, **fields):
    response = client.post('/api/tasks', json={'title': '태그를 붙일 일', 'scheduled_date': str(DAY), **fields})
    assert response.status_code == 201, response.text
    return response.json()


def events(database):
    with database() as session:
        return list(session.scalars(select(TaskEvent).order_by(TaskEvent.id)))


def test_tag_normalization_search_palette_and_reuse(client):
    first = tag(client, '  Python  ', '#648ca6')
    assert first['name'] == 'Python'
    assert tag(client, 'pYTHON', '#bd7887') == first
    german = tag(client, 'Straße')
    assert tag(client, 'STRASSE') == german
    assert client.get('/api/tags?q= PYt ').json() == [first]
    literal = tag(client, '100%_done')
    assert client.get('/api/tags?q=%_').json() == [literal]
    assert len(client.get('/api/tags').json()) == 3
    assert tag(client, '가' * 30)['name'] == '가' * 30
    assert client.post('/api/tags', json={'name': '기본 색'}).json()['color'] == '#7c956b'


@pytest.mark.parametrize('payload', [
    {'name': ''}, {'name': ' \n\t '}, {'name': 'x' * 31}, {'name': None},
    {'name': 'X', 'color': '#000000'}, {'name': 'X', 'color': None},
    {'name': 'X', 'extra': 'no'}, {'color': '#7c956b'},
])
def test_invalid_tag_inputs(client, payload):
    assert client.post('/api/tags', json=payload).status_code == 422
    assert client.get('/api/tags').json() == []


def test_concurrent_duplicate_tag_creation(database):
    def create(name):
        with database() as session:
            return TagService(session).create(TagCreate(name=name)).id
    with ThreadPoolExecutor(max_workers=3) as executor:
        assert len(set(executor.map(create, ['Python', ' PYTHON ', 'python']))) == 1


def test_multiple_tags_omit_clear_noop_reuse_and_delete(client, database):
    a, b = tag(client), tag(client, 'Dayly', '#a183b5')
    original = task(client, tag_ids=[b['id'], a['id'], a['id']])
    assert original['tags'] == [a, b]
    path = f"/api/tasks/{original['id']}"
    assert client.patch(path, json={'tag_ids': [b['id'], a['id']]}).json() == original
    assert len(events(database)) == 1
    renamed = client.patch(path, json={'title': '제목만 수정'}).json()
    assert renamed['tags'] == [a, b]
    removed = client.patch(path, json={'tag_ids': [b['id']]}).json()
    assert removed['tags'] == [b]
    cleared = client.patch(path, json={'tag_ids': []}).json()
    assert cleared['tags'] == []
    assert events(database)[-1].before_state == removed
    assert events(database)[-1].after_state == cleared
    reused = task(client, tag_ids=[a['id']])
    assert client.delete(f"/api/tasks/{reused['id']}").status_code == 204
    assert client.get('/api/tags').json() == [a, b]
    assert events(database)[-1].before_state['tags'] == [a]
    with database() as session:
        assert session.execute(text('SELECT * FROM task_tags')).all() == []
    assert client.get(f'/api/tasks?date={DAY}').json() == [cleared]


@pytest.mark.parametrize('ids', [None, [0], [-1], ['1'], [True]])
def test_invalid_tag_ids(client, ids):
    original = task(client)
    assert client.post('/api/tasks', json={'title': 'invalid', 'scheduled_date': str(DAY), 'tag_ids': ids}).status_code == 422
    assert client.patch(f"/api/tasks/{original['id']}", json={'tag_ids': ids}).status_code == 422


def test_unknown_tag_rolls_back_all_fields_and_events(client, database):
    a = tag(client)
    original = task(client, tag_ids=[a['id']])
    assert client.post('/api/tasks', json={'title': '실패', 'scheduled_date': str(DAY), 'tag_ids': [999]}).status_code == 404
    assert client.patch(f"/api/tasks/{original['id']}", json={'title': '실패', 'tag_ids': [999]}).status_code == 404
    assert client.get(f'/api/tasks?date={DAY}').json() == [original]
    assert len(events(database)) == 1


@pytest.mark.parametrize('operation', ['assign', 'remove', 'create', 'postpone'])
def test_event_failure_rolls_back_tag_links_and_postpone(client, database, operation):
    a = tag(client)
    original = task(client, tag_ids=[a['id']] if operation == 'remove' else [])
    def fail(*args):
        raise RuntimeError('event failed')
    event.listen(TaskEvent, 'before_insert', fail)
    try:
        with pytest.raises(RuntimeError, match='event failed'):
            if operation == 'create':
                task(client, tag_ids=[a['id']])
            elif operation == 'postpone':
                client.post(f"/api/tasks/{original['id']}/postpone")
            else:
                client.patch(f"/api/tasks/{original['id']}", json={'tag_ids': [] if operation == 'remove' else [a['id']]})
    finally:
        event.remove(TaskEvent, 'before_insert', fail)
    assert client.get(f'/api/tasks?date={DAY}').json() == [original]
    assert len(events(database)) == 1
    assert client.get('/api/tags').json() == [a]


def test_association_composite_key_blocks_duplicates(client, database):
    a = tag(client)
    original = task(client, tag_ids=[a['id']])
    with database() as session:
        with pytest.raises(IntegrityError):
            session.execute(text('INSERT INTO task_tags VALUES (:task,:tag)'), {'task': original['id'], 'tag': a['id']})
        session.rollback()


def test_tag_history_is_self_contained_and_legacy_events_default_to_empty(client, database, monkeypatch):
    import app.services.tasks as module
    start = datetime(2026, 11, 2, 1, tzinfo=UTC)
    monkeypatch.setattr(module, 'utc_now', lambda: start)
    a = tag(client)
    original = task(client)
    monkeypatch.setattr(module, 'utc_now', lambda: start + timedelta(hours=1))
    assigned = client.patch(f"/api/tasks/{original['id']}", json={'tag_ids': [a['id']]}).json()
    # Simulate a future tag rename without rewriting events.
    with database() as session:
        row = session.get(Tag, a['id'])
        row.name, row.color = '나중 이름', '#648ca6'
        session.commit()
    with database() as session:
        history = TaskHistoryService(session)
        assert history.reconstruct(start + timedelta(minutes=1))[0].tags == []
        assert history.reconstruct(start + timedelta(hours=2))[0].model_dump(mode='json') == assigned
        legacy = {key: value for key, value in original.items() if key != 'tags'}
        session.add(TaskEvent(task_id=999, event_type='CREATED', after_state={**legacy, 'id': 999}, occurred_at=start))
        session.commit()
    with database() as session:
        assert TaskHistoryService(session).reconstruct(start + timedelta(seconds=1))[-1].tags == []


@pytest.mark.parametrize('day,next_day', [
    ('2026-11-02', '2026-11-03'), ('2026-11-30', '2026-12-01'),
    ('2026-12-31', '2027-01-01'), ('2028-02-28', '2028-02-29'),
    ('2028-02-29', '2028-03-01'), ('2027-02-28', '2027-03-01'),
])
def test_postpone_preserves_identity_tags_fields_and_updates_aggregates(client, database, day, next_day):
    a = tag(client)
    original = task(client, scheduled_date=day, tag_ids=[a['id']], description='보존할 설명')
    response = client.post(f"/api/tasks/{original['id']}/postpone")
    assert response.status_code == 200
    moved = response.json()
    assert moved == {**original, 'scheduled_date': next_day, 'updated_at': moved['updated_at']}
    assert moved['updated_at'] > original['updated_at']
    assert client.get(f'/api/tasks?date={day}').json() == []
    assert client.get(f'/api/tasks?date={next_day}').json() == [moved]
    assert client.get(f'/api/stats/daily?date={day}').json()['total'] == 0
    assert client.get(f'/api/stats/daily?date={next_day}').json()['total'] == 1
    year, month, day_number = map(int, day.split('-'))
    assert client.get(f'/api/calendar?year={year}&month={month}').json()['days'][day_number - 1]['total'] == 0
    assert client.get('/api/stats/weekly').json()['total'] == 0
    record = events(database)[-1]
    assert record.event_type == 'UPDATED' and record.change_reason == 'POSTPONED'
    assert record.before_state == original and record.after_state == moved
    with database() as session:
        history = TaskHistoryService(session)
        assert history.reconstruct(record.occurred_at)[0].model_dump(mode='json') == original
        assert history.reconstruct(record.occurred_at + timedelta(microseconds=1))[0].model_dump(mode='json') == moved


def test_postpone_rejects_completed_restricted_missing_and_overflow(client, database):
    original = task(client)
    client.patch(f"/api/tasks/{original['id']}", json={'is_completed': True})
    assert client.post(f"/api/tasks/{original['id']}/postpone").status_code == 403
    assert client.post('/api/tasks/999/postpone').status_code == 404
    assert client.post('/api/tasks/0/postpone').status_code == 422
    last = task(client, scheduled_date='9999-12-31')
    assert client.post(f"/api/tasks/{last['id']}/postpone").status_code == 403
    with database() as session:
        session.get(Task, original['id']).scheduled_date = date(2026, 1, 1)
        session.commit()
    assert client.post(f"/api/tasks/{original['id']}/postpone").status_code == 403
    assert len(events(database)) == 3


def test_snapshot_tag_changes_postpone_and_xp_compatibility(scenario, client, database, monkeypatch):
    import app.services.tasks as module
    a, b = tag(client), tag(client, 'Dayly')
    task_id = scenario(datetime(2026, 11, 2, 1, tzinfo=UTC), tag_ids=[a['id']])
    frozen = client.get('/api/retrospectives?kind=daily&date=2026-11-02').json()['items'][0]
    assert frozen['data']['incomplete_tasks'][0]['tags'] == [a]
    monkeypatch.setattr(module, 'utc_now', lambda: datetime(2026, 11, 3, 1, tzinfo=UTC))
    with database() as session:
        service = TaskService(session, date(2026, 11, 3))
        service.update(task_id, TaskUpdate(tag_ids=[b['id']]))
        service.postpone(task_id)
    assert client.get('/api/growth/summary').json()['total_xp'] == 0
    assert client.get(f"/api/retrospectives/{frozen['id']}").json() == frozen
    assert client.get('/api/retrospectives?kind=daily&date=2026-11-02').json()['items'][0] == frozen
    # Completion, undo, tags and postpone must not repay first-completion XP.
    scenario(datetime(2026, 11, 3, 2, tzinfo=UTC), 'update', task_id, is_completed=True)
    before = client.get('/api/growth/history?limit=100').json()
    scenario(datetime(2026, 11, 3, 3, tzinfo=UTC), 'update', task_id, is_completed=False, tag_ids=[])
    monkeypatch.setattr(module, 'utc_now', lambda: datetime(2026, 11, 3, 4, tzinfo=UTC))
    with database() as session:
        TaskService(session, date(2026, 11, 3)).postpone(task_id)
    scenario(datetime(2026, 11, 3, 5, tzinfo=UTC), 'update', task_id, is_completed=True)
    assert client.get('/api/growth/history?limit=100').json() == before
    assert client.get('/api/growth/summary').json()['total_xp'] == 30


def test_missing_snapshot_reconstructs_tags_and_schedule_before_later_postpone(scenario, client, database, monkeypatch):
    import app.services.tasks as module
    a = tag(client)
    task_id = scenario(datetime(2026, 11, 2, 1, tzinfo=UTC), tag_ids=[a['id']])
    scenario(datetime(2026, 11, 3, 1, tzinfo=UTC), 'update', task_id, tag_ids=[])
    monkeypatch.setattr(module, 'utc_now', lambda: datetime(2026, 11, 3, 2, tzinfo=UTC))
    with database() as session:
        TaskService(session, date(2026, 11, 3)).postpone(task_id)
    frozen = client.get('/api/retrospectives?kind=daily&date=2026-11-02').json()['items'][0]
    assert frozen['total'] == 1 and frozen['completion_rate'] == 0
    assert frozen['data']['incomplete_tasks'][0]['tags'] == [a]
    assert frozen['data']['incomplete_tasks'][0]['scheduled_date'] == '2026-11-02'
    assert client.get('/api/growth/summary').json()['total_xp'] == 0
