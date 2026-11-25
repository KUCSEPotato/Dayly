import json
from datetime import UTC, date, datetime

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.core.clock import seoul_today
from app.core.config import BACKEND_DIR, get_settings
from app.db import get_session
from app.main import app
from app.services.task_history import TaskHistoryService


def test_0004_preserves_populated_legacy_tables_and_snapshot_response(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'v021.db'}"
    monkeypatch.setenv('DATABASE_URL', url)
    get_settings.cache_clear()
    config = Config(str(BACKEND_DIR / 'alembic.ini'))
    engine = create_engine(url)
    factory = sessionmaker(engine, expire_on_commit=False)
    state = dict(id=42, title='기존 태그 없는 일', description=None, scheduled_date='2026-11-02',
                 is_completed=True, created_at='2026-11-02T01:00:00Z',
                 updated_at='2026-11-02T02:00:00Z', completed_at='2026-11-02T02:00:00Z')
    snapshot_data = dict(completed_tasks=[state], incomplete_tasks=[], days=[], weeks=[],
                         best_day='2026-11-02', best_week=None, activity={'unique_completed_tasks': 1, 'task_ids': [42]},
                         recording_started_at='2026-11-01T00:00:00Z', xp_policy={'version': 'v0.2.1-provisional'})
    try:
        command.upgrade(config, '0003')
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO tasks (id,title,scheduled_date,is_completed,created_at,updated_at,completed_at) "
                                    "VALUES (42,'기존 태그 없는 일','2026-11-02',1,'2026-11-02 01:00:00','2026-11-02 02:00:00','2026-11-02 02:00:00')"))
            connection.execute(text("INSERT INTO task_events (id,task_id,event_type,before_state,after_state,occurred_at) "
                                    "VALUES (8,42,'BASELINE',NULL,:state,'2026-11-02 02:00:00')"), {'state': json.dumps(state)})
            connection.execute(text("INSERT INTO retrospective_snapshots "
                                    "(id,kind,period_start,period_end,created_at,status,total,completed,incomplete,completion_rate,xp_total,data) "
                                    "VALUES (3,'daily','2026-11-02','2026-11-03','2026-11-03 00:00:00','ready',1,1,0,100,30,:data)"), {'data': json.dumps(snapshot_data)})
            connection.execute(text("INSERT INTO experience_grants "
                                    "(id,dedup_key,reason,task_id,event_id,amount,earned_date,occurred_at,created_at,policy_version) "
                                    "VALUES (9,'legacy','TASK_COMPLETED',42,8,30,'2026-11-02','2026-11-02 02:00:00','2026-11-03 00:00:00','v0.2.1-provisional')"))
            names = ['tasks', 'task_events', 'retrospective_snapshots', 'experience_grants', 'history_coverage']
            columns = {name: [item['name'] for item in inspect(connection).get_columns(name)] for name in names}
            before = {name: connection.execute(text(f'SELECT * FROM {name} ORDER BY id')).all() for name in names}
        command.upgrade(config, 'head')
        command.upgrade(config, 'head')
        with engine.connect() as connection:
            for name in names:
                assert connection.execute(text(f"SELECT {','.join(columns[name])} FROM {name} ORDER BY id")).all() == before[name]
            assert connection.scalar(text('SELECT count(*) FROM tags')) == 0
            assert connection.scalar(text('SELECT count(*) FROM task_tags')) == 0
            assert connection.scalar(text('SELECT change_reason FROM task_events')) is None
            assert connection.exec_driver_sql('PRAGMA integrity_check').scalar() == 'ok'
        def sessions():
            with factory() as session:
                yield session
        app.dependency_overrides[get_session] = sessions
        app.dependency_overrides[seoul_today] = lambda: date(2026, 11, 3)
        with TestClient(app) as client:
            response = client.get('/api/retrospectives/3')
            assert response.status_code == 200
            assert response.json()['data'] == snapshot_data
            assert client.get('/api/retrospectives?kind=daily&date=2026-11-02').json()['items'][0] == response.json()
            assert client.get('/api/tasks?date=2026-11-02').json()[0]['tags'] == []
            created_tag = client.post('/api/tags', json={'name': 'New'}).json()
            client.patch('/api/tasks/42', json={'tag_ids': [created_tag['id']]}).raise_for_status()
            assert client.get('/api/retrospectives/3').json() == response.json()
        with factory() as session:
            restored = TaskHistoryService(session).reconstruct(datetime(2026, 11, 3, tzinfo=UTC))[0]
            assert restored.id == 42 and restored.tags == []
        command.check(config)
        engine.dispose()
        with factory() as session:
            assert session.execute(text('SELECT count(*) FROM task_tags')).scalar() == 1
            assert session.execute(text('SELECT amount FROM experience_grants')).scalar() == 30
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
        get_settings.cache_clear()
