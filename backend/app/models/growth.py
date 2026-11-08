from datetime import date, datetime

from sqlalchemy import CheckConstraint, Index, String, event
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.task import UTCDateTime


class ExperienceGrant(Base):
    __tablename__ = "experience_grants"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_experience_amount"),
        Index("ix_experience_earned_date", "earned_date", "id"),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    dedup_key: Mapped[str] = mapped_column(String(120), unique=True)
    reason: Mapped[str] = mapped_column(String(24))
    task_id: Mapped[int | None] = mapped_column()
    event_id: Mapped[int | None] = mapped_column()
    amount: Mapped[int] = mapped_column()
    earned_date: Mapped[date] = mapped_column()
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime())
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
    policy_version: Mapped[str] = mapped_column(String(24))


@event.listens_for(ExperienceGrant, "before_update")
@event.listens_for(ExperienceGrant, "before_delete")
def protect_grant(mapper, connection, target):
    raise ValueError("Experience grants are immutable")
