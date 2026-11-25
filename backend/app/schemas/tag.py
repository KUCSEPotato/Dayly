from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

TagName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]
TagColor = Literal["#7c956b", "#648ca6", "#a183b5", "#c48b65", "#bd7887", "#aa994f"]


class TagCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: TagName
    color: TagColor = "#7c956b"


class TagRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    color: str
