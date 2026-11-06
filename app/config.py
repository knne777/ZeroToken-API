"""Configuration for ZeroToken API."""

import os
from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "ZeroToken API"
    app_version: str = "1.0.0"
    app_description: str = (
        "Universal AI Chat Gateway powered by your local subscriptions (Antigravity, Claude Code, Codex). "
        "Zero API keys, zero per-token billing."
    )
    host: str = os.getenv("ZEROTOKEN_HOST", "0.0.0.0")
    port: int = int(os.getenv("ZEROTOKEN_PORT", "8000"))
    default_provider: str = os.getenv("ZEROTOKEN_DEFAULT_PROVIDER", "agy")
    default_timeout_seconds: float = float(os.getenv("ZEROTOKEN_TIMEOUT", "300.0"))


settings = Settings()
