from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from backend.participants import Participants
from backend.resources import Resources
from backend.teacher_preferences import TeacherPreferences
from backend.generation_settings import GenerationSettings


GradeGroup = Literal["1-4", "5-8", "9-11"]
EventFormat = Literal[
    "class_hour",
    "school_event",
    "interactive_lesson",
]


class GenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1)
    region_id: Literal["RU-SVE"]

    grade_group: GradeGroup | None = None
    grade: int | None = Field(default=None, ge=1, le=11)

    pupils_count: int = Field(ge=1, le=35)
    duration_minutes: Literal[30, 45, 60, 90]
    format: EventFormat
    participants: Participants = Field(default_factory=Participants)
    resources: Resources = Field(default_factory=Resources)
    teacher_preferences: TeacherPreferences = Field(default_factory=TeacherPreferences)
    generation: GenerationSettings = Field(default_factory=GenerationSettings)

    @model_validator(mode="after")
    def check_grade_group(self):
        if self.grade is None and self.grade_group is None:
            raise ValueError("Укажите класс или возрастную группу")

        if self.grade is not None:
            if self.grade <= 4:
                expected = "1-4"
            elif self.grade <= 8:
                expected = "5-8"
            else:
                expected = "9-11"

            if self.grade_group is None:
                self.grade_group = expected
            elif self.grade_group != expected:
                raise ValueError(
                    "Класс не соответствует возрастной группе"
                )

        return self
