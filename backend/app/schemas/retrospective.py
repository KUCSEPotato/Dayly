from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.core.periods import PeriodKind
from app.schemas.task import TaskRead

SnapshotStatus = Literal["ready", "no_activity", "partial", "unavailable"]


class PeriodRead(BaseModel):
    kind: PeriodKind
    start: date
    end: date


class RetrospectiveDay(BaseModel):
    date: date
    coverage: Literal["complete", "partial", "unavailable"]
    total: int | None
    completed: int | None
    incomplete: int | None
    completion_rate: float | None


class RetrospectiveWeek(BaseModel):
    start: date
    end: date
    completed: int
    total: int
    completion_rate: float | None


class AnalysisCoverage(BaseModel):
    status: Literal["complete", "partial", "unavailable"]
    recording_started_at: datetime | None


class AnalysisTag(BaseModel):
    tag_id: int | None
    name: str
    color: str | None


class TagActivity(AnalysisTag):
    total: int
    completed: int
    incomplete: int
    completion_rate: float | None


class TagPostponements(AnalysisTag):
    postponed_tasks: int
    total_postponements: int
    postponed_days: int


class PostponementAnalysis(BaseModel):
    postponed_tasks: int | None
    total_postponements: int | None
    postponed_days: int | None
    by_tag: list[TagPostponements]


class RetrospectiveAnalysis(BaseModel):
    version: Literal["v0.2.3"]
    coverage: AnalysisCoverage
    tag_activity: list[TagActivity]
    postponements: PostponementAnalysis


class SnapshotData(BaseModel):
    completed_tasks: list[TaskRead]
    incomplete_tasks: list[TaskRead]
    days: list[RetrospectiveDay]
    weeks: list[RetrospectiveWeek]
    best_day: date | None
    best_week: date | None
    activity: dict
    recording_started_at: datetime
    xp_policy: dict
    analysis: RetrospectiveAnalysis | None = None


class SnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: PeriodKind
    period_start: date
    period_end: date
    created_at: datetime
    status: SnapshotStatus
    total: int | None
    completed: int | None
    incomplete: int | None
    completion_rate: float | None
    xp_total: int
    data: SnapshotData


class RetrospectiveList(BaseModel):
    items: list[SnapshotRead]
    total: int
    requested_period: PeriodRead | None
    status: SnapshotStatus | Literal["not_ended"] | None
