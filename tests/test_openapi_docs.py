from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_openapi_422_matches_actual_error_format():
    response = client.get("/openapi.json")
    assert response.status_code == 200

    schema = response.json()

    error_response = schema["paths"][
        "/api/v1/generations"
    ]["post"]["responses"]["422"]

    error_ref = error_response["content"][
        "application/json"
    ]["schema"]["$ref"]

    assert error_ref == (
        "#/components/schemas/ApiErrorResponse"
    )

    error_schema = schema["components"]["schemas"][
        "ApiErrorResponse"
    ]

    fields = error_schema["properties"]["error"][
        "properties"
    ]

    assert set(fields) == {
        "code", "message", "field", "retryable"
    }
