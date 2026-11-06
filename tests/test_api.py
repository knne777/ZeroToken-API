"""Tests for ZeroToken API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from app.main import app
from app.models.schemas import ChatResponse, TokenUsage

client = TestClient(app)


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["app"] == "ZeroToken API"


def test_root():
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert "default_provider" in data
    assert "/docs" in data["documentation"]


def test_list_providers():
    res = client.get("/api/v1/providers")
    assert res.status_code == 200
    data = res.json()
    assert "agy" in data["providers"]
    assert "claude" in data["providers"]
    assert "codex" in data["providers"]
    # agy is installed on the host
    assert data["providers"]["agy"]["installed"] is True


def test_list_models():
    res = client.get("/api/v1/models?provider=agy")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["provider"] == "agy"
    assert len(data[0]["models"]) > 0


def test_chat_invalid_provider():
    res = client.post(
        "/api/v1/chat",
        json={"message": "hello", "provider": "nonexistent_provider"},
    )
    assert res.status_code == 400
    assert "not supported" in res.json()["message"]


def test_chat_mocked_success():
    mock_resp = ChatResponse(
        provider="agy",
        model="gemini-3.8-flash-high",
        conversation_id="conv-abc-123",
        response="Respuesta exitosa de prueba",
        status="SUCCESS",
        num_turns=1,
        duration_seconds=1.2,
        usage=TokenUsage(input_tokens=100, output_tokens=50, total_tokens=150),
    )

    with patch(
        "app.providers.agy.AgyProvider.run",
        new_callable=AsyncMock,
        return_value=mock_resp,
    ):
        res = client.post(
            "/api/v1/chat",
            json={
                "message": "Hola mundo",
                "provider": "agy",
                "model": "gemini-3.8-flash-high",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["provider"] == "agy"
        assert data["conversation_id"] == "conv-abc-123"
        assert data["response"] == "Respuesta exitosa de prueba"
        assert data["usage"]["total_tokens"] == 150
