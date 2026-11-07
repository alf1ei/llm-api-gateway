import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


@pytest.fixture(autouse=True)
def configure(monkeypatch, tmp_path):
    monkeypatch.setenv("GATEWAY_API_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("PROVIDERS_JSON", json.dumps({
        "default_provider": "demo",
        "demo": {"base_url": "https://api.example.com/v1", "api_key": "upstream",
                 "models": ["test-model"]}
    }))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_health():
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}


def test_rejects_missing_key():
    with TestClient(app) as client:
        response = client.get("/v1/models")
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"


def test_lists_configured_models():
    with TestClient(app) as client:
        response = client.get("/v1/models", headers={"Authorization": "Bearer test-secret"})
        assert response.status_code == 200
        assert response.json()["data"][0]["id"] == "demo:test-model"


def test_unknown_provider_returns_400():
    from app.gateway import GatewayError, resolve_model
    with pytest.raises(GatewayError) as error:
        resolve_model("missing:anything")
    assert error.value.status_code == 400


def test_model_allowlist_is_enforced():
    from app.gateway import GatewayError, resolve_model
    with pytest.raises(GatewayError, match="not enabled"):
        resolve_model("demo:unlisted-model")


def test_private_provider_ip_is_rejected(monkeypatch):
    from app.gateway import GatewayError, resolve_model
    monkeypatch.setenv("PROVIDERS_JSON", json.dumps({
        "demo": {"base_url": "http://192.168.1.2/v1", "api_key": "secret", "models": ["m"]}
    }))
    get_settings.cache_clear()
    with pytest.raises(GatewayError, match="private"):
        resolve_model("demo:m")


def test_request_requires_messages():
    with TestClient(app) as client:
        response = client.post("/v1/chat/completions", headers={"Authorization": "Bearer test-secret"},
                               json={"model": "demo:test-model"})
        assert response.status_code == 422


def test_forward_chat_uses_provider_model_and_returns_usage():
    from app.gateway import forward_chat

    async def handler(request):
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer upstream"
        assert request.read()  # body is sent
        return httpx.Response(200, json={"id": "chatcmpl-test", "usage": {"total_tokens": 3}})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await forward_chat({"model": "demo:test-model", "messages": [{"role": "user", "content": "hi"}]}, client)

    import asyncio
    result = asyncio.run(run())
    assert result[0:3] == ("demo", "test-model", 200)
    assert result[3]["usage"]["total_tokens"] == 3
