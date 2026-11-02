from datetime import date
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.clock import seoul_today
from app.db import get_session
from app.services.statistics import StatisticsService
from app.services.tasks import TaskService

SessionDependency = Annotated[Session, Depends(get_session)]
TodayDependency = Annotated[date, Depends(seoul_today)]


def get_task_service(session: SessionDependency, today: TodayDependency) -> TaskService:
    return TaskService(session, today)


def get_statistics_service(session: SessionDependency, today: TodayDependency) -> StatisticsService:
    return StatisticsService(session, today)


TaskServiceDependency = Annotated[TaskService, Depends(get_task_service)]
StatisticsServiceDependency = Annotated[StatisticsService, Depends(get_statistics_service)]
