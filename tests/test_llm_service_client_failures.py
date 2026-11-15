"""Контракт ошибок Backend при сбоях связи с внутренним LLM-сервисом."""

from unittest.mock import patch

import httpx
import pytest
from fastapi import HTTPException

from backend.llm_service_client import LLMServiceClient


@pytest.fixture
def client():
    return LLMServiceClient("http://127.0.0.1:8090")


def test_remote_protocol_disconnect_returns_retryable_503(client):
    with patch("backend.llm_service_client.httpx.request", side_effect=httpx.RemoteProtocolError("disconnect")):
        with pytest.raises(HTTPException) as error:
            client.get_generation("job_test")
    assert error.value.status_code == 503
    assert error.value.detail == {
        "code": "MODEL_UNAVAILABLE",
        "message": "LLM-сервис недоступен",
        "field": None,
        "retryable": True,
    }


@pytest.mark.parametrize("body, expected", [
    (b"not-json", "LLM-сервис вернул некорректный JSON"),
    (b"[]", "LLM-сервис вернул неожиданный формат ответа"),
])
def test_invalid_success_response_is_controlled_502(client, body, expected):
    response = httpx.Response(200, content=body, request=httpx.Request("GET", "http://127.0.0.1:8090/api/v1/health/llm"))
    with patch("backend.llm_service_client.httpx.request", return_value=response):
        with pytest.raises(HTTPException) as error:
            client.health()
    assert error.value.status_code == 502
    assert error.value.detail["code"] == "LLM_SERVICE_ERROR"
    assert error.value.detail["message"] == expected
    assert error.value.detail["retryable"] is True


def test_valid_response_remains_unchanged(client):
    payload = {"status": "ok", "model_key": "some-model"}
    response = httpx.Response(200, json=payload, request=httpx.Request("GET", "http://127.0.0.1:8090/api/v1/health/llm"))
    with patch("backend.llm_service_client.httpx.request", return_value=response):
        assert client.health() == payload


def test_upstream_service_busy_propagates(client):
    err = {"code": "SERVICE_BUSY", "message": "Подождите", "field": None, "retryable": True}
    response = httpx.Response(503, json={"error": err}, request=httpx.Request("POST", "http://127.0.0.1:8090/api/v1/generations"))
    with patch("backend.llm_service_client.httpx.request", return_value=response):
        with pytest.raises(HTTPException) as error:
            client.create_generation({"event_id": "knowledge_day"})
    assert error.value.status_code == 503
    assert error.value.detail == err
