from datetime import date

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.clock import seoul_today
from app.core.config import BACKEND_DIR, get_settings
from app.db import get_session
from app.main import app

TODAY = date(2026, 11, 2)


@pytest.fixture
def database(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'test.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    command.upgrade(config, "head")
    engine = create_engine(url, connect_args={"check_same_thread": False})
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    engine.dispose()
    get_settings.cache_clear()


@pytest.fixture
def client(database):
    def session_override():
        with database() as session:
            try:
                yield session
            except Exception:
                session.rollback()
                raise

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[seoul_today] = lambda: TODAY
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
