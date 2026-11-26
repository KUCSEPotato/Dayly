from copy import deepcopy
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import event, select, text

from app.core.clock import seoul_day_bounds
from app.core.periods import PeriodKind, resolve_period
from app.models import RetrospectiveSnapshot, Tag, TaskEvent
from app.services.retrospective_aggregation import RetrospectiveAggregator
from app.services.retrospective_analysis import RetrospectiveAnalysisService
from app.services.tasks import TaskService
from app.schemas.retrospective import RetrospectiveAnalysis
from tests.test_retrospectives_growth import scenario


def tag(client, name, color='#648ca6'):
    response = client.post('/api/tags', json={'name': name, 'color': color})
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def tracked(scenario, database, monkeypatch):
    # A format marker before the studied periods, on a future plan excluded from totals.
    scenario(datetime(2026, 1, 1, tzinfo=UTC), scheduled_date=date(2030, 1, 1))
    def move(at, task_id, target=None):
        import app.services.tasks as module
        monkeypatch.setattr(module, 'utc_now', lambda: at)
        with database() as session:
            return TaskService(session, at.astimezone(ZoneInfo('Asia/Seoul')).date()).postpone(task_id, target)
    return scenario, move


def snapshot(client, kind='daily', anchor='2026-11-02'):
    response = client.get(f'/api/retrospectives?kind={kind}&date={anchor}')
    assert response.status_code == 200, response.text
    return response.json()['items'][0]


@pytest.mark.parametrize('kind,anchor', [('daily', '2026-10-26'), ('weekly', '2026-10-28'), ('monthly', '2026-10-15')])
def test_tag_activity_is_weighted_multitag_and_historical(tracked, client, kind, anchor):
    write, _ = tracked
    python, dayly = tag(client, 'Python'), tag(client, 'Dayly', '#7c956b')
    first = write(datetime(2026, 10, 26, 1, tzinfo=UTC), tag_ids=[python['id'], dayly['id']])
    write(datetime(2026, 10, 26, 2, tzinfo=UTC), 'update', first, is_completed=True)
    for _ in range(9):
        write(datetime(2026, 10, 31, 1, tzinfo=UTC), tag_ids=[python['id']])
    write(datetime(2026, 10, 28, 1, tzinfo=UTC))
    write(datetime(2026, 11, 1, 1, tzinfo=UTC), 'update', first, tag_ids=[])
    result = snapshot(client, kind, anchor)
    analysis = result['data']['analysis']
    assert analysis['coverage']['status'] == 'complete'
    rows = {row['tag_id']: row for row in analysis['tag_activity']}
    assert rows[dayly['id']] == dict(tag_id=dayly['id'], name='Dayly', color='#7c956b', total=1, completed=1, incomplete=0, completion_rate=100)
    assert rows[python['id']]['completion_rate'] == (100 if kind == 'daily' else 10)
    assert rows[python['id']]['total'] == (1 if kind == 'daily' else 10)
    assert result['total'] == (1 if kind == 'daily' else 11)
    assert result['completed'] == 1
    assert sum(row['total'] for row in rows.values()) == result['total'] + 1
    if kind != 'daily':
        assert rows[None]['name'] == '태그 없음' and rows[None]['incomplete'] == 1
        assert result['completion_rate'] == 9.09


def test_same_named_tag_ids_are_not_merged_and_current_metadata_is_not_used(tracked, client, database):
    write, _ = tracked
    first, second = tag(client, 'One'), tag(client, 'Two')
    with database() as session:
        session.get(Tag, second['id']).name = 'One'
        session.commit()
    write(datetime(2026, 11, 2, 1, tzinfo=UTC), tag_ids=[first['id'], second['id']])
    with database() as session:
        row = session.get(Tag, first['id'])
        row.name, row.color = 'Later', '#bd7887'
        session.commit()
    rows = snapshot(client)['data']['analysis']['tag_activity']
    assert [row['tag_id'] for row in rows] == [first['id'], second['id']]
    assert all(row['name'] == 'One' and row['color'] == '#648ca6' for row in rows)


def test_existing_daily_occurrence_policy_is_preserved_when_task_moves_on_later_day(tracked, client):
    write, move = tracked
    python = tag(client, 'Python')
    task_id = write(datetime(2026, 10, 26, 1, tzinfo=UTC), tag_ids=[python['id']])
    move(datetime(2026, 10, 27, 1, tzinfo=UTC), task_id)
    result = snapshot(client, 'weekly', '2026-10-26')
    assert result['total'] == 2  # Oct 26 cutoff and Oct 27 cutoff each contain this plan.
    assert result['data']['analysis']['tag_activity'][0]['total'] == 2
    assert result['data']['analysis']['postponements'] == dict(
        postponed_tasks=1, total_postponements=1, postponed_days=1,
        by_tag=[dict(tag_id=python['id'], name='Python', color='#648ca6', postponed_tasks=1, total_postponements=1, postponed_days=1)])


