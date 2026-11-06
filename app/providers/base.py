"""Base abstract provider definition for ZeroToken API."""

from abc import ABC, abstractmethod
from app.models.schemas import ChatResponse, FileAttachment, ProviderStatus


class BaseProvider(ABC):
    """Abstract base class for all CLI subscription providers."""

    name: str
    label: str

    @abstractmethod
    async def preflight(self) -> ProviderStatus:
        """Check if CLI is installed, accessible, and authenticated."""
        pass

    @abstractmethod
    async def run(
        self,
        prompt: str,
        conversation_id: str | None = None,
        model: str | None = None,
        effort: str | None = None,
        attachments: list[FileAttachment] | None = None,
        timeout: float = 300.0,
    ) -> ChatResponse:
        """Run a single or multi-turn prompt and return structured ChatResponse."""
        pass

    @abstractmethod
    async def list_models(self) -> list[str]:
        """List available models supported by this provider."""
        pass
