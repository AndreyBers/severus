from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


ParentRole = Literal[
    "helper",
    "active_participant",
    "audience",
    "evaluator",
]

AudienceEngagement = Literal[
    "none",
    "feedback",
    "vote",
    "audience_award",
]


class Participants(BaseModel):
    model_config = ConfigDict(extra="forbid")

    teachers_count: int = Field(default=1, ge=1)
    parents_enabled: bool = False
    parents_count: int | None = Field(default=None, ge=0)
    parent_roles: list[ParentRole] = Field(default_factory=list)
    parent_audience_engagement: AudienceEngagement = "none"
    parent_notes: str | None = None

    @model_validator(mode="after")
    def check_parents(self):
        if not self.parents_enabled:
            if self.parents_count not in (None, 0):
                raise ValueError("Родители отключены, но указано их количество")

            if self.parent_roles:
                raise ValueError("Роли родителей требуют их участия")

            if self.parent_audience_engagement != "none":
                raise ValueError("Зрительское участие родителей отключено")

            self.parents_count = 0
        else:
            if self.parents_count is None or self.parents_count < 1:
                raise ValueError("Укажите количество родителей")

            if not self.parent_roles:
                self.parent_roles = ["audience"]

            if (
                self.parent_audience_engagement != "none"
                and "audience" not in self.parent_roles
            ):
                raise ValueError("Для голосования или обратной связи нужна роль audience")

        return self
