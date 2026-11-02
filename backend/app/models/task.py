from datetime import UTC, date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from app.core.clock import utc_now
from app.db import Base


class UTCDateTime(TypeDecorator):
    """SQLite loses timezone metadata; restore UTC on reads for consistent API output."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("A timezone-aware datetime is required")
        return value.astimezone(UTC)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint("length(trim(title)) > 0", name="ck_tasks_title_not_blank"),
        CheckConstraint(
            "(is_completed AND completed_at IS NOT NULL) OR "
            "(NOT is_completed AND completed_at IS NULL)",
            name="ck_tasks_completion_consistent",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    scheduled_date: Mapped[date] = mapped_column(Date, index=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, onupdate=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
