"""Provider manager and dispatcher for ZeroToken API."""

from __future__ import annotations

import logging
from typing import Dict

from app.config import settings
from app.core.exceptions import ProviderNotFoundError
from app.models.schemas import ProviderStatus
from app.providers.agy import AgyProvider
from app.providers.base import BaseProvider
from app.providers.claude import ClaudeProvider
from app.providers.codex import CodexProvider

logger = logging.getLogger("zerotoken.manager")


class ProviderManager:
    def __init__(self):
        self.providers: Dict[str, BaseProvider] = {
            "agy": AgyProvider(),
            "claude": ClaudeProvider(),
            "codex": CodexProvider(),
        }

    def get_provider(self, name: str | None = None) -> BaseProvider:
        provider_name = (name or settings.default_provider).strip().lower()
        if provider_name not in self.providers:
            raise ProviderNotFoundError(provider_name)
        return self.providers[provider_name]

    async def get_all_statuses(self) -> dict[str, ProviderStatus]:
        statuses = {}
        for name, provider in self.providers.items():
            statuses[name] = await provider.preflight()
        return statuses

    async def get_active_default(self) -> str:
        statuses = await self.get_all_statuses()
        default = settings.default_provider
        if statuses.get(default) and statuses[default].installed:
            return default
        for name, st in statuses.items():
            if st.installed:
                return name
        return default


provider_manager = ProviderManager()
