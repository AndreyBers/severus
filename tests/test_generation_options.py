import pytest
from pydantic import ValidationError

from backend.generation_settings import GenerationSettings
from backend.teacher_preferences import TeacherPreferences
from backend.schemas import GenerationRequest


def test_default_teacher_preferences():
    data = TeacherPreferences()

    assert data.style == "classic"
    assert data.script_detail == "standard"
    assert data.group_work is False


def test_custom_teacher_preferences():
    data = TeacherPreferences(
        style="interactive",
        script_detail="detailed",
        group_work=True,
    )

    assert data.style == "interactive"
    assert data.group_work is True


def test_invalid_teacher_style():
    with pytest.raises(ValidationError):
        TeacherPreferences(style="unknown")


def test_valid_variants_count():
    for count in (1, 2, 3):
        data = GenerationSettings(variants_count=count)
        assert data.variants_count == count


def test_invalid_variants_count():
    for count in (0, 4):
        with pytest.raises(ValidationError):
            GenerationSettings(variants_count=count)


def test_options_in_generation_request():
    request = GenerationRequest(
        event_id="knowledge_day",
        region_id="RU-SVE",
        grade=6,
        pupils_count=25,
        duration_minutes=45,
        format="class_hour",
        teacher_preferences={
            "style": "creative",
            "group_work": True,
        },
        generation={
            "variants_count": 2,
        },
    )

    assert request.teacher_preferences.style == "creative"
    assert request.teacher_preferences.group_work is True
    assert request.generation.variants_count == 2
