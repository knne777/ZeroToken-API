"""OpenAI Codex CLI provider implementation."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import shutil
import tempfile
import time

from app.core.exceptions import (
    ConversationNotFoundError,
    ProviderExecutionError,
    ProviderUnavailableError,
)
from app.models.schemas import ChatResponse, FileAttachment, ProviderStatus, TokenUsage
from app.providers.base import BaseProvider

logger = logging.getLogger("zerotoken.providers.codex")

FALLBACK_MODELS = [
    "gpt-6-luna",
    "gpt-5.6-luna",
    "gpt-5.6-terra",
    "gpt-reserve",
]


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
        if not found:
            # Check common nvm / npm global paths
            nvm_path = os.path.expanduser("~/.nvm/versions/node")
            if os.path.isdir(nvm_path):
                for node_ver in os.listdir(nvm_path):
                    candidate = os.path.join(nvm_path, node_ver, "bin", "codex")
                    if os.path.exists(candidate):
                        found = candidate
                        break
        if found:
            self._executable = found
        return found

    def _is_authenticated(self) -> bool:
        auth_file = os.path.expanduser("~/.codex/auth.json")
        return os.path.isfile(auth_file) and os.path.getsize(auth_file) > 0

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
        auth = self._is_authenticated()
        return ProviderStatus(
            name=self.name,
            label=self.label,
            installed=True,
            authenticated=auth,
            executable=exe,
            reason=None if auth else "Codex auth file (~/.codex/auth.json) not found. Run 'codex login'.",
        )

    async def list_models(self) -> list[str]:
        exe = self.find_executable()
        if exe:
            try:
                proc = await asyncio.create_subprocess_exec(
                    exe,
                    "debug",
                    "models",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)
                if proc.returncode == 0:
                    data = json.loads(stdout.decode(errors="replace"))
                    models = []
                    for m in data.get("models", []):
                        slug = m.get("slug")
                        if slug and slug != "codex-auto-review":
                            models.append(slug)
                    if models:
                        return models
            except Exception as e:
                logger.debug(f"Failed to dynamically query codex debug models: {e}")

        return list(FALLBACK_MODELS)

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
            raise ProviderUnavailableError(self.name, "Codex CLI not found on host PATH")

        t0 = time.perf_counter()

        with tempfile.TemporaryDirectory(prefix="zerotoken-codex-") as cwd:
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
                effective_prompt = (
                    f"[Archivos adjuntos en workspace: {', '.join(attached_files_info)}]\n\n{effective_prompt}"
                )

            # Build command line arguments
            if conversation_id:
                # Resuming an existing thread
                cmd = [
                    exe,
                    "exec",
                    "resume",
                    "--skip-git-repo-check",
                    "--json",
                ]
                if model:
                    cmd.extend(["-m", model])
                if effort:
                    cmd.extend(["-c", f'model_reasoning_effort="{effort}"'])
                cmd.append(conversation_id)
                cmd.append(effective_prompt)
            else:
                # Starting a new thread in read-only sandbox
                cmd = [
                    exe,
                    "exec",
                    "--sandbox",
                    "read-only",
                    "--skip-git-repo-check",
                    "--json",
                ]
                if model:
                    cmd.extend(["-m", model])
                if effort:
                    cmd.extend(["-c", f'model_reasoning_effort="{effort}"'])
                cmd.append(effective_prompt)

            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    cwd=cwd,
                    env=env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
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

            duration = time.perf_counter() - t0
            raw_stdout = stdout_bytes.decode(errors="replace").strip()
            raw_stderr = stderr_bytes.decode(errors="replace").strip()

            # Parse JSONL events
            thread_id: str | None = conversation_id
            messages: list[str] = []
            error_messages: list[str] = []
            usage_data: dict = {}

            for line in raw_stdout.splitlines():
                line = line.strip()
                if not line or not line.startswith("{"):
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                etype = event.get("type")
                if etype == "thread.started":
                    thread_id = event.get("thread_id") or thread_id
                elif etype == "item.completed":
                    item = event.get("item", {})
                    if item.get("type") == "agent_message":
                        text = item.get("text", "")
                        if text:
                            messages.append(text)
                    elif item.get("type") == "error":
                        err_text = item.get("message", "")
                        if err_text:
                            error_messages.append(err_text)
                elif etype == "turn.completed":
                    usage_data = event.get("usage", {})
                elif etype in ("turn.failed", "error"):
                    err = event.get("error")
                    if isinstance(err, dict):
                        err_text = err.get("message", "")
                        if err_text:
                            error_messages.append(err_text)
                    elif isinstance(event.get("message"), str):
                        error_messages.append(event["message"])

            # Check for non-existent session
            if "no rollout found for thread id" in raw_stderr.lower() or "thread/resume failed" in raw_stderr.lower():
                raise ConversationNotFoundError(conversation_id or "")

            if proc.returncode != 0:
                # If model is unsupported by ChatGPT subscription, clarify error
                combined_err = " | ".join(error_messages) if error_messages else (raw_stderr or raw_stdout)
                if "is not supported when using Codex with a ChatGPT account" in combined_err:
                    valid_models = await self.list_models()
                    raise ProviderExecutionError(
                        self.name,
                        f"The model '{model}' is not supported by your ChatGPT subscription in Codex. "
                        f"Supported models: {', '.join(valid_models)} (or omit 'model' for default)."
                    )
                raise ProviderExecutionError(
                    self.name,
                    f"Codex CLI exited with code {proc.returncode}: {combined_err[:400]}",
                )

            reply = "\n\n".join(messages).strip()
            if not reply and error_messages:
                raise ProviderExecutionError(self.name, "; ".join(error_messages))

            input_toks = int(usage_data.get("input_tokens") or 0)
            output_toks = int(usage_data.get("output_tokens") or 0)
            reasoning_toks = int(usage_data.get("reasoning_output_tokens") or 0)
            cached_toks = int(usage_data.get("cached_input_tokens") or 0)

            return ChatResponse(
                provider=self.name,
                model=model or "default",
                conversation_id=thread_id or "",
                response=reply,
                status="SUCCESS",
                num_turns=1,
                duration_seconds=round(duration, 3),
                usage=TokenUsage(
                    input_tokens=input_toks,
                    output_tokens=output_toks,
                    thinking_tokens=reasoning_toks,
                    cache_read_tokens=cached_toks,
                    total_tokens=input_toks + output_toks,
                ),
            )
