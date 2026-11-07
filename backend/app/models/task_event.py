from datetime import datetime
from enum import StrEnum

from sqlalchemy import JSON, CheckConstraint, Index, String, event, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.task import UTCDateTime


class EventType(StrEnum):
    CREATED = "CREATED"
    UPDATED = "UPDATED"
    COMPLETED = "COMPLETED"
    UNCOMPLETED = "UNCOMPLETED"
    DELETED = "DELETED"
    BASELINE = "BASELINE"


class TaskEvent(Base):
    """Immutable snapshots. Deliberately no FK to the deletable tasks table."""

    __tablename__ = "task_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('CREATED','UPDATED','COMPLETED','UNCOMPLETED','DELETED','BASELINE')",
            name="ck_task_events_type",
        ),
        CheckConstraint(
            "(event_type IN ('CREATED','BASELINE') AND before_state IS NULL AND after_state IS NOT NULL) OR "
            "(event_type = 'DELETED' AND before_state IS NOT NULL AND after_state IS NULL) OR "
            "(event_type IN ('UPDATED','COMPLETED','UNCOMPLETED') "
            "AND before_state IS NOT NULL AND after_state IS NOT NULL)",
            name="ck_task_events_states",
        ),
        Index("ix_task_events_order", "occurred_at", "id"),
        Index("ix_task_events_task_order", "task_id", "occurred_at", "id"),
        Index("uq_task_events_baseline", "task_id", unique=True,
              sqlite_where=text("event_type = 'BASELINE'"),
              postgresql_where=text("event_type = 'BASELINE'")),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column()
    event_type: Mapped[str] = mapped_column(String(16))
    before_state: Mapped[dict | None] = mapped_column(JSON(none_as_null=True))
    after_state: Mapped[dict | None] = mapped_column(JSON(none_as_null=True))
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime())


@event.listens_for(TaskEvent, "before_update")
@event.listens_for(TaskEvent, "before_delete")
def prevent_event_changes(mapper, connection, target):
    raise ValueError("Task events are append-only")
