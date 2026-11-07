"""Deterministic browser-test data only. Never called by the application or Docker entrypoint."""
from datetime import timedelta

from app.core.clock import seoul_day_bounds, seoul_today
from app.db import SessionLocal
from app.models import HistoryCoverage
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.tasks import TaskService
import app.services.tasks as task_module


def seed():
    today = seoul_today()
    sample = today - timedelta(days=today.weekday() + 14)
    start = seoul_day_bounds(sample)[0]
    original_clock = task_module.utc_now
    try:
        with SessionLocal() as session:
            session.get(HistoryCoverage, 1).started_at = start - timedelta(days=35)
            session.commit()
            task_module.utc_now = lambda: start + timedelta(hours=1)
            service = TaskService(session, sample)
            completed = service.create(TaskCreate(title="회고 검증 · 완료", description="당시의 제목과 설명", scheduled_date=sample))
            completed_id = completed.id
            service.create(TaskCreate(title="회고 검증 · 미완료", scheduled_date=sample))
            task_module.utc_now = lambda: start + timedelta(hours=2)
            service.update(completed_id, TaskUpdate(is_completed=True))
    finally:
        task_module.utc_now = original_clock


if __name__ == "__main__":
    seed()
