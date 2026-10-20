from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool


RoomType = Literal[
    "classroom",
    "assembly_hall",
    "gym",
    "other",
]


class Resources(BaseModel):
    model_config = ConfigDict(extra="forbid")

    projector: StrictBool | None = None
    printer: StrictBool | None = None
    internet: StrictBool | None = None
    audio: StrictBool | None = None

    room: RoomType | None = None

    available_materials: list[str] = Field(
        default_factory=list
    )

    extra_notes: str | None = None
