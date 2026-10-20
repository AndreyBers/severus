import pytest
from pydantic import ValidationError

from backend.schemas import GenerationRequest


BASE_REQUEST = {
    "event_id": "knowledge_day",
    "region_id": "RU-SVE",
    "grade": 6,
    "pupils_count": 25,
    "duration_minutes": 45,
    "format": "class_hour",
}


def test_valid_generation_request():
    request = GenerationRequest(**BASE_REQUEST)

    assert request.grade == 6
    assert request.grade_group == "5-8"
    assert request.pupils_count == 25


def test_incorrect_grade_group():
    data = {**BASE_REQUEST, "grade_group": "1-4"}

    with pytest.raises(ValidationError):
        GenerationRequest(**data)


def test_invalid_pupils_count():
    data = {**BASE_REQUEST, "pupils_count": 0}

    with pytest.raises(ValidationError):
        GenerationRequest(**data)


def test_missing_grade_and_group():
    data = {
        **BASE_REQUEST,
        "grade": None,
        "grade_group": None,
    }

    with pytest.raises(ValidationError):
        GenerationRequest(**data)


def test_unsupported_region():
    data = {**BASE_REQUEST, "region_id": "RU-MOW"}

    with pytest.raises(ValidationError):
        GenerationRequest(**data)
