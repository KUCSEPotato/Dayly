import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from app.core.config import BACKEND_DIR
from app.models import Task


def test_database_constraint_rejects_inconsistent_completion(database):
    from datetime import date

    with database() as session:
        session.add(Task(title="검증", scheduled_date=date(2026, 11, 2), is_completed=True, completed_at=None))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
        assert session.query(Task).count() == 0


def test_migrations_match_models_and_can_roundtrip(database):
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    command.check(config)
    command.downgrade(config, "base")
    with database() as session:
        assert "tasks" not in inspect(session.bind).get_table_names()
    command.upgrade(config, "head")
    with database() as session:
        assert "tasks" in inspect(session.bind).get_table_names()
