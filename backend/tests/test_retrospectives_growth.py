from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import event, func, select, text
from sqlalchemy.exc import IntegrityError

from app.core.clock import seoul_day_bounds, utc_now
from app.core.config import Settings
from app.core.periods import PeriodKind, resolve_period
from app.main import app
from app.models import ExperienceGrant, HistoryCoverage, RetrospectiveSnapshot, TaskEvent
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.growth import GrowthService
from app.services.retrospectives import RetrospectiveService
from app.services.tasks import TaskService

NOW = datetime(2026, 11, 4, 3, tzinfo=UTC)


@pytest.fixture
def scenario(database, client, monkeypatch):
    with database() as session:
        session.get(HistoryCoverage, 1).started_at = datetime(2026, 1, 1, tzinfo=UTC)
        session.commit()
    app.dependency_overrides[utc_now] = lambda: NOW

    def write(at, operation="create", task_id=None, **fields):
        import app.services.tasks as module
        monkeypatch.setattr(module, "utc_now", lambda: at)
        today = at.astimezone(ZoneInfo("Asia/Seoul")).date()
        with database() as session:
            service = TaskService(session, today)
            if operation == "create":
                task = service.create(TaskCreate(title=fields.pop("title", "기록할 일"), scheduled_date=fields.pop("scheduled_date", today), **fields))
                return task.id
            if operation == "update":
                service.update(task_id, TaskUpdate(**fields))
            else:
                service.delete(task_id)
    yield write
    app.dependency_overrides.pop(utc_now, None)


@pytest.mark.parametrize("kind,today,start,end", [
    ("daily", "2026-01-01", "2025-12-31", "2026-01-01"),
    ("weekly", "2026-11-02", "2026-10-26", "2026-11-02"),
    ("weekly", "2026-11-08", "2026-10-26", "2026-11-02"),
    ("monthly", "2028-03-01", "2028-02-01", "2028-03-01"),
    ("monthly", "2027-03-01", "2027-02-01", "2027-03-01"),
    ("monthly", "2026-05-01", "2026-04-01", "2026-05-01"),
    ("monthly", "2026-01-01", "2025-12-01", "2026-01-01"),
])
def test_calendar_period_boundaries(kind, today, start, end):
    period = resolve_period(PeriodKind(kind), date.fromisoformat(today))
    assert str(period.start) == start and str(period.end) == end
    assert period.start_at == seoul_day_bounds(date.fromisoformat(start))[0]
    assert period.end_at == seoul_day_bounds(date.fromisoformat(end))[0]


def test_daily_snapshot_late_completion_edit_delete_and_xp_are_independent(scenario, client):
    task_id = scenario(datetime(2026, 11, 2, 1, tzinfo=UTC), title="그날의 제목")
    first = client.get('/api/retrospectives?kind=daily&date=2026-11-02').json()['items'][0]
    assert first['status'] == 'ready' and first['completion_rate'] == 0
    assert first['incomplete'] == 1 and first['xp_total'] == 0
    scenario(datetime(2026, 11, 3, 1, tzinfo=UTC), 'update', task_id, title="나중 제목", is_completed=True)
    scenario(datetime(2026, 11, 3, 2, tzinfo=UTC), 'delete', task_id)
    assert client.get(f"/api/retrospectives/{first['id']}").json() == first
    assert client.get('/api/retrospectives?kind=daily&date=2026-11-02').json()['items'][0] == first
    later = client.get('/api/retrospectives?kind=daily&date=2026-11-03').json()['items'][0]
    assert later['status'] == 'no_activity' and later['completion_rate'] is None
    assert later['xp_total'] == 10 and later['data']['activity']['unique_completed_tasks'] == 1
    assert first['data']['incomplete_tasks'][0]['title'] == '그날의 제목'


