import json
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel, Field


router = APIRouter(
    prefix="/api/v1/catalog",
    tags=["Catalog"],
)

EVENTS_DIR = (
    Path(__file__).resolve().parent.parent
    / "catalog"
    / "events"
)


class EventSummary(BaseModel):
    id: str
    title: str
    category: str
    aliases: list[str] = Field(default_factory=list)
    supported_age_groups: list[str] = Field(default_factory=list)
    supported_formats: list[str] = Field(default_factory=list)
    catalog_version: str


@router.get("/events", response_model=list[EventSummary])
def list_events():
    events = []

    for path in sorted(EVENTS_DIR.glob("*.json")):
        with path.open(encoding="utf-8") as file:
            data = json.load(file)

        events.append(EventSummary.model_validate(data))

    return events
