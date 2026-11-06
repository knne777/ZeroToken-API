"""ZeroToken API — Universal AI Chat Gateway and Platform."""

import time
import uuid
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.analytics.routes import router as analytics_router
from app.auth.routes import router as auth_router
from app.config import settings
from app.core.exceptions import ZeroTokenException
from app.db.database import execute_query, init_db
from app.keys.routes import router as keys_router
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    ModelsResponse,
    ProvidersResponse,
)
from app.openai_proxy.routes import router as openai_router
from app.providers.manager import provider_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database schema
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=settings.app_description,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS configuration to allow access from any web frontend or dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
@app.exception_handler(ZeroTokenException)
async def zerotoken_exception_handler(request: Request, exc: ZeroTokenException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": type(exc).__name__, "message": exc.message},
    )


# Mount routers
app.include_router(auth_router)
app.include_router(keys_router)
app.include_router(openai_router)
app.include_router(analytics_router)

# Mount React Frontend Studio if built
frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_dist.is_dir():
    assets_dir = frontend_dist / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
    app.mount("/studio", StaticFiles(directory=str(frontend_dist), html=True), name="studio")

    @app.get("/dashboard", include_in_schema=False)
    async def dashboard_redirect():
        return RedirectResponse(url="/studio/")


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
            "studio": "/studio",
            "chat": "POST /api/v1/chat",
            "openai_compatible": "POST /v1/chat/completions",
            "auth": "/api/v1/auth",
            "keys": "/api/v1/keys",
            "analytics": "/api/v1/analytics",
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
    """Execute a single-turn or multi-turn conversational AI turn with zero per-token billing."""
    chosen_provider_name = request.provider or await provider_manager.get_active_default()
    provider = provider_manager.get_provider(chosen_provider_name)

    # Prefix optional system prompt if present
    prompt = request.message
    if request.system_prompt:
        prompt = f"{request.system_prompt.strip()}\n\nUser: {request.message}"

    t0 = time.time()
    resp = await provider.run(
        prompt=prompt,
        conversation_id=request.conversation_id,
        model=request.model,
        effort=request.effort,
        attachments=request.attachments,
        timeout=settings.default_timeout_seconds,
    )
    elapsed_ms = (time.time() - t0) * 1000.0

    # Log telemetry for analytics & ROI calculation
    try:
        log_id = str(uuid.uuid4())
        inp = resp.usage.input_tokens
        out = resp.usage.output_tokens
        tot = resp.usage.total_tokens
        savings_usd = round((tot / 1_000_000.0) * 5.0, 5)

        await execute_query(
            """
            INSERT INTO request_logs (id, api_key_name, provider, model, status_code, duration_ms, input_tokens, output_tokens, total_tokens, savings_usd)
            VALUES (?, 'Native REST', ?, ?, 200, ?, ?, ?, ?, ?)
            """,
            (log_id, chosen_provider_name, resp.model, elapsed_ms, inp, out, tot, savings_usd),
        )
    except Exception:
        pass

    return resp