def test_postponement_three_metrics_event_tags_and_deletion(tracked, client):
    write, move = tracked
    python, dayly = tag(client, 'Python'), tag(client, 'Dayly', '#7c956b')
    task_id = write(datetime(2026, 10, 26, 1, tzinfo=UTC), scheduled_date=date(2026, 11, 20), tag_ids=[python['id'], dayly['id']])
    move(datetime(2026, 10, 27, 1, tzinfo=UTC), task_id, date(2026, 11, 23))
    write(datetime(2026, 10, 28, 1, tzinfo=UTC), 'update', task_id, tag_ids=[dayly['id']])
    move(datetime(2026, 10, 28, 2, tzinfo=UTC), task_id, date(2026, 11, 25))
    # A normal date edit is not a postponement, including edits back in time.
    write(datetime(2026, 10, 29, 1, tzinfo=UTC), 'update', task_id, scheduled_date=date(2026, 11, 24))
    write(datetime(2026, 10, 30, 1, tzinfo=UTC), 'delete', task_id)
    other = write(datetime(2026, 10, 29, 1, tzinfo=UTC), scheduled_date=date(2026, 11, 20))
    move(datetime(2026, 10, 29, 2, tzinfo=UTC), other)
    result = snapshot(client, 'weekly', '2026-10-28')
    assert result['total'] == 0  # Event occurrence date, not either planned date.
    stats = result['data']['analysis']['postponements']
    assert (stats['postponed_tasks'], stats['total_postponements'], stats['postponed_days']) == (2, 3, 6)
    rows = {row['tag_id']: row for row in stats['by_tag']}
    assert rows[python['id']]['postponed_tasks'] == 1
    assert (rows[python['id']]['total_postponements'], rows[python['id']]['postponed_days']) == (1, 3)
    assert (rows[dayly['id']]['total_postponements'], rows[dayly['id']]['postponed_days']) == (2, 5)
    assert rows[None]['total_postponements'] == 1 and rows[None]['postponed_days'] == 1


def test_three_then_two_days_is_one_task_two_events_five_days(tracked, client):
    write, move = tracked
    task_id = write(datetime(2026, 11, 2, 0, tzinfo=UTC))
    move(datetime(2026, 11, 2, 1, tzinfo=UTC), task_id, date(2026, 11, 5))
    move(datetime(2026, 11, 2, 2, tzinfo=UTC), task_id, date(2026, 11, 7))
    stats = snapshot(client)['data']['analysis']['postponements']
    assert (stats['postponed_tasks'], stats['total_postponements'], stats['postponed_days']) == (1, 2, 5)


def test_legacy_one_day_requests_are_counted_individually_without_grouping(tracked, client):
    write, move = tracked
    task_id = write(datetime(2026, 11, 2, 0, tzinfo=UTC))
    for hour in range(1, 4):
        move(datetime(2026, 11, 2, hour, tzinfo=UTC), task_id)
    stats = snapshot(client)['data']['analysis']['postponements']
    assert (stats['postponed_tasks'], stats['total_postponements'], stats['postponed_days']) == (1, 3, 3)


def test_seoul_event_period_boundaries_are_half_open(tracked, client):
    write, move = tracked
    start, end = seoul_day_bounds(date(2026, 11, 2))
    task_id = write(start - timedelta(hours=2), scheduled_date=date(2026, 11, 20))
    move(start - timedelta(microseconds=1), task_id)
    move(start, task_id, date(2026, 11, 24))
    move(end - timedelta(microseconds=1), task_id, date(2026, 11, 26))
    move(end, task_id)
    stats = snapshot(client)['data']['analysis']['postponements']
    assert (stats['postponed_tasks'], stats['total_postponements'], stats['postponed_days']) == (1, 2, 5)


def test_full_coverage_empty_days_are_real_zeroes(tracked, client):
    result = snapshot(client)
    assert result['status'] == 'no_activity'
    analysis = result['data']['analysis']
    assert analysis['coverage']['status'] == 'complete'
    assert analysis['tag_activity'] == []
    assert analysis['postponements'] == dict(postponed_tasks=0, total_postponements=0, postponed_days=0, by_tag=[])


def test_legacy_unknown_and_partial_periods_are_not_reported_as_zero(scenario, client, database):
    state = dict(id=900, title='옛 기록', description=None, scheduled_date='2026-11-01', is_completed=False,
                 created_at='2026-10-31T01:00:00Z', updated_at='2026-10-31T01:00:00Z', completed_at=None)
    with database() as session:
        session.add(TaskEvent(task_id=900, event_type='BASELINE', after_state=state, occurred_at=datetime(2026, 10, 31, 1, tzinfo=UTC)))
        session.commit()
    unknown = snapshot(client, anchor='2026-11-01')
    assert unknown['total'] == 1
    assert unknown['data']['analysis']['coverage']['status'] == 'unavailable'
    assert unknown['data']['analysis']['postponements']['total_postponements'] is None
    scenario(datetime(2026, 11, 2, 1, tzinfo=UTC))
    partial = snapshot(client)
    assert partial['data']['analysis']['coverage']['status'] == 'partial'
    assert partial['data']['analysis']['tag_activity'] == []
    assert partial['data']['analysis']['postponements']['postponed_days'] is None
    complete = snapshot(client, anchor='2026-11-03')
    assert complete['data']['analysis']['coverage']['status'] == 'complete'
    assert complete['data']['analysis']['postponements']['total_postponements'] == 0


