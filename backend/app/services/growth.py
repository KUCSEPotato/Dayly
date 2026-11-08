from collections import defaultdict
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import func, select

from app.core.clock import as_utc, seoul_day_bounds
from app.core.config import Settings, get_settings
from app.models import ExperienceGrant, TaskEvent
from app.schemas.growth import GrowthHistory, GrowthSummary
from app.services.retrospective_aggregation import RetrospectiveAggregator
from app.services.transactions import write_transaction


class GrowthService:
    """Immutable XP ledger; first tracked completion wins, with no clawback."""

    def __init__(self, session, now: datetime, settings: Settings | None = None):
        self.session = session
        self.now = as_utc(now)
        self.today = self.now.astimezone(ZoneInfo("Asia/Seoul")).date()
        self.settings = settings or get_settings()

    @property
    def policy(self) -> dict:
        return {"version": "v0.2.1-provisional", "task_points": self.settings.xp_task_points,
                "daily_cap": self.settings.xp_daily_cap, "bonus_half": self.settings.xp_bonus_half,
                "bonus_full": self.settings.xp_bonus_full, "level_step": self.settings.xp_level_step,
                "clawback": False}

    def sync_in_transaction(self, aggregator: RetrospectiveAggregator | None = None) -> None:
        """Caller owns the serialized transaction; safe to compose with snapshot creation."""
        aggregator = aggregator or RetrospectiveAggregator(self.session)
        grants = list(self.session.scalars(select(ExperienceGrant)))
        keys = {grant.dedup_key for grant in grants}
        budgets = defaultdict(int)
        for grant in grants:
            budgets[grant.earned_date] += grant.amount

        def award(key, reason, day, occurred_at, requested, task_id=None, event_id=None):
            if key in keys:
                return
            amount = min(requested, max(0, self.settings.xp_daily_cap - budgets[day]))
            self.session.add(ExperienceGrant(
                dedup_key=key, reason=reason, task_id=task_id, event_id=event_id,
                amount=amount, earned_date=day, occurred_at=occurred_at, created_at=self.now,
                policy_version=self.policy["version"],
            ))
            # Even a capped zero grant consumes the key permanently.
            keys.add(key)
            budgets[day] += amount

        seen = set()
        candidate_days = set()
        events = list(self.session.scalars(select(TaskEvent).where(TaskEvent.occurred_at < self.now)
                                          .order_by(TaskEvent.occurred_at, TaskEvent.id)))
        for event in events:
            for state in (event.before_state, event.after_state):
                if state:
                    candidate_days.add(date.fromisoformat(state["scheduled_date"]))
            if event.event_type == "BASELINE" and event.after_state["is_completed"]:
                seen.add(event.task_id)  # No invented pre-baseline completion reward.
            if event.event_type == "COMPLETED" and event.task_id not in seen:
                seen.add(event.task_id)
                day = event.occurred_at.astimezone(ZoneInfo("Asia/Seoul")).date()
                award(f"task:{event.task_id}:first", "TASK_COMPLETED", day, event.occurred_at,
                      self.settings.xp_task_points, event.task_id, event.id)
        for day in sorted(candidate_days):
            if day >= self.today or f"day:{day}:bonus" in keys:
                continue
            stats = aggregator.day(day)
            rate = stats["completion_rate"]
            if stats["coverage"] != "complete" or rate is None or rate < 50:
                continue
            requested = self.settings.xp_bonus_full if rate == 100 else self.settings.xp_bonus_half
            award(f"day:{day}:bonus", "DAILY_BONUS", day, seoul_day_bounds(day)[1], requested)
        self.session.flush()

    def summary(self) -> GrowthSummary:
        with write_transaction(self.session):
            self.sync_in_transaction()
            total = self.session.scalar(select(func.coalesce(func.sum(ExperienceGrant.amount), 0)))
            level, remaining = 1, total
            while remaining >= self.settings.xp_level_step * level:
                remaining -= self.settings.xp_level_step * level
                level += 1
            next_level = self.settings.xp_level_step * level
            return GrowthSummary(total_xp=total, level=level, xp_into_level=remaining,
                                 next_level_xp=next_level, xp_to_next_level=next_level - remaining, policy=self.policy)

    def history(self, limit=20, offset=0) -> GrowthHistory:
        with write_transaction(self.session):
            self.sync_in_transaction()
            items = list(self.session.scalars(select(ExperienceGrant)
                .order_by(ExperienceGrant.occurred_at.desc(), ExperienceGrant.id.desc()).limit(limit).offset(offset)))
            total = self.session.scalar(select(func.count()).select_from(ExperienceGrant))
            return GrowthHistory(items=items, total=total)
