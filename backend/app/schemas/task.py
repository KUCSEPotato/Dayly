from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Description = Annotated[str, StringConstraints(max_length=5000)]


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Title
    description: Description | None = None
    scheduled_date: date


class TaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Title | None = None
    description: Description | None = None
    scheduled_date: date | None = None
    is_completed: bool | None = None

    @model_validator(mode="after")
    def validate_patch(self):
        if not self.model_fields_set:
            raise ValueError("수정할 필드를 하나 이상 입력해 주세요.")
        for field in ("title", "scheduled_date", "is_completed"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field}에는 null을 사용할 수 없습니다.")
        return self


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    scheduled_date: date
    is_completed: bool
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
