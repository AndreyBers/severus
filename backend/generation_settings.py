from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class GenerationSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variants_count: int = Field(
        default=1,
        ge=1,
        le=3,
        strict=True,
    )

    language: Literal["ru"] = "ru"
