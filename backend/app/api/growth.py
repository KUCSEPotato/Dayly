from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import GrowthServiceDependency
from app.schemas.growth import GrowthHistory, GrowthSummary

router = APIRouter(prefix="/growth", tags=["Growth"])


@router.get("/summary", response_model=GrowthSummary)
def summary(service: GrowthServiceDependency):
    return service.summary()


@router.get("/history", response_model=GrowthHistory)
def history(service: GrowthServiceDependency,
            limit: Annotated[int, Query(ge=1, le=100)] = 20,
            offset: Annotated[int, Query(ge=0)] = 0):
    return service.history(limit, offset)
