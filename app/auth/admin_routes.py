"""Endpoints for Admin Login and Password Management."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth.admin import (
    create_token,
    get_current_admin,
    hash_password,
    verify_password,
)
from app.db.database import execute_query, fetch_one

router = APIRouter(prefix="/api/v1/admin", tags=["Admin Authentication"])


class AdminLoginRequest(BaseModel):
    username: str = Field(..., description="Administrator username (e.g. 'admin')")
    password: str = Field(..., description="Administrator password")


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=6, description="New password (minimum 6 characters)")


@router.post("/login")
async def login(req: AdminLoginRequest):
    """Authenticate administrator and return access token."""
    user = await fetch_one("SELECT * FROM admin_users WHERE username = ?", (req.username.strip(),))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos.",
        )

    if not verify_password(req.password, user["password_hash"], user["salt"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos.",
        )

    token = create_token(user["username"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user["username"],
        "must_change_password": bool(user["must_change_password"]),
    }


@router.get("/me")
async def get_me(username: str = Depends(get_current_admin)):
    """Return profile details of the currently authenticated administrator."""
    user = await fetch_one("SELECT id, username, must_change_password, created_at, updated_at FROM admin_users WHERE username = ?", (username,))
    if not user:
        raise HTTPException(status_code=404, detail="Admin user not found.")
    return {
        "id": user["id"],
        "username": user["username"],
        "must_change_password": bool(user["must_change_password"]),
        "created_at": user["created_at"],
        "updated_at": user["updated_at"],
    }


@router.post("/change-password")
async def change_password(req: ChangePasswordRequest, username: str = Depends(get_current_admin)):
    """Change the administrator password."""
    user = await fetch_one("SELECT * FROM admin_users WHERE username = ?", (username,))
    if not user:
        raise HTTPException(status_code=404, detail="Admin user not found.")

    if not verify_password(req.current_password, user["password_hash"], user["salt"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual es incorrecta.",
        )

    if req.new_password == req.current_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La nueva contraseña no puede ser idéntica a la actual.",
        )

    pw_hash, salt = hash_password(req.new_password)
    await execute_query(
        """
        UPDATE admin_users
        SET password_hash = ?, salt = ?, must_change_password = 0, updated_at = CURRENT_TIMESTAMP
        WHERE username = ?
        """,
        (pw_hash, salt, username),
    )

    # Return refreshed token
    new_token = create_token(username)
    return {
        "status": "success",
        "message": "Contraseña actualizada exitosamente.",
        "access_token": new_token,
    }


@router.post("/logout")
async def logout(username: str = Depends(get_current_admin)):
    """Log out admin session."""
    return {"status": "success", "message": "Sesión cerrada correctamente."}
