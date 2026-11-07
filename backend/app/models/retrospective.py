from datetime import date, datetime

from sqlalchemy import JSON, CheckConstraint, Float, String, UniqueConstraint, event
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.task import UTCDateTime


class HistoryCoverage(Base):
    __tablename__ = "history_coverage"
    __table_args__ = (CheckConstraint("id = 1", name="ck_history_coverage_singleton"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime())


class RetrospectiveSnapshot(Base):
    __tablename__ = "retrospective_snapshots"
    __table_args__ = (
        UniqueConstraint("kind", "period_start", "period_end", name="uq_retrospective_period"),
        CheckConstraint("kind IN ('daily','weekly','monthly')", name="ck_retrospective_kind"),
        CheckConstraint("period_start < period_end", name="ck_retrospective_period"),
        CheckConstraint("status IN ('ready','no_activity','partial','unavailable')", name="ck_retrospective_status"),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(12))
    period_start: Mapped[date] = mapped_column()
    period_end: Mapped[date] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
    status: Mapped[str] = mapped_column(String(16))
    total: Mapped[int | None] = mapped_column()
    completed: Mapped[int | None] = mapped_column()
    incomplete: Mapped[int | None] = mapped_column()
    completion_rate: Mapped[float | None] = mapped_column(Float)
    xp_total: Mapped[int] = mapped_column()
    data: Mapped[dict] = mapped_column(JSON)


@event.listens_for(RetrospectiveSnapshot, "before_update")
@event.listens_for(RetrospectiveSnapshot, "before_delete")
def protect_snapshot(mapper, connection, target):
    raise ValueError("Retrospective snapshots are immutable")