def test_snapshot_analysis_is_persisted_and_immutable_with_original_xp(tracked, client, database):
    write, move = tracked
    python = tag(client, 'Python')
    task_id = write(datetime(2026, 11, 2, 0, tzinfo=UTC), tag_ids=[python['id']])
    move(datetime(2026, 11, 2, 1, tzinfo=UTC), task_id, date(2026, 11, 5))
    result = snapshot(client)
    before = client.get('/api/growth/history?limit=100').json()
    with database() as session:
        stored_before = deepcopy(session.get(RetrospectiveSnapshot, result['id']).data)
    write(datetime(2026, 11, 3, 1, tzinfo=UTC), 'update', task_id, tag_ids=[], title='나중 제목')
    write(datetime(2026, 11, 3, 2, tzinfo=UTC), 'delete', task_id)
    assert client.get(f"/api/retrospectives/{result['id']}").json() == result
    assert snapshot(client) == result
    assert client.get('/api/growth/history?limit=100').json() == before
    with database() as session:
        stored = session.get(RetrospectiveSnapshot, result['id'])
        assert stored.data == stored_before
        assert RetrospectiveAnalysis.model_validate(stored.data['analysis']).model_dump(mode='json') == result['data']['analysis']


def test_old_snapshot_has_no_analysis_backfill_or_response_field(tracked, client, database, monkeypatch):
    write, _ = tracked
    task_id = write(datetime(2026, 11, 2, 1, tzinfo=UTC))
    with database() as session:
        values = RetrospectiveAggregator(session).aggregate(resolve_period(PeriodKind.DAILY, date(2026, 11, 4), date(2026, 11, 2)))
        values['data'].pop('analysis')
        values['data'].update(activity={'unique_completed_tasks': 0, 'task_ids': []}, xp_policy={'version': 'v0.2.1-provisional'})
        legacy = RetrospectiveSnapshot(kind='daily', period_start=date(2026, 11, 2), period_end=date(2026, 11, 3), created_at=datetime(2026, 11, 3, tzinfo=UTC), xp_total=0, **values)
        session.add(legacy)
        session.commit()
        snapshot_id, original_data = legacy.id, deepcopy(legacy.data)
    def fail(*args):
        raise AssertionError('must not analyze an existing snapshot')
    monkeypatch.setattr(RetrospectiveAnalysisService, 'build', fail)
    original = client.get(f'/api/retrospectives/{snapshot_id}').json()
    assert 'analysis' not in original['data']
    write(datetime(2026, 11, 3, 1, tzinfo=UTC), 'update', task_id, title='changed')
    assert snapshot(client) == original
    with database() as session:
        assert session.get(RetrospectiveSnapshot, snapshot_id).data == original_data


def test_analysis_reuses_day_states_and_does_not_query_current_tasks_or_tags(tracked, client, database, monkeypatch):
    write, _ = tracked
    write(datetime(2026, 11, 2, 1, tzinfo=UTC))
    with database() as session:
        aggregator = RetrospectiveAggregator(session)
        aggregator.day(date(2026, 11, 2))
        def fail(*args):
            raise AssertionError('day must be cached')
        monkeypatch.setattr(aggregator.history, 'reconstruct', fail)
        statements = []
        def capture(connection, cursor, statement, parameters, context, executemany):
            statements.append(statement)
        event.listen(session.bind, 'before_cursor_execute', capture)
        try:
            result = aggregator.aggregate(resolve_period(PeriodKind.DAILY, date(2026, 11, 4), date(2026, 11, 2)))
        finally:
            event.remove(session.bind, 'before_cursor_execute', capture)
        assert result['data']['analysis']['coverage']['status'] == 'complete'
        assert all('FROM tasks' not in sql and 'FROM tags' not in sql for sql in statements)
        assert sum('FROM task_events' in sql for sql in statements) == 1


def test_multi_day_postpone_neither_awards_xp_nor_repays_first_completion(tracked, client):
    write, move = tracked
    task_id = write(datetime(2026, 11, 2, 0, tzinfo=UTC), scheduled_date=date(2026, 11, 5))
    move(datetime(2026, 11, 2, 1, tzinfo=UTC), task_id, date(2026, 11, 8))
    assert client.get('/api/growth/summary').json()['total_xp'] == 0
    write(datetime(2026, 11, 2, 2, tzinfo=UTC), 'update', task_id, is_completed=True)
    before = client.get('/api/growth/history?limit=100').json()
    assert client.get('/api/growth/summary').json()['total_xp'] == 10
    write(datetime(2026, 11, 3, 1, tzinfo=UTC), 'update', task_id, is_completed=False)
    move(datetime(2026, 11, 3, 2, tzinfo=UTC), task_id, date(2026, 11, 10))
    write(datetime(2026, 11, 3, 3, tzinfo=UTC), 'update', task_id, is_completed=True)
    assert client.get('/api/growth/summary').json()['total_xp'] == 10
    assert client.get('/api/growth/history?limit=100').json() == before
