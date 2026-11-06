"""One-Click CLI Authentication Manager for ZeroToken API."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import uuid
from pathlib import Path
from typing import Any

from app.db.database import execute_query, fetch_one

logger = logging.getLogger("zerotoken.auth")

# In-memory registry of active background login processes
ACTIVE_AUTH_PROCESSES: dict[str, asyncio.subprocess.Process] = {}


class AuthManager:
    """Manages CLI logins, device codes, and credential files."""

    @staticmethod
    def get_codex_status() -> dict[str, Any]:
        auth_file = Path.home() / ".codex" / "auth.json"
        installed = shutil.which("codex") is not None
        if not installed:
            nvm_path = Path.home() / ".nvm" / "versions" / "node"
            if nvm_path.is_dir():
                for node_ver in os.listdir(nvm_path):
                    cand = nvm_path / node_ver / "bin" / "codex"
                    if cand.is_file():
                        installed = True
                        break

        if not installed:
            return {
                "installed": False,
                "authenticated": False,
                "plan": None,
                "auth_method": None,
                "credential_path": str(auth_file),
                "message": "Codex CLI not installed. Run: npm install -g @openai/codex",
            }

        if not auth_file.is_file() or auth_file.stat().st_size == 0:
            return {
                "installed": True,
                "authenticated": False,
                "plan": None,
                "auth_method": None,
                "credential_path": str(auth_file),
                "message": "Not authenticated. Click 'Conectar con ChatGPT'.",
            }

        try:
            data = json.loads(auth_file.read_text(encoding="utf-8"))
            auth_mode = data.get("auth_mode", "chatgpt")
            return {
                "installed": True,
                "authenticated": True,
                "plan": "ChatGPT Plus / Pro" if auth_mode == "chatgpt" else "API Key",
                "auth_method": auth_mode,
                "credential_path": str(auth_file),
                "message": "Connected and active",
            }
        except Exception as e:
            return {
                "installed": True,
                "authenticated": False,
                "plan": None,
                "auth_method": None,
                "credential_path": str(auth_file),
                "message": f"Error reading auth file: {e}",
            }

    @staticmethod
    def get_agy_status() -> dict[str, Any]:
        auth_file = Path.home() / ".gemini" / "antigravity-cli" / "antigravity-oauth-token"
        installed = (
            shutil.which("agy") is not None
            or (Path.home() / ".local" / "bin" / "agy").is_file()
            or Path("/usr/local/bin/agy").is_file()
        )

        if not installed:
            return {
                "installed": False,
                "authenticated": False,
                "plan": None,
                "auth_method": None,
                "credential_path": str(auth_file),
                "message": "Antigravity CLI not installed.",
            }

        if not auth_file.is_file() or auth_file.stat().st_size == 0:
            return {
                "installed": True,
                "authenticated": False,
                "plan": None,
                "auth_method": None,
                "credential_path": str(auth_file),
                "message": "Not authenticated with Google.",
            }

        try:
            data = json.loads(auth_file.read_text(encoding="utf-8"))
            auth_method = data.get("auth_method", "oauth2")
            return {
                "installed": True,
                "authenticated": True,
                "plan": "Google Antigravity Subscription",
                "auth_method": auth_method,
                "credential_path": str(auth_file),
                "message": "Connected and active",
            }
        except Exception as e:
            return {
                "installed": True,
                "authenticated": False,
                "plan": None,
                "auth_method": None,
                "credential_path": str(auth_file),
                "message": f"Error reading token: {e}",
            }

    @staticmethod
    def get_claude_status() -> dict[str, Any]:
        creds_file = Path.home() / ".claude" / ".credentials.json"
        installed = shutil.which("claude") is not None

        if not installed:
            return {
                "installed": False,
                "authenticated": False,
                "plan": None,
                "auth_method": None,
                "credential_path": str(creds_file),
                "message": "Claude Code CLI not installed. Run: npm install -g @anthropic-ai/claude-code",
            }

        if not creds_file.is_file() or creds_file.stat().st_size == 0:
            return {
                "installed": True,
                "authenticated": False,
                "plan": None,
                "auth_method": None,
                "credential_path": str(creds_file),
                "message": "Not authenticated. Click 'Conectar con Claude'.",
            }

        try:
            data = json.loads(creds_file.read_text(encoding="utf-8"))
            oauth = data.get("claudeAiOauth", {})
            has_token = bool(oauth.get("accessToken"))
            return {
                "installed": True,
                "authenticated": has_token,
                "plan": "Claude Pro / Team / Max" if has_token else None,
                "auth_method": "oauth2" if has_token else None,
                "credential_path": str(creds_file),
                "message": "Connected and active" if has_token else "Credentials missing token.",
            }
        except Exception as e:
            return {
                "installed": True,
                "authenticated": False,
                "plan": None,
                "auth_method": None,
                "credential_path": str(creds_file),
                "message": f"Error reading credentials: {e}",
            }

    @classmethod
    def get_all_statuses(cls) -> dict[str, Any]:
        return {
            "codex": cls.get_codex_status(),
            "agy": cls.get_agy_status(),
            "claude": cls.get_claude_status(),
        }

    @classmethod
    async def start_login_session(cls, provider: str) -> dict[str, Any]:
        session_id = str(uuid.uuid4())

        if provider == "codex":
            exe = shutil.which("codex")
            if not exe:
                # Check nvm paths
                nvm_path = Path.home() / ".nvm" / "versions" / "node"
                if nvm_path.is_dir():
                    for node_ver in os.listdir(nvm_path):
                        cand = nvm_path / node_ver / "bin" / "codex"
                        if cand.is_file():
                            exe = str(cand)
                            break
            if not exe:
                raise RuntimeError("Codex CLI executable not found on host.")

            # Spawn codex login --device-auth
            proc = await asyncio.create_subprocess_exec(
                exe,
                "login",
                "--device-auth",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            ACTIVE_AUTH_PROCESSES[session_id] = proc

            # Read lines looking for code and URL
            user_code = None
            verification_url = "https://auth.openai.com/codex/device"

            try:
                # Wait up to 5 seconds for initial prompt output
                lines_read = []
                for _ in range(20):
                    line = await asyncio.wait_for(proc.stdout.readline(), timeout=5.0)
                    if not line:
                        break
                    text = line.decode("utf-8", errors="replace").strip()
                    # Strip ANSI color codes
                    text = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", text).strip()
                    lines_read.append(text)
                    if "auth.openai.com" in text:
                        m_url = re.search(r"https://auth\.openai\.com[^\s]+", text)
                        if m_url:
                            verification_url = m_url.group(0).rstrip(".,;")
                    m_code = re.search(r"([A-Z0-9]{4,5}-[A-Z0-9]{4,5})", text)
                    if m_code:
                        user_code = m_code.group(1)
                    if user_code and verification_url:
                        break

                if not user_code:
                    raise RuntimeError(f"Could not extract device code from codex: {' '.join(lines_read)}")

                # Save session in DB
                await execute_query(
                    """
                    INSERT INTO auth_sessions (id, provider, status, user_code, verification_url)
                    VALUES (?, ?, 'CODE_READY', ?, ?)
                    """,
                    (session_id, provider, user_code, verification_url),
                )

                # Launch async waiter in background
                asyncio.create_task(cls._wait_for_codex_completion(session_id, proc))

                return {
                    "session_id": session_id,
                    "provider": provider,
                    "status": "CODE_READY",
                    "user_code": user_code,
                    "verification_url": verification_url,
                    "instructions": "Abre el enlace de OpenAI y escribe el código para vincular tu suscripción de ChatGPT.",
                }

            except Exception as e:
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
                ACTIVE_AUTH_PROCESSES.pop(session_id, None)
                raise RuntimeError(f"Failed to start codex device auth: {e}") from e

        elif provider == "agy":
            # For Antigravity, token file path or OAuth direct consent
            auth_file = Path.home() / ".gemini" / "antigravity-cli" / "antigravity-oauth-token"
            await execute_query(
                """
                INSERT INTO auth_sessions (id, provider, status, verification_url)
                VALUES (?, ?, 'CODE_READY', ?)
                """,
                (session_id, provider, "https://accounts.google.com/"),
            )
            return {
                "session_id": session_id,
                "provider": provider,
                "status": "CODE_READY",
                "user_code": None,
                "verification_url": "https://accounts.google.com/",
                "instructions": (
                    "Google Antigravity utiliza el archivo OAuth en ~/.gemini/antigravity-cli/antigravity-oauth-token. "
                    "Puedes autorizar mediante el CLI o pegar tu token en la pestaña 'Importar Token'."
                ),
            }

        elif provider == "claude":
            creds_file = Path.home() / ".claude" / ".credentials.json"
            await execute_query(
                """
                INSERT INTO auth_sessions (id, provider, status, verification_url)
                VALUES (?, ?, 'CODE_READY', ?)
                """,
                (session_id, provider, "https://claude.ai/oauth"),
            )
            return {
                "session_id": session_id,
                "provider": provider,
                "status": "CODE_READY",
                "user_code": None,
                "verification_url": "https://claude.ai/oauth",
                "instructions": (
                    "Claude Code guarda sus credenciales en ~/.claude/.credentials.json. "
                    "Puedes ejecutar 'claude login' o importar el archivo de sesión."
                ),
            }

        else:
            raise ValueError(f"Unknown provider '{provider}'")

    @classmethod
    async def _wait_for_codex_completion(cls, session_id: str, proc: asyncio.subprocess.Process):
        try:
            stdout, stderr = await proc.communicate()
            if proc.returncode == 0:
                await execute_query(
                    "UPDATE auth_sessions SET status = 'SUCCESS' WHERE id = ?",
                    (session_id,),
                )
            else:
                err_text = stderr.decode(errors="replace").strip() or stdout.decode(errors="replace").strip()
                await execute_query(
                    "UPDATE auth_sessions SET status = 'FAILED', error_message = ? WHERE id = ?",
                    (err_text[:200], session_id),
                )
        except Exception as e:
            logger.error(f"Error waiting for codex login process: {e}")
            await execute_query(
                "UPDATE auth_sessions SET status = 'FAILED', error_message = ? WHERE id = ?",
                (str(e), session_id),
            )
        finally:
            ACTIVE_AUTH_PROCESSES.pop(session_id, None)

    @staticmethod
    async def get_session_status(session_id: str) -> dict[str, Any] | None:
        row = await fetch_one("SELECT * FROM auth_sessions WHERE id = ?", (session_id,))
        return row

    @staticmethod
    def import_credentials(provider: str, content: str) -> bool:
        content_str = content.strip()
        # Verify valid JSON
        json_data = json.loads(content_str)

        if provider == "codex":
            path = Path.home() / ".codex" / "auth.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(json_data, indent=2), encoding="utf-8")
            path.chmod(0o600)
            return True

        elif provider == "agy":
            path = Path.home() / ".gemini" / "antigravity-cli" / "antigravity-oauth-token"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(json_data, indent=2), encoding="utf-8")
            path.chmod(0o600)
            return True

        elif provider == "claude":
            path = Path.home() / ".claude" / ".credentials.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(json_data, indent=2), encoding="utf-8")
            path.chmod(0o600)
            return True

        return False

    @staticmethod
    def logout_provider(provider: str) -> bool:
        if provider == "codex":
            path = Path.home() / ".codex" / "auth.json"
            if path.is_file():
                path.unlink()
            return True
        elif provider == "agy":
            path = Path.home() / ".gemini" / "antigravity-cli" / "antigravity-oauth-token"
            if path.is_file():
                path.unlink()
            return True
        elif provider == "claude":
            path = Path.home() / ".claude" / ".credentials.json"
            if path.is_file():
                path.unlink()
            return True
        return False
