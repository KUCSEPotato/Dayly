from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query

from app.api.dependencies import RetrospectiveServiceDependency
from app.core.periods import PeriodKind
from app.schemas.retrospective import RetrospectiveList, SnapshotRead

router = APIRouter(prefix="/retrospectives", tags=["Retrospectives"])


@router.get("", response_model=RetrospectiveList)
def list_retrospectives(
    service: RetrospectiveServiceDependency,
    kind: PeriodKind | None = None,
    anchor: Annotated[date | None, Query(alias="date")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    if anchor is not None and kind is None:
        raise HTTPException(status_code=422, detail="날짜를 지정할 때는 회고 종류도 지정해 주세요.")
    return service.list(kind, anchor, limit, offset)


@router.get("/{snapshot_id}", response_model=SnapshotRead)
def retrospective_detail(snapshot_id: Annotated[int, Path(gt=0)], service: RetrospectiveServiceDependency):
    return service.detail(snapshot_id)
