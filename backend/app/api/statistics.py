from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import StatisticsServiceDependency
from app.schemas.statistics import CalendarSummary, DailyStatistics, WeeklyStatistics

router = APIRouter(tags=["Calendar & Statistics"])


@router.get("/calendar", response_model=CalendarSummary)
def calendar_summary(
    service: StatisticsServiceDependency,
    year: Annotated[int, Query(ge=1, le=9999)],
    month: Annotated[int, Query(ge=1, le=12)],
):
    return service.calendar(year, month)


@router.get("/stats/daily", response_model=DailyStatistics)
def daily(service: StatisticsServiceDependency, day: Annotated[date, Query(alias="date")]):
    return service.daily(day)


@router.get("/stats/weekly", response_model=WeeklyStatistics)
def weekly(service: StatisticsServiceDependency):
    return service.weekly()
