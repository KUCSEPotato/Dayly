"""Deterministic browser-test data only. Never called by the application or Docker entrypoint."""
from datetime import date, timedelta

from app.core.clock import seoul_day_bounds, seoul_today
from app.db import SessionLocal
from app.models import HistoryCoverage
from app.schemas.task import TaskCreate, TaskUpdate
from app.schemas.tag import TagCreate
from app.services.tags import TagService
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
            tag = TagService(session).create(TagCreate(name="회고 태그", color="#648ca6"))
            marker_day = sample - timedelta(days=35)
            task_module.utc_now = lambda: seoul_day_bounds(marker_day)[0]
            TaskService(session, marker_day).create(TaskCreate(title="분석 범위 확인용 미래 계획", scheduled_date=date(2030, 1, 1)))
            task_module.utc_now = lambda: start + timedelta(hours=1)
            service = TaskService(session, sample)
            completed = service.create(TaskCreate(title="회고 검증 · 완료", description="당시의 제목과 설명", scheduled_date=sample, tag_ids=[tag.id]))
            completed_id = completed.id
            service.create(TaskCreate(title="회고 검증 · 미완료", scheduled_date=sample))
            task_module.utc_now = lambda: start + timedelta(hours=2)
            service.update(completed_id, TaskUpdate(is_completed=True))
            planned = service.create(TaskCreate(title="미루기 분석 검증", scheduled_date=date(2030, 2, 1), tag_ids=[tag.id]))
            task_module.utc_now = lambda: start + timedelta(hours=3)
            service.postpone(planned.id, date(2030, 2, 4))
            task_module.utc_now = lambda: start + timedelta(hours=4)
            service.postpone(planned.id, date(2030, 2, 6))
    finally:
        task_module.utc_now = original_clock


if __name__ == "__main__":
    seed()
