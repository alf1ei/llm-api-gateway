import time
import httpx
from .config import get_settings

class GatewayError(Exception):
    def __init__(self, message, status_code=502):
        self.message, self.status_code = message, status_code
        super().__init__(message)

def resolve_model(model: str):
    providers = get_settings().providers()
    if ":" in model:
        provider_name, upstream_model = model.split(":", 1)
    else:
        provider_name = providers.get("default_provider", "openai")
        upstream_model = model
    provider = providers.get(provider_name)
    if not isinstance(provider, dict):
        raise GatewayError(f"Unknown provider: {provider_name}", 400)
    base_url, api_key = provider.get("base_url", "").rstrip("/"), provider.get("api_key", "")
    if not base_url or not api_key:
        raise GatewayError(f"Provider '{provider_name}' is missing base_url or api_key", 503)
    return provider_name, upstream_model, base_url, api_key

async def forward_chat(payload: dict):
    provider_name, upstream_model, base_url, api_key = resolve_model(payload.get("model", ""))
    body = {**payload, "model": upstream_model}
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=get_settings().request_timeout) as client:
            response = await client.post(f"{base_url}/chat/completions", json=body, headers=headers)
    except httpx.TimeoutException:
        raise GatewayError("Upstream provider timed out", 504)
    except httpx.HTTPError as exc:
        raise GatewayError(f"Upstream connection failed: {exc}", 502)
    latency_ms = int((time.perf_counter() - started) * 1000)
    try:
        data = response.json()
    except ValueError:
        data = {"error": {"message": response.text[:1000]}}
    return provider_name, upstream_model, response.status_code, data, latency_ms
