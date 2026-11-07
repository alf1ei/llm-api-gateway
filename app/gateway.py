import ipaddress
import time
from urllib.parse import urlsplit

import httpx

from .config import get_settings


class GatewayError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _validate_base_url(value: str) -> str:
    """Accept HTTPS endpoints, plus HTTP loopback for local development."""
    parsed = urlsplit(value)
    if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise GatewayError("Provider base_url is invalid", 503)
    try:
        address = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        address = None
    if address and not address.is_global and not address.is_loopback:
        raise GatewayError("Provider base_url cannot target a private or reserved IP", 503)
    is_loopback = parsed.hostname in {"localhost", "127.0.0.1", "::1"} or bool(address and address.is_loopback)
    if parsed.scheme != "https" and not (parsed.scheme == "http" and is_loopback):
        raise GatewayError("Provider base_url must use HTTPS (HTTP is allowed for loopback)", 503)
    return value.rstrip("/")


def resolve_model(model: str):
    providers = get_settings().providers()
    if not isinstance(model, str) or not model.strip():
        raise GatewayError("A model name is required", 400)
    if ":" in model:
        provider_name, upstream_model = model.split(":", 1)
    else:
        provider_name = providers.get("default_provider", "openai")
        upstream_model = model
    if not provider_name or not upstream_model:
        raise GatewayError("Model must use provider:model format", 400)
    provider = providers.get(provider_name)
    if not isinstance(provider, dict):
        raise GatewayError(f"Unknown provider: {provider_name}", 400)
    allowed_models = provider.get("models") or []
    if allowed_models and upstream_model not in allowed_models:
        raise GatewayError("Model is not enabled for this provider", 400)
    api_key = provider.get("api_key", "")
    if not isinstance(api_key, str) or not api_key.strip():
        raise GatewayError(f"Provider '{provider_name}' is missing an API key", 503)
    base_url = _validate_base_url(provider.get("base_url", ""))
    return provider_name, upstream_model, base_url, api_key


async def forward_chat(payload: dict, client: httpx.AsyncClient | None = None):
    provider_name, upstream_model, base_url, api_key = resolve_model(payload.get("model", ""))
    body = {**payload, "model": upstream_model}
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    started = time.perf_counter()
    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=get_settings().request_timeout)
    try:
        response = await client.post(f"{base_url}/chat/completions", json=body, headers=headers)
    except httpx.TimeoutException as exc:
        raise GatewayError("Upstream provider timed out", 504) from exc
    except httpx.HTTPError as exc:
        # Do not leak provider URLs, credentials, or low-level exception details.
        raise GatewayError("Upstream connection failed", 502) from exc
    finally:
        if owns_client:
            await client.aclose()
    latency_ms = int((time.perf_counter() - started) * 1000)
    try:
        data = response.json()
    except ValueError:
        data = {"error": {"message": "Upstream returned a non-JSON response"}}
    if not isinstance(data, (dict, list)):
        data = {"error": {"message": "Upstream returned an invalid response"}}
    return provider_name, upstream_model, response.status_code, data, latency_ms
