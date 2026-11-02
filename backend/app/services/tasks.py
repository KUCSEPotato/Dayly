from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import utc_now
from app.core.errors import DomainError
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.policy import ensure_accessible


class TaskService:
    """Owns task rules and write transactions. No FastAPI/HTTP objects here."""

    def __init__(self, session: Session, today: date):
        self.session = session
        self.today = today

    def list_for_date(self, day: date) -> list[Task]:
        ensure_accessible(day, self.today)
        return list(self.session.scalars(
            select(Task).where(Task.scheduled_date == day).order_by(Task.created_at, Task.id)
        ))

    def create(self, data: TaskCreate) -> Task:
        ensure_accessible(data.scheduled_date, self.today)
        task = Task(**data.model_dump())
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        return task

    def _get(self, task_id: int) -> Task:
        task = self.session.get(Task, task_id)
        if task is None:
            raise DomainError("task_not_found", "할 일을 찾을 수 없습니다.")
        ensure_accessible(task.scheduled_date, self.today)
        return task

    def update(self, task_id: int, data: TaskUpdate) -> Task:
        task = self._get(task_id)
        changes = data.model_dump(exclude_unset=True)
        if "scheduled_date" in changes:
            ensure_accessible(changes["scheduled_date"], self.today)
        # Repeated PATCH true is idempotent: preserve the first completion timestamp.
        if "is_completed" in changes and changes["is_completed"] != task.is_completed:
            task.completed_at = utc_now() if changes["is_completed"] else None
        for key, value in changes.items():
            setattr(task, key, value)
        task.updated_at = utc_now()
        self.session.commit()
        self.session.refresh(task)
        return task

    def delete(self, task_id: int) -> None:
        self.session.delete(self._get(task_id))
        self.session.commit()
