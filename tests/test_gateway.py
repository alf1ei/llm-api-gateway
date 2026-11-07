import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import get_settings

@pytest.fixture(autouse=True)
def configure(monkeypatch, tmp_path):
    get_settings.cache_clear()
    monkeypatch.setenv("GATEWAY_API_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("PROVIDERS_JSON", json.dumps({
        "default_provider": "demo",
        "demo": {"base_url": "https://example.invalid/v1", "api_key": "upstream",
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
        assert client.get("/v1/models").status_code == 401

def test_lists_configured_models():
    with TestClient(app) as client:
        response = client.get("/v1/models", headers={"Authorization": "Bearer test-secret"})
        assert response.status_code == 200
        assert response.json()["data"][0]["id"] == "demo:test-model"

def test_unknown_provider_returns_400(monkeypatch):
    from app.gateway import resolve_model, GatewayError
    with pytest.raises(GatewayError) as error:
        resolve_model("missing:anything")
    assert error.value.status_code == 400
