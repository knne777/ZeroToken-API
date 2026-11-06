"""ZeroToken API — FastAPI entrypoint and routes."""

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.exceptions import ZeroTokenException
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    ModelsResponse,
    ProvidersResponse,
)
from app.providers.manager import provider_manager

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=settings.app_description,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration to allow access from any web frontend or dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ZeroTokenException)
async def zerotoken_exception_handler(request: Request, exc: ZeroTokenException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": type(exc).__name__, "message": exc.message},
    )


@app.get("/", tags=["Info"])
async def root():
    default_p = await provider_manager.get_active_default()
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "description": settings.app_description,
        "default_provider": default_p,
        "documentation": "/docs",
        "endpoints": {
            "chat": "POST /api/v1/chat",
            "providers": "GET /api/v1/providers",
            "models": "GET /api/v1/models",
            "health": "GET /health",
        },
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version}


@app.get("/api/v1/providers", response_model=ProvidersResponse, tags=["Providers"])
async def list_providers():
    """Inspect local CLI engines (Antigravity, Claude Code, Codex) and report health."""
    statuses = await provider_manager.get_all_statuses()
    default_p = await provider_manager.get_active_default()
    return ProvidersResponse(default_provider=default_p, providers=statuses)


@app.get("/api/v1/models", response_model=list[ModelsResponse], tags=["Models"])
async def list_models(provider: str | None = None):
    """List available models for one or all active providers."""
    if provider:
        p = provider_manager.get_provider(provider)
        models = await p.list_models()
        return [ModelsResponse(provider=p.name, models=models)]

    results = []
    statuses = await provider_manager.get_all_statuses()
    for name, p in provider_manager.providers.items():
        if statuses[name].installed:
            models = await p.list_models()
            results.append(ModelsResponse(provider=name, models=models))
    return results


@app.post("/api/v1/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest):
    """Execute a single-turn or multi-turn conversational AI turn with zero per-token billing.

    - Set `conversation_id` to continue an ongoing conversation with native context memory.
    - Leave `conversation_id` empty to generate a fresh new conversation.
    - Select `provider`: 'agy' (default), 'claude', or 'codex'.
    """
    chosen_provider_name = request.provider or await provider_manager.get_active_default()
    provider = provider_manager.get_provider(chosen_provider_name)

    # Prefix optional system prompt if present
    prompt = request.message
    if request.system_prompt:
        prompt = f"{request.system_prompt.strip()}\n\nUser: {request.message}"

    return await provider.run(
        prompt=prompt,
        conversation_id=request.conversation_id,
        model=request.model,
        effort=request.effort,
        timeout=settings.default_timeout_seconds,
    )
