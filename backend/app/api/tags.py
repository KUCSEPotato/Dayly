from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.dependencies import SessionDependency
from app.schemas.tag import TagCreate, TagRead
from app.services.tags import TagService

router = APIRouter(prefix="/tags", tags=["Tags"])


@router.get("", response_model=list[TagRead])
def list_tags(session: SessionDependency, q: Annotated[str, Query(max_length=30)] = ""):
    return TagService(session).list(q)


@router.post("", response_model=TagRead, status_code=status.HTTP_201_CREATED)
def create_tag(data: TagCreate, session: SessionDependency):
    return TagService(session).create(data)
