from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)

VALID = {
    "event_id": "knowledge_day",
    "region_id": "RU-SVE",
    "grade": 6,
    "pupils_count": 25,
    "duration_minutes": 45,
    "format": "class_hour",
}


def check_error(response, expected_code, expected_field):
    data = response.json()

    assert set(data) == {"error"}
    assert set(data["error"]) == {
        "code", "message", "field", "retryable"
    }
    assert data["error"]["code"] == expected_code
    assert data["error"]["field"] == expected_field
    assert data["error"]["message"]
    assert data["error"]["retryable"] is False


def test_invalid_variants_count_error():
    payload = {
        **VALID,
        "generation": {"variants_count": 4},
    }
    response = client.post("/api/v1/generations", json=payload)

    assert response.status_code == 422
    check_error(
        response, "INVALID_VARIANTS_COUNT",
        "generation.variants_count"
    )


def test_missing_required_field_error():
    payload = {k: v for k, v in VALID.items() if k != "event_id"}
    response = client.post("/api/v1/generations", json=payload)

    assert response.status_code == 422
    check_error(response, "VALIDATION_ERROR", "event_id")


def test_unknown_event_error():
    response = client.post(
        "/api/v1/generations",
        json={**VALID, "event_id": "not_existing"},
    )

    assert response.status_code == 422
    check_error(response, "EVENT_NOT_FOUND", "event_id")


def test_unknown_project_error():
    response = client.get("/api/v1/projects/evt_not_existing")

    assert response.status_code == 404
    check_error(response, "RESOURCE_NOT_FOUND", None)
