"""API endpoints for managing Virtual API Keys."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.keys.service import KeyService

router = APIRouter(prefix="/api/v1/keys", tags=["Virtual API Keys"])


class CreateKeyRequest(BaseModel):
    name: str = Field(..., description="Descriptive name for the key, e.g. 'Conta360 Backend', 'Support Bot'.")
    allowed_providers: list[str] | None = Field(
        None, description="List of authorized providers: ['agy', 'codex', 'claude']. Defaults to all."
    )
    allowed_models: list[str] | None = Field(None, description="Optional whitelist of allowed models.")
    rate_limit_rpm: int = Field(60, description="Rate limit requests per minute. Defaults to 60.")


@router.get("")
async def list_keys():
    """List all created virtual API keys with usage stats and masked prefixes."""
    return await KeyService.list_keys()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_key(req: CreateKeyRequest):
    """Generate a new virtual API key (prefix ztk_live_...). Secret is only displayed once."""
    if not req.name.strip():
        raise HTTPException(status_code=400, detail="Key name cannot be empty.")
    return await KeyService.create_key(
        name=req.name.strip(),
        allowed_providers=req.allowed_providers,
        allowed_models=req.allowed_models,
        rate_limit_rpm=req.rate_limit_rpm,
    )


@router.delete("/{key_id}")
async def revoke_key(key_id: str):
    """Permanently revoke and delete an API key."""
    success = await KeyService.revoke_key(key_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"API key '{key_id}' not found.")
    return {"status": "success", "message": f"API key '{key_id}' revoked."}
