"""Admin authentication, password hashing, and session management."""

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any
from fastapi import Header, HTTPException, status
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
SECRET_FILE = DATA_DIR / ".jwt_secret"


def get_jwt_secret() -> str:
    env_secret = os.environ.get("ZEROTOKEN_JWT_SECRET")
    if env_secret:
        return env_secret

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if SECRET_FILE.is_file():
        return SECRET_FILE.read_text(encoding="utf-8").strip()

    generated = secrets.token_hex(32)
    SECRET_FILE.write_text(generated, encoding="utf-8")
    SECRET_FILE.chmod(0o600)
    return generated


def hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    if salt is None:
        salt = secrets.token_bytes(32)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return derived.hex(), salt.hex()


def verify_password(password: str, expected_hash_hex: str, salt_hex: str) -> bool:
    salt = bytes.fromhex(salt_hex)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return hmac.compare_digest(derived.hex(), expected_hash_hex)


def create_token(username: str, expires_in_days: int = 7) -> str:
    secret = get_jwt_secret().encode("utf-8")
    payload = {
        "sub": username,
        "exp": int(time.time()) + (expires_in_days * 86400),
        "nonce": secrets.token_hex(8),
    }
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8").rstrip("=")
    signature = hmac.new(secret, payload_b64.encode("utf-8"), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")
    return f"{payload_b64}.{sig_b64}"


def verify_token(token: str) -> str | None:
    try:
        parts = token.strip().split(".")
        if len(parts) != 2:
            return None
        payload_b64, sig_b64 = parts
        secret = get_jwt_secret().encode("utf-8")

        # Verify signature
        expected_sig = hmac.new(secret, payload_b64.encode("utf-8"), hashlib.sha256).digest()
        # Pad base64 if needed
        pad_len = 4 - (len(sig_b64) % 4)
        sig_padded = sig_b64 + ("=" * (pad_len % 4))
        actual_sig = base64.urlsafe_b64decode(sig_padded.encode("utf-8"))

        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        # Parse payload
        pad_payload_len = 4 - (len(payload_b64) % 4)
        payload_padded = payload_b64 + ("=" * (pad_payload_len % 4))
        payload = json.loads(base64.urlsafe_b64decode(payload_padded.encode("utf-8")).decode("utf-8"))

        if payload.get("exp", 0) < time.time():
            return None

        return payload.get("sub")
    except Exception:
        return None


async def get_current_admin(authorization: str | None = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authentication token. Please log in.",
        )
    token = authorization.split("Bearer ", 1)[1].strip()
    username = verify_token(token)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid token. Please log in again.",
        )
    return username
