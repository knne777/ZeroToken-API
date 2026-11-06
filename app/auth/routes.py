"""Authentication API endpoints for ZeroToken CLI Auth Engine."""

from typing import Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.auth.manager import AuthManager

router = APIRouter(prefix="/api/v1/auth", tags=["CLI Authentication"])


class TokenImportRequest(BaseModel):
    content: str = Field(..., description="JSON string or file contents of the token/credentials.")


@router.get("/status")
async def get_auth_status():
    """Get real-time connection and subscription status for all CLI providers."""
    return AuthManager.get_all_statuses()


@router.post("/{provider}/start")
async def start_auth_session(provider: str):
    """Start an interactive login session (e.g. Device Code flow for Codex)."""
    if provider not in ("codex", "agy", "claude"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provider '{provider}' not supported for login orchestration.",
        )
    try:
        session = await AuthManager.start_login_session(provider)
        return session
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start login session: {e}",
        )


@router.get("/session/{session_id}")
async def get_session_status(session_id: str):
    """Poll the status of an active login session (e.g. CODE_READY, SUCCESS, FAILED)."""
    sess = await AuthManager.get_session_status(session_id)
    if not sess:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Auth session '{session_id}' not found.",
        )
    return sess


@router.post("/{provider}/token")
async def import_token(provider: str, req: TokenImportRequest):
    """Directly import credentials JSON for a provider."""
    if provider not in ("codex", "agy", "claude"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provider '{provider}' not supported.",
        )
    try:
        success = AuthManager.import_credentials(provider, req.content)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to import credentials.")
        return {"status": "success", "provider": provider, "message": "Credentials imported successfully."}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON credentials format: {e}",
        )


@router.post("/{provider}/logout")
async def logout_provider(provider: str):
    """Safely log out by removing the provider's local credential file."""
    if provider not in ("codex", "agy", "claude"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provider '{provider}' not supported.",
        )
    AuthManager.logout_provider(provider)
    return {"status": "success", "provider": provider, "message": f"Successfully logged out of {provider}."}
