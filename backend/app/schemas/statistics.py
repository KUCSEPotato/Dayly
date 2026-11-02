from datetime import date

from pydantic import BaseModel


class DailyStatistics(BaseModel):
    date: date
    total: int
    completed: int
    incomplete: int
    completion_rate: float | None


class WeeklyStatistics(BaseModel):
    start_date: date
    end_date: date
    total: int
    completed: int
    incomplete: int
    completion_rate: float | None
    days: list[DailyStatistics]


class CalendarSummary(BaseModel):
    year: int
    month: int
    days: list[DailyStatistics]
