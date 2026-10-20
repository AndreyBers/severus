import pytest
from pydantic import ValidationError

from backend.resources import Resources
from backend.schemas import GenerationRequest


def test_default_resources():
    data = Resources()

    assert data.projector is None
    assert data.printer is None
    assert data.room is None
    assert data.available_materials == []


def test_valid_resources():
    data = Resources(
        projector=True,
        printer=False,
        internet=None,
        audio=True,
        room="classroom",
        available_materials=["paper", "markers"],
    )

    assert data.projector is True
    assert data.printer is False
    assert data.internet is None
    assert len(data.available_materials) == 2


def test_invalid_projector_type():
    with pytest.raises(ValidationError):
        Resources(projector=1)


def test_invalid_room():
    with pytest.raises(ValidationError):
        Resources(room="unknown_room")


def test_resources_in_generation_request():
    request = GenerationRequest(
        event_id="knowledge_day",
        region_id="RU-SVE",
        grade=6,
        pupils_count=25,
        duration_minutes=45,
        format="class_hour",
        resources={
            "projector": True,
            "internet": False,
            "room": "classroom",
            "available_materials": ["paper"],
        },
    )

    assert request.resources.projector is True
    assert request.resources.internet is False
    assert request.resources.room == "classroom"
