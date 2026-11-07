from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class GrowthSummary(BaseModel):
    total_xp: int
    level: int
    xp_into_level: int
    next_level_xp: int
    xp_to_next_level: int
    policy: dict


class GrantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reason: str
    task_id: int | None
    event_id: int | None
    amount: int
    earned_date: date
    occurred_at: datetime
    created_at: datetime
    policy_version: str


class GrowthHistory(BaseModel):
    items: list[GrantRead]
    total: int
