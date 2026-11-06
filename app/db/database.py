"""SQLite database management for ZeroToken API."""

import os
import sqlite3
import asyncio
from pathlib import Path
from typing import Any

DB_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DB_PATH = DB_DIR / "zerotoken.db"


def get_connection() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    prefix TEXT NOT NULL,
                    hashed_key TEXT UNIQUE NOT NULL,
                    allowed_providers TEXT DEFAULT '["agy", "codex", "claude"]',
                    allowed_models TEXT,
                    rate_limit_rpm INTEGER DEFAULT 60,
                    requests_count INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used_at TIMESTAMP
                );
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS auth_sessions (
                    id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    status TEXT DEFAULT 'INITIALIZING',
                    user_code TEXT,
                    verification_url TEXT,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS request_logs (
                    id TEXT PRIMARY KEY,
                    api_key_id TEXT,
                    api_key_name TEXT,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    status_code INTEGER NOT NULL,
                    duration_ms REAL NOT NULL,
                    input_tokens INTEGER DEFAULT 0,
                    output_tokens INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    savings_usd REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS admin_users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    must_change_password INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Check if default admin exists; if not, create it
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM admin_users")
            count = cur.fetchone()[0]
            if count == 0:
                from app.auth.admin import hash_password
                import uuid
                default_user = os.environ.get("ZEROTOKEN_ADMIN_USER", "admin")
                default_pass = os.environ.get("ZEROTOKEN_ADMIN_PASSWORD", "zerotoken2026")
                pw_hash, salt = hash_password(default_pass)
                conn.execute(
                    """
                    INSERT INTO admin_users (id, username, password_hash, salt, must_change_password)
                    VALUES (?, ?, ?, ?, 1)
                    """,
                    (str(uuid.uuid4()), default_user, pw_hash, salt),
                )
    finally:
        conn.close()


async def execute_query(query: str, params: tuple = ()) -> None:
    def _run():
        conn = get_connection()
        try:
            with conn:
                conn.execute(query, params)
        finally:
            conn.close()

    await asyncio.to_thread(_run)


async def fetch_one(query: str, params: tuple = ()) -> dict[str, Any] | None:
    def _run():
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    return await asyncio.to_thread(_run)


async def fetch_all(query: str, params: tuple = ()) -> list[dict[str, Any]]:
    def _run():
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    return await asyncio.to_thread(_run)
