"""OpenAI-compatible router (/v1/chat/completions)."""

import time
import uuid
from fastapi import APIRouter, Header, HTTPException, status

from app.db.database import execute_query
from app.keys.service import KeyService
from app.models.schemas import ChatResponse
from app.openai_proxy.schemas import (
    OpenAIChatRequest,
    OpenAIChatResponse,
    OpenAIChoice,
    OpenAIChoiceMessage,
    OpenAIUsage,
)
from app.providers.manager import provider_manager

router = APIRouter(prefix="/v1", tags=["OpenAI Compatible Proxy"])


def _route_model_to_provider(model: str | None) -> tuple[str, str | None]:
    if not model or model == "default":
        return "agy", None

    m = model.lower()
    if any(k in m for k in ("gemini", "argon")):
        return "agy", model
    if any(k in m for k in ("gpt", "codex", "luna", "terra", "sol", "o1", "o3")):
        return "codex", model
    if "claude" in m or "sonnet" in m or "haiku" or "opus" in m:
        return "claude", model

    return "agy", model


@router.post("/chat/completions", response_model=OpenAIChatResponse)
async def create_chat_completion(
    req: OpenAIChatRequest,
    authorization: str | None = Header(None),
):
    """OpenAI-compatible drop-in replacement endpoint.

    Use with standard OpenAI libraries:
    ```python
    client = OpenAI(base_url="http://localhost:8000/v1", api_key="ztk_live_...")
    ```
    """
    key_info = None
    if authorization and authorization.startswith("Bearer "):
        raw_key = authorization.split("Bearer ", 1)[1].strip()
        if raw_key.startswith("ztk_"):
            key_info = await KeyService.validate_key(raw_key)
            if not key_info:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or revoked ZeroToken API key.",
                )

    # Route provider
    provider_name, target_model = _route_model_to_provider(req.model)
    provider = provider_manager.get_provider(provider_name)

    # Extract system prompt and user messages
    system_parts = []
    user_parts = []
    for msg in req.messages:
        if msg.role == "system":
            system_parts.append(msg.content)
        elif msg.role in ("user", "assistant"):
            prefix = "User" if msg.role == "user" else "Assistant"
            user_parts.append(f"{prefix}: {msg.content}")

    system_prompt = "\n".join(system_parts) if system_parts else None
    if req.response_format and req.response_format.get("type") == "json_object":
        json_instruction = "Responde estrictamente con un objeto JSON válido sin texto introductorio ni markdown."
        system_prompt = f"{system_prompt}\n{json_instruction}" if system_prompt else json_instruction

    final_message = "\n\n".join(user_parts) if user_parts else (req.messages[-1].content if req.messages else "")

    full_prompt = final_message
    if system_prompt:
        full_prompt = f"{system_prompt}\n\n{final_message}"

    t0 = time.time()
    chat_resp: ChatResponse = await provider.run(
        prompt=full_prompt,
        model=target_model,
        effort="low",  # fast by default
    )
    elapsed_ms = (time.time() - t0) * 1000.0

    # Calculate token usage and estimated dollars saved
    # OpenAI baseline: ~$5.00 per 1M blended tokens
    inp = chat_resp.usage.input_tokens
    out = chat_resp.usage.output_tokens
    tot = chat_resp.usage.total_tokens
    savings_usd = round((tot / 1_000_000.0) * 5.0, 5)

    # Log to database for ROI and analytics
    log_id = str(uuid.uuid4())
    key_id = key_info["id"] if key_info else None
    key_name = key_info["name"] if key_info else "Direct Local"

    await execute_query(
        """
        INSERT INTO request_logs (id, api_key_id, api_key_name, provider, model, status_code, duration_ms, input_tokens, output_tokens, total_tokens, savings_usd)
        VALUES (?, ?, ?, ?, ?, 200, ?, ?, ?, ?, ?)
        """,
        (log_id, key_id, key_name, provider_name, chat_resp.model, elapsed_ms, inp, out, tot, savings_usd),
    )

    return OpenAIChatResponse(
        id=f"chatcmpl-{chat_resp.conversation_id or uuid.uuid4().hex[:12]}",
        created=int(t0),
        model=chat_resp.model,
        choices=[
            OpenAIChoice(
                index=0,
                message=OpenAIChoiceMessage(
                    role="assistant",
                    content=chat_resp.response,
                ),
                finish_reason="stop",
            )
        ],
        usage=OpenAIUsage(
            prompt_tokens=inp,
            completion_tokens=out,
            total_tokens=tot,
        ),
    )
