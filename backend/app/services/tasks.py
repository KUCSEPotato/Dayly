from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import utc_now
from app.core.errors import DomainError
from app.models.task import Task
from app.models.tag import Tag
from app.models.task_event import EventType, TaskEvent
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate
from app.services.policy import ensure_accessible
from app.services.transactions import write_transaction


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
        with self._transaction():
            now = utc_now()
            task = Task(**data.model_dump(exclude={"tag_ids"}), tags=self._tags(data.tag_ids),
                        created_at=now, updated_at=now)
            self.session.add(task)
            self.session.flush()  # Obtain the DB-generated ID before taking the snapshot.
            self._record(task, EventType.CREATED, None, now)
        return task

    def _transaction(self):
        return write_transaction(self.session)

    @staticmethod
    def _snapshot(task: Task) -> dict:
        return TaskRead.model_validate(task).model_dump(mode="json")

    def _record(self, task: Task, kind: EventType, before: dict | None, occurred_at,
                change_reason: str | None = None) -> None:
        self.session.add(TaskEvent(
            task_id=task.id, event_type=kind, before_state=before,
            after_state=None if kind == EventType.DELETED else self._snapshot(task),
            occurred_at=occurred_at,
            change_reason=change_reason,
        ))

    def _tags(self, tag_ids: list[int]) -> list[Tag]:
        ids = set(tag_ids)
        tags = list(self.session.scalars(select(Tag).where(Tag.id.in_(ids)).order_by(Tag.id))) if ids else []
        if len(tags) != len(ids):
            raise DomainError("tag_not_found", "선택한 태그를 찾을 수 없습니다. 태그 목록을 다시 확인해 주세요.")
        return tags

    def _get(self, task_id: int) -> Task:
        task = self.session.scalar(
            select(Task).where(Task.id == task_id).with_for_update()
            .execution_options(populate_existing=True)
        )
        if task is None:
            raise DomainError("task_not_found", "할 일을 찾을 수 없습니다.")
        ensure_accessible(task.scheduled_date, self.today)
        return task

    def update(self, task_id: int, data: TaskUpdate) -> Task:
        with self._transaction():
            task = self._get(task_id)
            changes = {key: value for key, value in data.model_dump(exclude_unset=True).items()
                       if key != "tag_ids" and getattr(task, key) != value}
            if "tag_ids" in data.model_fields_set:
                tags = self._tags(data.tag_ids)
                if [tag.id for tag in task.tags] != [tag.id for tag in tags]:
                    changes["tags"] = tags
            if not changes:
                return task
            if "scheduled_date" in changes:
                ensure_accessible(changes["scheduled_date"], self.today)
            before = self._snapshot(task)
            now = utc_now()
            kind = EventType.UPDATED
            if "is_completed" in changes:
                kind = EventType.COMPLETED if changes["is_completed"] else EventType.UNCOMPLETED
                task.completed_at = now if changes["is_completed"] else None
            for key, value in changes.items():
                setattr(task, key, value)
            task.updated_at = now
            self.session.flush()
            self._record(task, kind, before, now)
        return task

    def postpone(self, task_id: int, target_date: date | None = None) -> Task:
        with self._transaction():
            task = self._get(task_id)
            if task.is_completed:
                raise DomainError("task_completed", "완료된 할 일은 미룰 수 없습니다.")
            if target_date is None and task.scheduled_date == date.max:
                raise DomainError("date_limit", "더 이상 미룰 수 없는 날짜입니다.")
            target_date = target_date or task.scheduled_date + timedelta(days=1)
            if target_date <= task.scheduled_date:
                raise DomainError("invalid_postpone_date", "기존 예정 날짜보다 이후의 날짜를 선택해 주세요.")
            before = self._snapshot(task)
            task.scheduled_date = target_date
            task.updated_at = utc_now()
            self.session.flush()
            self._record(task, EventType.UPDATED, before, task.updated_at, "POSTPONED")
        return task

    def delete(self, task_id: int) -> None:
        with self._transaction():
            task = self._get(task_id)
            self._record(task, EventType.DELETED, self._snapshot(task), utc_now())
            self.session.delete(task)
