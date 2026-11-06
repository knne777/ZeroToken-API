"""Anthropic Claude Code CLI provider implementation."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import tempfile

from app.core.exceptions import ProviderExecutionError, ProviderUnavailableError
from app.models.schemas import ChatResponse, ProviderStatus, TokenUsage
from app.providers.base import BaseProvider

logger = logging.getLogger("zerotoken.providers.claude")


class ClaudeProvider(BaseProvider):
    name = "claude"
    label = "Anthropic Claude Code"

    def __init__(self):
        self._executable: str | None = None

    def find_executable(self) -> str | None:
        if self._executable and os.path.exists(self._executable):
            return self._executable
        path = os.environ.get("PATH")
        found = shutil.which("claude", path=path)
        if found:
            self._executable = found
        return found

    async def preflight(self) -> ProviderStatus:
        exe = self.find_executable()
        if not exe:
            return ProviderStatus(
                name=self.name,
                label=self.label,
                installed=False,
                authenticated=False,
                reason="Claude Code CLI not found on PATH. Install: npm install -g @anthropic-ai/claude-code",
            )
        return ProviderStatus(
            name=self.name,
            label=self.label,
            installed=True,
            authenticated=True,
            executable=exe,
        )

    async def list_models(self) -> list[str]:
        return [
            "claude-3-7-sonnet",
            "claude-3-5-sonnet",
            "claude-3-5-haiku",
            "claude-3-opus",
        ]

    async def run(
        self,
        prompt: str,
        conversation_id: str | None = None,
        model: str | None = None,
        effort: str | None = None,
        timeout: float = 300.0,
    ) -> ChatResponse:
        exe = self.find_executable()
        if not exe:
            raise ProviderUnavailableError(self.name, "Claude CLI not found on host PATH")

        cmd = [
            exe,
            "-p",
            "--output-format",
            "json",
            "--tools",
            "",
            "--strict-mcp-config",
            "--safe-mode",
            "--setting-sources",
            "",
            "--disable-slash-commands",
            "--no-session-persistence",
        ]
        if conversation_id:
            cmd.extend(["--session-id", conversation_id])
        if model:
            cmd.extend(["--model", model])

        with tempfile.TemporaryDirectory(prefix="zerotoken-claude-") as cwd:
            env = dict(os.environ)
            env["PWD"] = cwd
            env["CLAUDE_CODE_SAFE_MODE"] = "1"

            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    cwd=cwd,
                    env=env,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(prompt.encode("utf-8")), timeout=timeout
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
                raise ProviderExecutionError(
                    self.name, f"Claude CLI exited with code {proc.returncode}: {err_text[:300]}"
                )

            raw = stdout.decode(errors="replace").strip()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as e:
                # Fallback to plain text if older CLI version
                return ChatResponse(
                    provider=self.name,
                    model=model or "default",
                    conversation_id=conversation_id or "",
                    response=raw,
                    status="SUCCESS",
                    num_turns=1,
                    duration_seconds=0.0,
                    usage=TokenUsage(),
                )

            response_text = str(payload.get("result") or "")
            conv_id = str(payload.get("session_id") or conversation_id or "")
            duration_ms = int(payload.get("duration_ms") or 0)
            duration_s = duration_ms / 1000.0

            raw_usage = payload.get("usage") or {}
            usage = TokenUsage(
                input_tokens=int(raw_usage.get("input_tokens") or 0),
                output_tokens=int(raw_usage.get("output_tokens") or 0),
                cache_read_tokens=int(raw_usage.get("cache_read_input_tokens") or 0),
                total_tokens=int(raw_usage.get("input_tokens") or 0)
                + int(raw_usage.get("output_tokens") or 0),
            )

            return ChatResponse(
                provider=self.name,
                model=model or "default",
                conversation_id=conv_id,
                response=response_text,
                status="SUCCESS",
                num_turns=1,
                duration_seconds=duration_s,
                usage=usage,
            )
