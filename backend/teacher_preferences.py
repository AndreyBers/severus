from typing import Literal

from pydantic import BaseModel, ConfigDict, StrictBool


class TeacherPreferences(BaseModel):
    model_config = ConfigDict(extra="forbid")

    style: Literal[
        "classic", "interactive", "creative", "research"
    ] = "classic"

    script_detail: Literal[
        "brief", "standard", "detailed"
    ] = "standard"

    difficulty: Literal[
        "basic", "standard", "advanced"
    ] = "standard"

    interaction_level: Literal[
        "low", "medium", "high"
    ] = "low"

    group_work: StrictBool = False

    preparation_effort: Literal[
        "minimal", "standard", "extended"
    ] = "minimal"

    notes: str | None = None
