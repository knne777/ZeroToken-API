"""OpenAI-compatible request and response schemas."""

from typing import Any, Literal
from pydantic import BaseModel, Field


class OpenAIMessage(BaseModel):
    role: str = Field(..., description="Role: 'system', 'user', or 'assistant'")
    content: str = Field(..., description="Message text content")


class OpenAIChatRequest(BaseModel):
    model: str | None = Field("default", description="Model identifier")
    messages: list[OpenAIMessage] = Field(..., description="Array of messages")
    temperature: float | None = Field(None, description="Sampling temperature")
    response_format: dict[str, Any] | None = Field(None, description="Optional {'type': 'json_object'}")
    user: str | None = Field(None, description="Optional user identifier (can be conversation_id)")


class OpenAIChoiceMessage(BaseModel):
    role: str = "assistant"
    content: str


class OpenAIChoice(BaseModel):
    index: int = 0
    message: OpenAIChoiceMessage
    finish_reason: str = "stop"


class OpenAIUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class OpenAIChatResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[OpenAIChoice]
    usage: OpenAIUsage
