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


def test_chat_nonexistent_conversation():
    res = client.post(
        "/api/v1/chat",
        json={
            "message": "Hola",
            "provider": "agy",
            "conversation_id": "00000000-0000-0000-0000-000000000000",
        },
    )
    assert res.status_code == 404
    data = res.json()
    assert data["error"] == "ConversationNotFoundError"
    assert "not found" in data["message"]


def test_chat_with_attachments_schema():
    mock_resp = ChatResponse(
        provider="agy",
        model="default",
        conversation_id="conv-att-123",
        response='{"result": "parsed"}',
        status="SUCCESS",
        num_turns=1,
        duration_seconds=1.0,
        usage=TokenUsage(input_tokens=100, output_tokens=20, total_tokens=120),
    )

    with patch(
        "app.providers.agy.AgyProvider.run",
        new_callable=AsyncMock,
        return_value=mock_resp,
    ) as mock_run:
        res = client.post(
            "/api/v1/chat",
            json={
                "message": "Procesa archivo",
                "provider": "agy",
                "effort": "low",
                "system_prompt": "Responde en JSON",
                "attachments": [
                    {
                        "name": "test.txt",
                        "content_base64": "SGVsbG8gV29ybGQ=",
                    }
                ],
            },
        )
        assert res.status_code == 200
        assert res.json()["response"] == '{"result": "parsed"}'
        assert mock_run.called
        kwargs = mock_run.call_args.kwargs
        assert kwargs["effort"] == "low"
        assert len(kwargs["attachments"]) == 1
        assert kwargs["attachments"][0].name == "test.txt"


def test_auth_status():
    res = client.get("/api/v1/auth/status")
    assert res.status_code == 200
    data = res.json()
    assert "codex" in data
    assert "agy" in data
    assert "claude" in data


def test_virtual_api_keys_crud():
    # 1. Create key
    res = client.post(
        "/api/v1/keys",
        json={"name": "Test App Key", "rate_limit_rpm": 120},
    )
    assert res.status_code == 201
    key_data = res.json()
    assert key_data["name"] == "Test App Key"
    assert key_data["raw_key"].startswith("ztk_live_")
    assert "..." in key_data["prefix"]
    key_id = key_data["id"]
    raw_key = key_data["raw_key"]

    # 2. List keys
    list_res = client.get("/api/v1/keys")
    assert list_res.status_code == 200
    keys = list_res.json()
    assert any(k["id"] == key_id for k in keys)

    # 3. Revoke key
    del_res = client.delete(f"/api/v1/keys/{key_id}")
    assert del_res.status_code == 200


def test_openai_proxy_completion():
    mock_resp = ChatResponse(
        provider="agy",
        model="gemini-3.8-flash-high",
        conversation_id="conv-openai-999",
        response="OpenAI compatible response text",
        status="SUCCESS",
        num_turns=1,
        duration_seconds=0.8,
        usage=TokenUsage(input_tokens=50, output_tokens=25, total_tokens=75),
    )

    with patch(
        "app.providers.agy.AgyProvider.run",
        new_callable=AsyncMock,
        return_value=mock_resp,
    ):
        res = client.post(
            "/v1/chat/completions",
            json={
                "model": "gemini-3.8-flash-high",
                "messages": [
                    {"role": "system", "content": "You are a test bot."},
                    {"role": "user", "content": "Hello via OpenAI endpoint"},
                ],
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["object"] == "chat.completion"
        assert len(data["choices"]) == 1
        assert data["choices"][0]["message"]["content"] == "OpenAI compatible response text"
        assert data["usage"]["total_tokens"] == 75


def test_analytics_overview():
    res = client.get("/api/v1/analytics/overview")
    assert res.status_code == 200
    data = res.json()
    assert "total_requests" in data
    assert "total_savings_usd" in data
    assert "total_tokens" in data


def test_admin_auth_flow():
    # 1. Login with bad password -> 401
    bad_res = client.post(
        "/api/v1/admin/login",
        json={"username": "admin", "password": "wrong_password_123"},
    )
    assert bad_res.status_code == 401

    # 2. Login with valid default password -> 200 + token
    login_res = client.post(
        "/api/v1/admin/login",
        json={"username": "admin", "password": "zerotoken2026"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    assert token

    # 3. Access protected /me endpoint
    me_res = client.get(
        "/api/v1/admin/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "admin"

    # 4. Change password
    change_res = client.post(
        "/api/v1/admin/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "zerotoken2026",
            "new_password": "UpdatedPassword2026!",
        },
    )
    assert change_res.status_code == 200
    new_token = change_res.json()["access_token"]

    # 5. Verify old password fails
    old_res = client.post(
        "/api/v1/admin/login",
        json={"username": "admin", "password": "zerotoken2026"},
    )
    assert old_res.status_code == 401

    # 6. Verify new password succeeds
    success_res = client.post(
        "/api/v1/admin/login",
        json={"username": "admin", "password": "UpdatedPassword2026!"},
    )
    assert success_res.status_code == 200

    # 7. Restore back to default for test cleanliness
    client.post(
        "/api/v1/admin/change-password",
        headers={"Authorization": f"Bearer {new_token}"},
        json={
            "current_password": "UpdatedPassword2026!",
            "new_password": "zerotoken2026",
        },
    )
