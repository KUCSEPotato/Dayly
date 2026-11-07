from datetime import date, datetime
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.clock import seoul_today, utc_now
from app.db import get_session
from app.services.statistics import StatisticsService
from app.services.tasks import TaskService
from app.services.retrospectives import RetrospectiveService
from app.services.growth import GrowthService

SessionDependency = Annotated[Session, Depends(get_session)]
TodayDependency = Annotated[date, Depends(seoul_today)]
NowDependency = Annotated[datetime, Depends(utc_now)]


def get_task_service(session: SessionDependency, today: TodayDependency) -> TaskService:
    return TaskService(session, today)


def get_statistics_service(session: SessionDependency, today: TodayDependency) -> StatisticsService:
    return StatisticsService(session, today)


TaskServiceDependency = Annotated[TaskService, Depends(get_task_service)]
StatisticsServiceDependency = Annotated[StatisticsService, Depends(get_statistics_service)]


def get_retrospective_service(session: SessionDependency, now: NowDependency) -> RetrospectiveService:
    return RetrospectiveService(session, now)


def get_growth_service(session: SessionDependency, now: NowDependency) -> GrowthService:
    return GrowthService(session, now)


RetrospectiveServiceDependency = Annotated[RetrospectiveService, Depends(get_retrospective_service)]
GrowthServiceDependency = Annotated[GrowthService, Depends(get_growth_service)]
