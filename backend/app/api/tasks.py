from datetime import date
from typing import Annotated

from fastapi import APIRouter, Path, Query, Response, status

from app.api.dependencies import TaskServiceDependency
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["Tasks"])
TaskId = Annotated[int, Path(gt=0)]


@router.get("", response_model=list[TaskRead])
def list_tasks(service: TaskServiceDependency, day: Annotated[date, Query(alias="date")]):
    return service.list_for_date(day)


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(data: TaskCreate, service: TaskServiceDependency):
    return service.create(data)


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(task_id: TaskId, data: TaskUpdate, service: TaskServiceDependency):
    return service.update(task_id, data)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: TaskId, service: TaskServiceDependency):
    service.delete(task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
