from datetime import UTC, date, datetime, timedelta

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from app.core.config import BACKEND_DIR, get_settings
from app.models import Task, TaskEvent
from app.schemas.task import TaskRead, TaskUpdate
from app.services.task_history import TaskHistoryService
from app.services.tasks import TaskService


def test_upgrade_preserves_existing_tasks_and_baselines_once(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'existing-v01.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    engine = create_engine(url)
    factory = sessionmaker(engine, expire_on_commit=False)
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    try:
        command.upgrade(config, "0001")
        created = datetime(2026, 10, 1, 3, 4, 5, 123456, tzinfo=UTC)
        with factory() as session:
            session.add_all([
                Task(id=7, title="기존 미완료", description="보존할 설명", scheduled_date=date(2026, 11, 2),
                     created_at=created, updated_at=created, is_completed=False),
                Task(id=42, title="기존 완료", scheduled_date=date(2026, 10, 1), is_completed=True,
                     completed_at=created, created_at=created, updated_at=created),
            ])
            session.commit()
            originals = [TaskRead.model_validate(task).model_dump(mode="json")
                         for task in session.scalars(select(Task).order_by(Task.id))]
        command.upgrade(config, "head")
        command.upgrade(config, "head")  # A normal rerun is safe and creates no duplicate baselines.
        with factory() as session:
            assert [TaskRead.model_validate(task).model_dump(mode="json")
                    for task in session.scalars(select(Task).order_by(Task.id))] == originals
            events = list(session.scalars(select(TaskEvent).order_by(TaskEvent.id)))
            assert len(events) == 2
            assert [item.event_type for item in events] == ["BASELINE", "BASELINE"]
            assert [item.after_state for item in events] == originals
            assert all(item.before_state is None and item.occurred_at > created for item in events)
            history = TaskHistoryService(session)
            assert history.reconstruct(events[0].occurred_at) == []
            assert [item.model_dump(mode="json") for item in history.reconstruct(
                events[0].occurred_at + timedelta(microseconds=1))] == originals
        with factory() as session:
            TaskService(session, date(2026, 11, 2)).update(7, TaskUpdate(title="이후 수정"))
        with factory() as session:
            events = list(session.scalars(select(TaskEvent).order_by(TaskEvent.id)))
            assert events[-1].event_type == "UPDATED"
            assert events[-1].before_state == originals[0]
            assert events[-1].after_state["title"] == "이후 수정"
            assert "AUTOINCREMENT" in session.scalar(text("SELECT sql FROM sqlite_master WHERE name='tasks'"))
        command.check(config)
    finally:
        engine.dispose()
        get_settings.cache_clear()
