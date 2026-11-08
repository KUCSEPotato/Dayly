from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import func, select

from app.core.clock import as_utc
from app.core.errors import DomainError
from app.core.periods import PeriodKind, resolve_period
from app.models import ExperienceGrant, RetrospectiveSnapshot
from app.schemas.retrospective import PeriodRead, RetrospectiveList
from app.services.growth import GrowthService
from app.services.retrospective_aggregation import RetrospectiveAggregator
from app.services.transactions import write_transaction


class RetrospectiveService:
    def __init__(self, session, now: datetime):
        self.session = session
        self.now = as_utc(now)
        self.today = self.now.astimezone(ZoneInfo("Asia/Seoul")).date()

    def list(self, kind: PeriodKind | None = None, anchor: date | None = None, limit=20, offset=0):
        requested, status = None, None
        with write_transaction(self.session):
            aggregator = None
            growth = None
            selected = None
            for current_kind in ([kind] if kind else list(PeriodKind)):
                period = resolve_period(current_kind, self.today, anchor)
                if kind:
                    requested = PeriodRead(kind=kind, start=period.start, end=period.end)
                if period.end_at > self.now:
                    status = "not_ended"
                    continue
                snapshot = self.session.scalar(select(RetrospectiveSnapshot).where(
                    RetrospectiveSnapshot.kind == current_kind,
                    RetrospectiveSnapshot.period_start == period.start,
                    RetrospectiveSnapshot.period_end == period.end,
                ))
                if snapshot is None:
                    if growth is None:
                        aggregator = RetrospectiveAggregator(self.session)
                        growth = GrowthService(self.session, self.now)
                        growth.sync_in_transaction(aggregator)
                    values = aggregator.aggregate(period)
                    xp = self.session.scalar(select(func.coalesce(func.sum(ExperienceGrant.amount), 0)).where(
                        ExperienceGrant.earned_date >= period.start, ExperienceGrant.earned_date < period.end))
                    values["data"]["xp_policy"] = growth.policy
                    # Performed volume uses first tracked completion per task, independent of planned dates.
                    grants = list(self.session.scalars(select(ExperienceGrant).where(
                        ExperienceGrant.reason == "TASK_COMPLETED",
                        ExperienceGrant.earned_date >= period.start, ExperienceGrant.earned_date < period.end)))
                    values["data"]["activity"] = {"unique_completed_tasks": len(grants),
                                                     "task_ids": [grant.task_id for grant in grants]}
                    snapshot = RetrospectiveSnapshot(kind=current_kind, period_start=period.start,
                        period_end=period.end, created_at=self.now, xp_total=xp, **values)
                    self.session.add(snapshot)
                    self.session.flush()
                if kind:
                    selected, status = snapshot, snapshot.status
            statement = select(RetrospectiveSnapshot)
            if kind:
                statement = statement.where(RetrospectiveSnapshot.kind == kind)
            total = self.session.scalar(select(func.count()).select_from(statement.subquery()))
            if anchor is not None:
                items = [selected] if selected else []
            else:
                items = list(self.session.scalars(statement.order_by(
                    RetrospectiveSnapshot.period_start.desc(), RetrospectiveSnapshot.id.desc()).limit(limit).offset(offset)))
            return RetrospectiveList(items=items, total=total, requested_period=requested, status=status)

    def detail(self, snapshot_id: int):
        # Stored snapshots are returned directly, without touching history or XP.
        snapshot = self.session.get(RetrospectiveSnapshot, snapshot_id)
        if snapshot is None:
            raise DomainError("snapshot_not_found", "회고를 찾을 수 없습니다.")
        return snapshot
