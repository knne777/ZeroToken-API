"""Virtual API Key service for ZeroToken Platform."""

import hashlib
import json
import secrets
import uuid
from typing import Any

from app.db.database import execute_query, fetch_all, fetch_one


class KeyService:
    @staticmethod
    def generate_raw_key(prefix: str = "ztk_live_") -> str:
        random_part = secrets.token_hex(24)
        return f"{prefix}{random_part}"

    @staticmethod
    def hash_key(raw_key: str) -> str:
        return hashlib.sha256(raw_key.strip().encode("utf-8")).hexdigest()

    @classmethod
    async def create_key(
        cls,
        name: str,
        allowed_providers: list[str] | None = None,
        allowed_models: list[str] | None = None,
        rate_limit_rpm: int = 60,
    ) -> dict[str, Any]:
        key_id = str(uuid.uuid4())
        raw_key = cls.generate_raw_key()
        hashed = cls.hash_key(raw_key)
        prefix_display = f"{raw_key[:12]}...{raw_key[-4:]}"

        providers_json = json.dumps(allowed_providers or ["agy", "codex", "claude"])
        models_json = json.dumps(allowed_models) if allowed_models else None

        await execute_query(
            """
            INSERT INTO api_keys (id, name, prefix, hashed_key, allowed_providers, allowed_models, rate_limit_rpm)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (key_id, name, prefix_display, hashed, providers_json, models_json, rate_limit_rpm),
        )

        return {
            "id": key_id,
            "name": name,
            "prefix": prefix_display,
            "raw_key": raw_key,  # ONLY returned once upon creation!
            "allowed_providers": json.loads(providers_json),
            "rate_limit_rpm": rate_limit_rpm,
            "message": "Guarda esta clave en un lugar seguro. No se volverá a mostrar completa.",
        }

    @classmethod
    async def list_keys(cls) -> list[dict[str, Any]]:
        rows = await fetch_all(
            """
            SELECT id, name, prefix, allowed_providers, allowed_models, rate_limit_rpm, requests_count, is_active, created_at, last_used_at
            FROM api_keys
            ORDER BY created_at DESC
            """
        )
        results = []
        for r in rows:
            results.append({
                "id": r["id"],
                "name": r["name"],
                "prefix": r["prefix"],
                "allowed_providers": json.loads(r["allowed_providers"]) if r["allowed_providers"] else [],
                "allowed_models": json.loads(r["allowed_models"]) if r["allowed_models"] else None,
                "rate_limit_rpm": r["rate_limit_rpm"],
                "requests_count": r["requests_count"],
                "is_active": bool(r["is_active"]),
                "created_at": r["created_at"],
                "last_used_at": r["last_used_at"],
            })
        return results

    @classmethod
    async def revoke_key(cls, key_id: str) -> bool:
        row = await fetch_one("SELECT id FROM api_keys WHERE id = ?", (key_id,))
        if not row:
            return False
        await execute_query("DELETE FROM api_keys WHERE id = ?", (key_id,))
        return True

    @classmethod
    async def validate_key(cls, raw_key: str) -> dict[str, Any] | None:
        if not raw_key:
            return None
        hashed = cls.hash_key(raw_key)
        row = await fetch_one(
            "SELECT * FROM api_keys WHERE hashed_key = ? AND is_active = 1",
            (hashed,),
        )
        if not row:
            return None

        # Update last_used_at and increment requests_count
        await execute_query(
            "UPDATE api_keys SET requests_count = requests_count + 1, last_used_at = CURRENT_TIMESTAMP WHERE id = ?",
            (row["id"],),
        )
        return dict(row)