def test_weekly_is_weighted_from_each_daily_cutoff(scenario, client):
    first = scenario(datetime(2026, 10, 26, 1, tzinfo=UTC))
    scenario(datetime(2026, 10, 26, 2, tzinfo=UTC), 'update', first, is_completed=True)
    for _ in range(9):
        scenario(datetime(2026, 11, 1, 1, tzinfo=UTC))
    # Completing on Monday cannot change Sunday's final plan statistics.
    response = client.get('/api/retrospectives?kind=weekly&date=2026-10-28')
    assert response.status_code == 200
    week = response.json()['items'][0]
    assert week['period_start'] == '2026-10-26' and week['period_end'] == '2026-11-02'
    assert week['total'] == 10 and week['completed'] == 1 and week['completion_rate'] == 10
    assert week['data']['best_day'] == '2026-10-26'
    daily = [client.get(f"/api/retrospectives?kind=daily&date={day['date']}").json()['items'][0] for day in week['data']['days']]
    assert sum(day['total'] for day in daily) == week['total']
    assert sum(day['completed'] for day in daily) == week['completed']
    assert sum(day['xp_total'] for day in daily) == week['xp_total']


def test_month_has_real_days_and_week_groups(scenario, client):
    task = scenario(datetime(2026, 10, 31, 1, tzinfo=UTC))
    scenario(datetime(2026, 10, 31, 2, tzinfo=UTC), 'update', task, is_completed=True)
    month = client.get('/api/retrospectives?kind=monthly&date=2026-10-10').json()['items'][0]
    assert len(month['data']['days']) == 31
    assert month['total'] == 1 and month['completion_rate'] == 100
    assert month['data']['weeks'][-1]['end'] == '2026-11-01'
    assert month['data']['best_day'] == '2026-10-31'
    assert sum(week['completed'] for week in month['data']['weeks']) == 1


def test_coverage_distinguishes_unknown_partial_empty_and_unfinished(scenario, database, client):
    with database() as session:
        session.get(HistoryCoverage, 1).started_at = datetime(2026, 11, 2, 3, tzinfo=UTC)
        session.commit()
    unavailable = client.get('/api/retrospectives?kind=daily&date=2026-11-01').json()['items'][0]
    partial = client.get('/api/retrospectives?kind=daily&date=2026-11-02').json()['items'][0]
    empty = client.get('/api/retrospectives?kind=daily&date=2026-11-03').json()['items'][0]
    unfinished = client.get('/api/retrospectives?kind=daily&date=2026-11-04').json()
    assert unavailable['status'] == 'unavailable' and unavailable['total'] is None
    assert partial['status'] == 'partial'
    assert empty['status'] == 'no_activity' and empty['total'] == 0
    assert unfinished['status'] == 'not_ended' and unfinished['items'] == []
    assert client.get('/api/retrospectives?kind=weekly&date=2026-11-02').json()['status'] == 'not_ended'
    assert client.get('/api/retrospectives?kind=monthly&date=2026-11-01').json()['status'] == 'not_ended'


def test_existing_snapshot_returns_without_replay(scenario, client, monkeypatch):
    first = client.get('/api/retrospectives?kind=daily&date=2026-11-02').json()['items'][0]
    def fail(*args):
        raise AssertionError('Snapshot must not be recalculated')
    monkeypatch.setattr(GrowthService, 'sync_in_transaction', fail)
    assert client.get('/api/retrospectives?kind=daily&date=2026-11-02').json()['items'][0] == first
    assert client.get(f"/api/retrospectives/{first['id']}").json() == first


def test_concurrent_snapshot_generation_is_unique(scenario, database):
    task = scenario(datetime(2026, 11, 2, 1, tzinfo=UTC))
    scenario(datetime(2026, 11, 2, 2, tzinfo=UTC), 'update', task, is_completed=True)
    def request(_):
        with database() as session:
            return RetrospectiveService(session, NOW).list(PeriodKind.DAILY, date(2026, 11, 2)).items[0].id
    with ThreadPoolExecutor(max_workers=3) as executor:
        ids = list(executor.map(request, range(3)))
    assert len(set(ids)) == 1
    with database() as session:
        assert session.scalar(select(func.count()).select_from(RetrospectiveSnapshot)) == 1
        assert session.scalar(select(func.sum(ExperienceGrant.amount))) == 30


