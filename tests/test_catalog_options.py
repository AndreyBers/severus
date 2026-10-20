from typing import get_args

from fastapi.testclient import TestClient

from backend.main import app
from backend.schemas import GradeGroup, EventFormat
from backend.participants import ParentRole, AudienceEngagement


client = TestClient(app)


def test_options_endpoint():
    response = client.get("/api/v1/catalog/options")

    assert response.status_code == 200
    data = response.json()

    assert data["regions"][0]["value"] == "RU-SVE"
    assert data["grades"] == list(range(1, 12))
    assert data["pupils_count"] == {"min": 1, "max": 35}
    assert [x["value"] for x in data["duration_minutes"]] == [
        30, 45, 60, 90
    ]


def test_options_match_request_enums():
    data = client.get("/api/v1/catalog/options").json()

    checks = [
        ("grade_groups", GradeGroup),
        ("formats", EventFormat),
        ("parent_roles", ParentRole),
        ("parent_audience_engagement", AudienceEngagement),
    ]

    for field, enum_type in checks:
        values = [item["value"] for item in data[field]]
        assert values == list(get_args(enum_type))
        assert all(item["label"] for item in data[field])


def test_teacher_and_generation_options():
    data = client.get("/api/v1/catalog/options").json()

    assert len(data["teacher_preferences"]["style"]) == 4
    assert len(data["teacher_preferences"]["difficulty"]) == 3
    assert data["generation"]["variants_count"] == [1, 2, 3]
    assert data["generation"]["languages"][0]["value"] == "ru"
