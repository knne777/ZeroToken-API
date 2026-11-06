"""OpenAI Codex CLI provider implementation."""

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

logger = logging.getLogger("zerotoken.providers.codex")


class CodexProvider(BaseProvider):
    name = "codex"
    label = "OpenAI Codex"

    def __init__(self):
        self._executable: str | None = None

    def find_executable(self) -> str | None:
        if self._executable and os.path.exists(self._executable):
            return self._executable
        path = os.environ.get("PATH")
        found = shutil.which("codex", path=path)
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
                reason="Codex CLI not found on PATH. Install: npm install -g @openai/codex",
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
            "gpt-5.5",
            "gpt-5.6-luna",
            "gpt-6.1-sol",
            "gpt-5.6-terra",
            "o3-mini",
            "o1",
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
            raise ProviderUnavailableError(self.name, "Codex CLI not found on host PATH")

        # Execute codex CLI non-interactively
        cmd = [exe, "exec", "--skip-git-check"]
        if model:
            cmd.extend(["-m", model])
        cmd.append(prompt)

        with tempfile.TemporaryDirectory(prefix="zerotoken-codex-") as cwd:
            env = dict(os.environ)
            env["PWD"] = cwd

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
                raise ProviderExecutionError(
                    self.name, f"Codex CLI exited with code {proc.returncode}: {err_text[:300]}"
                )

            raw = stdout.decode(errors="replace").strip()
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