def test_snapshot_failure_rolls_back_snapshot_and_new_xp(scenario, client, database):
    task = scenario(datetime(2026, 11, 2, 1, tzinfo=UTC))
    scenario(datetime(2026, 11, 2, 2, tzinfo=UTC), 'update', task, is_completed=True)
    def fail(*args):
        raise RuntimeError('snapshot save failed')
    event.listen(RetrospectiveSnapshot, 'before_insert', fail)
    try:
        with pytest.raises(RuntimeError, match='snapshot save failed'):
            client.get('/api/retrospectives?kind=daily&date=2026-11-02')
    finally:
        event.remove(RetrospectiveSnapshot, 'before_insert', fail)
    with database() as session:
        assert session.scalar(select(func.count()).select_from(RetrospectiveSnapshot)) == 0
        assert session.scalar(select(func.count()).select_from(ExperienceGrant)) == 0


@pytest.mark.parametrize('completed,total,expected', [(0, 2, 0), (1, 3, 10), (1, 2, 20), (1, 1, 30)])
def test_daily_xp_bonus_policy(scenario, client, completed, total, expected):
    for index in range(total):
        task = scenario(datetime(2026, 11, 2, 1, tzinfo=UTC))
        if index < completed:
            scenario(datetime(2026, 11, 2, 2, tzinfo=UTC), 'update', task, is_completed=True)
    assert client.get('/api/growth/summary').json()['total_xp'] == expected
    assert sum(item['amount'] for item in client.get('/api/growth/history?limit=100').json()['items']) == expected
    assert client.get('/api/growth/summary').json()['total_xp'] == expected


def test_daily_cap_and_repeated_completion_do_not_farm_xp(scenario, client):
    ids = []
    for _ in range(12):
        task = scenario(datetime(2026, 11, 2, 1, tzinfo=UTC))
        ids.append(task)
        scenario(datetime(2026, 11, 2, 2, tzinfo=UTC), 'update', task, is_completed=True)
    first = client.get('/api/growth/summary').json()
    assert first['total_xp'] == 100 and first['level'] == 2 and first['xp_to_next_level'] == 200
    for task in ids:
        scenario(datetime(2026, 11, 3, 1, tzinfo=UTC), 'update', task, is_completed=False)
        scenario(datetime(2026, 11, 3, 2, tzinfo=UTC), 'update', task, is_completed=True)
    assert client.get('/api/growth/summary').json() == first
    assert client.get('/api/growth/history?limit=1').json()['total'] == 13  # 12 first claims + capped day bonus.


@pytest.mark.parametrize('total,level,next_xp', [(0, 1, 100), (99, 1, 1), (100, 2, 200), (299, 2, 1), (300, 3, 300), (600, 4, 400)])
def test_levels_and_new_sessions_preserve_ledger(scenario, database, total, level, next_xp):
    with database() as session:
        session.add(ExperienceGrant(dedup_key='fixture', reason='TASK_COMPLETED', amount=total,
            earned_date=date(2026, 11, 2), occurred_at=NOW, created_at=NOW, policy_version='test'))
        session.commit()
    with database() as session:
        summary = GrowthService(session, NOW).summary()
        assert summary.total_xp == total and summary.level == level and summary.xp_to_next_level == next_xp


@pytest.mark.parametrize('table', ['retrospective_snapshots', 'experience_grants'])
def test_database_rejects_snapshot_and_ledger_mutations(scenario, client, database, table):
    task = scenario(datetime(2026, 11, 2, 1, tzinfo=UTC))
    scenario(datetime(2026, 11, 2, 2, tzinfo=UTC), 'update', task, is_completed=True)
    client.get('/api/retrospectives?kind=daily&date=2026-11-02')
    with database() as session:
        for sql in (f'DELETE FROM {table}', f'UPDATE {table} SET id=id'):
            with pytest.raises(IntegrityError, match='immutable'):
                session.execute(text(sql))
            session.rollback()


