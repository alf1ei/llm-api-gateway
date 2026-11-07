import hmac
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from .config import get_settings
from .db import init_db, log_usage, recent_usage
from .gateway import GatewayError, forward_chat


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    model: str = Field(min_length=1, max_length=200)
    messages: list[dict] = Field(min_length=1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    app.state.http_client = httpx.AsyncClient(timeout=get_settings().request_timeout)
    try:
        yield
    finally:
        await app.state.http_client.aclose()


app = FastAPI(
    title="LLM API Gateway",
    version="0.2.0",
    description="A secure, OpenAI-compatible multi-provider gateway.",
    lifespan=lifespan,
)


def verify_key(authorization: str | None = Header(default=None)):
    expected = get_settings().gateway_api_key
    if not expected or expected == "change-me":
        raise HTTPException(503, "Set a strong GATEWAY_API_KEY before using the gateway.")
    scheme, _, supplied = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not hmac.compare_digest(supplied.strip(), expected):
        raise HTTPException(401, "Invalid gateway API key.", headers={"WWW-Authenticate": "Bearer"})


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/v1/models", dependencies=[Depends(verify_key)])
def models():
    try:
        providers = get_settings().providers()
    except ValueError as exc:
        raise HTTPException(503, str(exc)) from exc
    data = []
    for provider_name, provider in providers.items():
        if provider_name == "default_provider" or not isinstance(provider, dict):
            continue
        for model in provider.get("models", []):
            data.append({"id": f"{provider_name}:{model}", "object": "model", "owned_by": provider_name})
    return {"object": "list", "data": data}


@app.post("/v1/chat/completions", dependencies=[Depends(verify_key)])
async def chat_completions(payload: ChatCompletionRequest):
    try:
        provider, model, status, data, latency = await forward_chat(
            payload.model_dump(), getattr(app.state, "http_client", None)
        )
        usage_data = data.get("usage", {}) if isinstance(data, dict) else {}
        log_usage(provider, model, status, usage_data, latency)
        return JSONResponse(status_code=status, content=data)
    except GatewayError as exc:
        raise HTTPException(exc.status_code, exc.message) from exc


@app.get("/admin/usage", dependencies=[Depends(verify_key)])
def usage(limit: int = Query(default=100, ge=1, le=1000)):
    return {"data": recent_usage(limit)}
