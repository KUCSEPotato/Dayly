from datetime import date

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import BACKEND_DIR, get_settings
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.tasks import TaskService


def test_0003_preserves_every_existing_task_and_event(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'v020.db'}"
    monkeypatch.setenv('DATABASE_URL', url)
    get_settings.cache_clear()
    engine = create_engine(url)
    factory = sessionmaker(engine, expire_on_commit=False)
    config = Config(str(BACKEND_DIR / 'alembic.ini'))
    try:
        command.upgrade(config, '0002')
        with factory() as session:
            service = TaskService(session, date(2026, 11, 2))
            task = service.create(TaskCreate(title='기존 Task', scheduled_date=date(2026, 11, 2)))
            service.update(task.id, TaskUpdate(is_completed=True))
        with engine.connect() as connection:
            before = {table: connection.execute(text(f'SELECT * FROM {table} ORDER BY id')).all()
                      for table in ('tasks', 'task_events')}
        command.upgrade(config, 'head')
        command.upgrade(config, 'head')
        with engine.connect() as connection:
            for table, rows in before.items():
                assert connection.execute(text(f'SELECT * FROM {table} ORDER BY id')).all() == rows
            assert connection.scalar(text('SELECT COUNT(*) FROM history_coverage')) == 1
            assert connection.scalar(text('SELECT COUNT(*) FROM experience_grants')) == 0
            assert connection.scalar(text('SELECT COUNT(*) FROM retrospective_snapshots')) == 0
            assert connection.scalar(text('SELECT started_at FROM history_coverage')) == connection.scalar(text('SELECT MIN(occurred_at) FROM task_events'))
        command.check(config)
    finally:
        engine.dispose()
        get_settings.cache_clear()
