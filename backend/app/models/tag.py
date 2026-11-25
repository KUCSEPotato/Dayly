from datetime import datetime

from sqlalchemy import CheckConstraint, Column, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utc_now
from app.db import Base
from app.models.task import UTCDateTime


task_tags = Table(
    "task_tags", Base.metadata,
    Column("task_id", ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (
        CheckConstraint("length(trim(name)) BETWEEN 1 AND 30", name="ck_tags_name_length"),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30))
    # Python casefold handles Unicode as well as ASCII; DB uniqueness handles races.
    normalized_name: Mapped[str] = mapped_column(String(90), unique=True)
    color: Mapped[str] = mapped_column(String(7))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, onupdate=utc_now)
