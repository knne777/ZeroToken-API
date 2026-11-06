"""Google Antigravity (agy) provider implementation."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import shutil
import tempfile
from pathlib import Path

from app.core.exceptions import (
    ConversationNotFoundError,
    ProviderExecutionError,
    ProviderUnavailableError,
)
from app.models.schemas import ChatResponse, FileAttachment, ProviderStatus, TokenUsage
from app.providers.base import BaseProvider

logger = logging.getLogger("zerotoken.providers.agy")


class AgyProvider(BaseProvider):
    name = "agy"
    label = "Google Antigravity"

    def __init__(self):
        self._executable: str | None = None

    def find_executable(self) -> str | None:
        if self._executable and os.path.exists(self._executable):
            return self._executable
        path = os.environ.get("PATH")
        found = shutil.which("agy", path=path)
        if found:
            self._executable = found
            return found
        user_bin = Path.home() / ".local" / "bin" / "agy"
        if user_bin.is_file() and os.access(user_bin, os.X_OK):
            self._executable = str(user_bin)
            return str(user_bin)
        usr_bin = Path("/usr/local/bin/agy")
        if usr_bin.is_file() and os.access(usr_bin, os.X_OK):
            self._executable = str(usr_bin)
            return str(usr_bin)
        return None

    async def preflight(self) -> ProviderStatus:
        exe = self.find_executable()
        if not exe:
            return ProviderStatus(
                name=self.name,
                label=self.label,
                installed=False,
                authenticated=False,
                reason="agy CLI not found on PATH or in ~/.local/bin/agy",
            )
        try:
            proc = await asyncio.create_subprocess_exec(
                exe,
                "--help",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.communicate(), timeout=10.0)
            if proc.returncode == 0:
                return ProviderStatus(
                    name=self.name,
                    label=self.label,
                    installed=True,
                    authenticated=True,
                    executable=exe,
                )
        except Exception as e:
            return ProviderStatus(
                name=self.name,
                label=self.label,
                installed=True,
                authenticated=False,
                executable=exe,
                reason=f"Preflight execution failed: {e}",
            )

        return ProviderStatus(
            name=self.name,
            label=self.label,
            installed=True,
            authenticated=True,
            executable=exe,
        )

    async def list_models(self) -> list[str]:
        exe = self.find_executable()
        if not exe:
            return []
        try:
            proc = await asyncio.create_subprocess_exec(
                exe,
                "models",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15.0)
            lines = stdout.decode("utf-8", errors="replace").splitlines()
            models = []
            for line in lines:
                parts = line.strip().split()
                if parts and not parts[0].startswith("⠋") and not parts[0].startswith("⠙"):
                    models.append(parts[0])
            return models or [
                "gemini-3.8-flash-high",
                "gemini-3.8-flash-medium",
                "gemini-4-argon-medium",
                "claude-opus-5-5-high",
                "claude-sonnet-5-5-high",
            ]
        except Exception:
            return [
                "gemini-3.8-flash-high",
                "gemini-3.8-flash-medium",
                "gemini-4-argon-medium",
                "claude-opus-5-5-high",
                "claude-sonnet-5-5-high",
            ]

    async def run(
        self,
        prompt: str,
        conversation_id: str | None = None,
        model: str | None = None,
        effort: str | None = None,
        attachments: list[FileAttachment] | None = None,
        timeout: float = 300.0,
    ) -> ChatResponse:
        exe = self.find_executable()
        if not exe:
            raise ProviderUnavailableError(self.name, "agy executable not found on host")

        if conversation_id:
            conv_db = (
                Path.home()
                / ".gemini"
                / "antigravity-cli"
                / "conversations"
                / f"{conversation_id}.db"
            )
            conv_brain = (
                Path.home() / ".gemini" / "antigravity-cli" / "brain" / conversation_id
            )
            if not conv_db.exists() and not conv_brain.exists():
                raise ConversationNotFoundError(conversation_id)

        # Enforce sandbox rules that prevent host shell tool execution and transcript snooping
        # while permitting structured JSON, tables, code, or custom schemas requested in system_prompt
        sandbox_instruction = (
            "Seguridad y Sandbox: Tienes estrictamente prohibido ejecutar comandos de terminal (bash/shell), "
            "invocar herramientas del sistema operativo local o acceder a archivos y transcripciones fuera de este directorio de trabajo. "
            "Responde directamente como texto hacia el usuario cumpliendo fielmente el formato, esquema "
            "(JSON estructurado, texto plano, tablas, etc.) o instrucciones de rol solicitadas en el prompt."
        )

        effective_effort = effort or "low"

        with tempfile.TemporaryDirectory(prefix="zerotoken-agy-") as cwd:
            env = dict(os.environ)
            env["PWD"] = cwd

            attached_files_info: list[str] = []
            if attachments:
                for att in attachments:
                    safe_name = os.path.basename(att.name)
                    dest_path = os.path.join(cwd, safe_name)
                    try:
                        content_bytes = base64.b64decode(att.content_base64)
                        with open(dest_path, "wb") as f:
                            f.write(content_bytes)
                        attached_files_info.append(safe_name)
                    except Exception as err:
                        logger.warning(f"Failed to decode attachment '{att.name}': {err}")

            effective_prompt = prompt
            if attached_files_info:
                files_notice = f"[Archivos adjuntos disponibles en el espacio de trabajo: {', '.join(attached_files_info)}]"
                effective_prompt = f"{files_notice}\n\n{effective_prompt}"

            if not conversation_id:
                effective_prompt = f"[{sandbox_instruction}]\n\n{effective_prompt}"

            cmd = [
                exe,
                "-p",
                effective_prompt,
                "--output-format",
                "json",
                "--disable-slash-commands",
                "--mode",
                "plan",
                "--effort",
                effective_effort,
            ]
            if conversation_id:
                cmd.extend(["--conversation", conversation_id])
            if model:
                cmd.extend(["--model", model])

            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    cwd=cwd,
                    env=env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                    await proc.wait()
                except ProcessLookupError:
                    pass
                raise ProviderExecutionError(
                    self.name, f"Execution timed out after {timeout:.0f}s", retryable=True
                )

            if proc.returncode != 0:
                err_text = stderr.decode(errors="replace").strip()
                out_text = stdout.decode(errors="replace").strip() if stdout else ""
                combined = f"{err_text} {out_text}".strip()
                raise ProviderExecutionError(
                    self.name, f"Process exited with code {proc.returncode}: {combined[:300]}"
                )

            raw = stdout.decode(errors="replace").strip()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as e:
                raise ProviderExecutionError(
                    self.name, f"Invalid JSON output from CLI: {raw[:200]}"
                ) from e

            if payload.get("status") == "ERROR":
                raise ProviderExecutionError(
                    self.name, payload.get("error") or "Unknown error reported by CLI"
                )

            response_text = str(payload.get("response") or "").strip()
            conv_id = str(payload.get("conversation_id") or conversation_id or "")
            duration_s = float(payload.get("duration_seconds") or 0.0)
            turns = int(payload.get("num_turns") or 1)

            raw_usage = payload.get("usage") or {}
            usage = TokenUsage(
                input_tokens=int(raw_usage.get("input_tokens") or 0),
                output_tokens=int(raw_usage.get("output_tokens") or 0),
                thinking_tokens=int(raw_usage.get("thinking_tokens") or 0),
                cache_read_tokens=int(raw_usage.get("cache_read_tokens") or 0),
                total_tokens=int(raw_usage.get("total_tokens") or 0),
            )

            return ChatResponse(
                provider=self.name,
                model=model or "default",
                conversation_id=conv_id,
                response=response_text,
                status="SUCCESS",
                num_turns=turns,
                duration_seconds=duration_s,
                usage=usage,
            )
