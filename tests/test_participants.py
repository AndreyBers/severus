import pytest
from pydantic import ValidationError

from backend.participants import Participants
from backend.schemas import GenerationRequest


def test_default_participants():
    data = Participants()

    assert data.teachers_count == 1
    assert data.parents_enabled is False
    assert data.parents_count == 0


def test_valid_parent_participation():
    data = Participants(
        teachers_count=1,
        parents_enabled=True,
        parents_count=12,
        parent_roles=["helper", "audience"],
        parent_audience_engagement="vote",
    )

    assert data.parents_count == 12
    assert "audience" in data.parent_roles


def test_parents_disabled_with_count():
    with pytest.raises(ValidationError):
        Participants(
            parents_enabled=False,
            parents_count=12,
        )


def test_voting_without_audience():
    with pytest.raises(ValidationError):
        Participants(
            parents_enabled=True,
            parents_count=12,
            parent_roles=["helper"],
            parent_audience_engagement="vote",
        )


def test_participants_in_generation_request():
    request = GenerationRequest(
        event_id="knowledge_day",
        region_id="RU-SVE",
        grade=6,
        pupils_count=25,
        duration_minutes=45,
        format="class_hour",
        participants={
            "teachers_count": 2,
            "parents_enabled": True,
            "parents_count": 5,
            "parent_roles": ["helper"],
        },
    )

    assert request.participants.teachers_count == 2
    assert request.participants.parents_count == 5
