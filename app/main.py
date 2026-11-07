from contextlib import asynccontextmanager
from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.responses import JSONResponse
from .config import get_settings
from .db import init_db, log_usage, recent_usage
from .gateway import forward_chat, GatewayError

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="LLM API Gateway", version="0.1.0",
              description="A lightweight OpenAI-compatible multi-provider gateway.",
              lifespan=lifespan)

def verify_key(authorization: str | None = Header(default=None)):
    expected = get_settings().gateway_api_key
    supplied = authorization.removeprefix("Bearer ").strip() if authorization else ""
    if not expected or expected == "change-me":
        raise HTTPException(503, "Set a strong GATEWAY_API_KEY before using the gateway.")
    if supplied != expected:
        raise HTTPException(401, "Invalid gateway API key.")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/v1/models", dependencies=[Depends(verify_key)])
def models():
    data = []
    for name, provider in get_settings().providers().items():
        if name == "default_provider" or not isinstance(provider, dict):
            continue
        for model in provider.get("models", []):
            data.append({"id": f"{name}:{model}", "object": "model", "owned_by": name})
    return {"object": "list", "data": data}

@app.post("/v1/chat/completions", dependencies=[Depends(verify_key)])
async def chat_completions(payload: dict):
    if not payload.get("model"):
        raise HTTPException(400, "model is required")
    try:
        provider, model, status, data, latency = await forward_chat(payload)
        usage = data.get("usage", {}) if isinstance(data, dict) else {}
        log_usage(provider, model, status, usage, latency)
        return JSONResponse(status_code=status, content=data)
    except GatewayError as exc:
        raise HTTPException(exc.status_code, exc.message)

@app.get("/admin/usage", dependencies=[Depends(verify_key)])
def usage():
    return {"data": recent_usage()}
