from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


VALID_REQUEST = {
    "event_id": "knowledge_day",
    "region_id": "RU-SVE",
    "grade": 6,
    "pupils_count": 25,
    "duration_minutes": 45,
    "format": "class_hour",
    "generation": {
        "variants_count": 2,
        "language": "ru",
    },
}


def test_create_generation():
    response = client.post(
        "/api/v1/generations",
        json=VALID_REQUEST,
    )

    assert response.status_code == 202

    data = response.json()

    assert data["status"] == "queued"
    assert data["requested_variants"] == 2
    assert data["completed_variants"] == 0
    assert data["job_id"].startswith("job_")
    assert data["project_id"].startswith("evt_")


def test_unknown_event():
    request = {
        **VALID_REQUEST,
        "event_id": "unknown_event",
    }

    response = client.post(
        "/api/v1/generations",
        json=request,
    )

    assert response.status_code == 422


def test_invalid_generation_parameters():
    request = {
        **VALID_REQUEST,
        "pupils_count": 0,
    }

    response = client.post(
        "/api/v1/generations",
        json=request,
    )

    assert response.status_code == 422


def test_full_generation_flow():
    response = client.post(
        "/api/v1/generations",
        json=VALID_REQUEST,
    )

    assert response.status_code == 202
    accepted = response.json()

    status_response = client.get(accepted["status_url"])
    project_response = client.get(accepted["project_url"])

    assert status_response.status_code == 200
    assert project_response.status_code == 200

    job = status_response.json()
    project = project_response.json()

    assert job["status"] == "completed"
    assert job["completed_variants"] == 2
    assert project["completed_variants"] == 2
    assert len(project["variants"]) == 2
    assert project["input"]["grade_group"] == "5-8"

    for variant in project["variants"]:
        total = sum(
            block["duration_minutes"]
            for block in variant["timeline"]
        )
        assert total == 45


def test_missing_job_and_project():
    job_response = client.get(
        "/api/v1/generations/job_missing"
    )
    project_response = client.get(
        "/api/v1/projects/evt_missing"
    )

    assert job_response.status_code == 404
    assert project_response.status_code == 404
