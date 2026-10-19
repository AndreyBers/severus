from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_health_check():
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_catalog_events():
    response = client.get("/api/v1/catalog/events")

    assert response.status_code == 200

    events = response.json()

    assert isinstance(events, list)
    assert len(events) >= 2

    event_ids = [event["id"] for event in events]

    assert "knowledge_day" in event_ids
    assert "teachers_day" in event_ids
    assert len(event_ids) == len(set(event_ids))


def test_catalog_event_structure():
    response = client.get("/api/v1/catalog/events")

    for event in response.json():
        assert event["id"]
        assert event["title"]
        assert event["category"]
        assert isinstance(event["supported_age_groups"], list)
        assert isinstance(event["supported_formats"], list)
