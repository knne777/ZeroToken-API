"""Pydantic schemas for request and response models."""

from typing import Any
from pydantic import BaseModel, Field


class TokenUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    thinking_tokens: int = 0
    cache_read_tokens: int = 0
    total_tokens: int = 0


class ChatRequest(BaseModel):
    message: str = Field(..., description="Message/prompt to send to the AI agent.")
    provider: str | None = Field(
        None, description="CLI provider: 'agy' (Antigravity), 'claude' (Claude Code), 'codex' (Codex). Defaults to active default provider."
    )
    conversation_id: str | None = Field(
        None, description="UUID of existing conversation to continue multi-turn chat. Leave empty to start a new chat."
    )
    model: str | None = Field(
        None, description="Model identifier (e.g. 'gemini-3.8-flash-high', 'claude-3-5-sonnet', 'gpt-5.5')."
    )
    effort: str | None = Field(
        None, description="Reasoning effort level (e.g. 'low', 'medium', 'high', 'xhigh', 'max')."
    )
    system_prompt: str | None = Field(
        None, description="Optional system instructions prefixed to the turn."
    )


class ChatResponse(BaseModel):
    provider: str
    model: str
    conversation_id: str
    response: str
    status: str = "SUCCESS"
    num_turns: int = 1
    duration_seconds: float = 0.0
    usage: TokenUsage


class ProviderStatus(BaseModel):
    name: str
    label: str
    installed: bool
    authenticated: bool
    executable: str | None = None
    reason: str | None = None


class ProvidersResponse(BaseModel):
    default_provider: str
    providers: dict[str, ProviderStatus]


class ModelsResponse(BaseModel):
    provider: str
    models: list[str]
