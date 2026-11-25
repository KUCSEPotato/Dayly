import json

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from app.core.config import BACKEND_DIR, get_settings


def test_0003_preserves_every_existing_task_and_event(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'v020.db'}"
    monkeypatch.setenv('DATABASE_URL', url)
    get_settings.cache_clear()
    engine = create_engine(url)
    config = Config(str(BACKEND_DIR / 'alembic.ini'))
    try:
        command.upgrade(config, '0002')
        # Seed the old schema directly: today's ORM also knows the new tag tables.
        state = dict(id=1, title='기존 Task', description=None, scheduled_date='2026-11-02',
                     is_completed=True, created_at='2026-11-02T01:00:00Z',
                     updated_at='2026-11-02T02:00:00Z', completed_at='2026-11-02T02:00:00Z')
        initial = {**state, 'is_completed': False, 'updated_at': state['created_at'], 'completed_at': None}
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO tasks (id,title,scheduled_date,is_completed,created_at,updated_at,completed_at) "
                                    "VALUES (1,'기존 Task','2026-11-02',1,'2026-11-02 01:00:00.000000','2026-11-02 02:00:00.000000','2026-11-02 02:00:00.000000')"))
            connection.execute(text("INSERT INTO task_events (task_id,event_type,before_state,after_state,occurred_at) "
                                    "VALUES (1,'CREATED',NULL,:state,'2026-11-02 01:00:00.000000')"), {'state': json.dumps(initial)})
            connection.execute(text("INSERT INTO task_events (task_id,event_type,before_state,after_state,occurred_at) "
                                    "VALUES (1,'COMPLETED',:before,:after,'2026-11-02 02:00:00.000000')"),
                               {'before': json.dumps(initial), 'after': json.dumps(state)})
        with engine.connect() as connection:
            before = {table: connection.execute(text(f'SELECT * FROM {table} ORDER BY id')).all()
                      for table in ('tasks', 'task_events')}
        command.upgrade(config, 'head')
        command.upgrade(config, 'head')
        with engine.connect() as connection:
            for table, rows in before.items():
                columns = 'id,task_id,event_type,before_state,after_state,occurred_at' if table == 'task_events' else '*'
                assert connection.execute(text(f'SELECT {columns} FROM {table} ORDER BY id')).all() == rows
            assert connection.scalar(text('SELECT COUNT(*) FROM history_coverage')) == 1
            assert connection.scalar(text('SELECT COUNT(*) FROM experience_grants')) == 0
            assert connection.scalar(text('SELECT COUNT(*) FROM retrospective_snapshots')) == 0
            assert connection.scalar(text('SELECT started_at FROM history_coverage')) == connection.scalar(text('SELECT MIN(occurred_at) FROM task_events'))
        command.check(config)
    finally:
        engine.dispose()
        get_settings.cache_clear()