def test_api_validation_and_detail_not_found(client):
    assert client.get('/api/retrospectives/999').status_code == 404
    for path in ('/api/retrospectives?kind=yearly', '/api/retrospectives?date=bad',
                 '/api/retrospectives?limit=0', '/api/growth/history?offset=-1'):
        assert client.get(path).status_code == 422


def test_exact_seoul_midnight_excludes_boundary_completion(scenario, client):
    boundary = datetime(2026, 11, 2, 15, tzinfo=UTC)
    task = scenario(boundary - timedelta(hours=2))
    scenario(boundary, 'update', task, is_completed=True)
    app.dependency_overrides[utc_now] = lambda: boundary - timedelta(microseconds=1)
    assert client.get('/api/retrospectives?kind=daily&date=2026-11-02').json()['status'] == 'not_ended'
    app.dependency_overrides[utc_now] = lambda: boundary
    snapshot = client.get('/api/retrospectives?kind=daily&date=2026-11-02').json()['items'][0]
    assert snapshot['completed'] == 0 and snapshot['completion_rate'] == 0


def test_xp_failure_is_atomic_and_can_be_retried(scenario, client, database):
    task = scenario(datetime(2026, 11, 2, 1, tzinfo=UTC))
    scenario(datetime(2026, 11, 2, 2, tzinfo=UTC), 'update', task, is_completed=True)
    def fail(*args):
        raise RuntimeError('xp insert failed')
    event.listen(ExperienceGrant, 'before_insert', fail)
    try:
        with pytest.raises(RuntimeError, match='xp insert failed'):
            client.get('/api/growth/summary')
    finally:
        event.remove(ExperienceGrant, 'before_insert', fail)
    with database() as session:
        assert session.scalar(select(func.count()).select_from(ExperienceGrant)) == 0
        assert session.scalar(select(func.count()).select_from(TaskEvent)) == 2
    assert client.get('/api/growth/summary').json()['total_xp'] == 30


def test_concurrent_growth_reads_and_config_changes_do_not_repay(scenario, database):
    task = scenario(datetime(2026, 11, 2, 1, tzinfo=UTC))
    scenario(datetime(2026, 11, 2, 2, tzinfo=UTC), 'update', task, is_completed=True)
    settings = Settings(xp_task_points=3, xp_bonus_full=2, xp_daily_cap=7, xp_level_step=4)
    def request(_):
        with database() as session:
            return GrowthService(session, NOW, settings).summary().total_xp
    with ThreadPoolExecutor(max_workers=3) as executor:
        assert list(executor.map(request, range(3))) == [5, 5, 5]
    with database() as session:
        assert GrowthService(session, NOW, Settings(xp_task_points=100, xp_bonus_full=100)).summary().total_xp == 5


def test_completed_baseline_does_not_invent_an_earlier_completion_reward(scenario, client, database):
    from app.models import Task
    from app.schemas.task import TaskRead
    at = datetime(2026, 11, 2, 1, tzinfo=UTC)
    with database() as session:
        task = Task(title='기존 완료', scheduled_date=date(2026, 11, 12), is_completed=True,
                    created_at=at, updated_at=at, completed_at=at)
        session.add(task)
        session.flush()
        task_id = task.id
        state = TaskRead.model_validate(task).model_dump(mode='json')
        session.add(TaskEvent(task_id=task_id, event_type='BASELINE', before_state=None, after_state=state, occurred_at=at))
        session.commit()
    scenario(datetime(2026, 11, 2, 2, tzinfo=UTC), 'update', task_id, is_completed=False)
    scenario(datetime(2026, 11, 2, 3, tzinfo=UTC), 'update', task_id, is_completed=True)
    assert client.get('/api/growth/summary').json()['total_xp'] == 0
