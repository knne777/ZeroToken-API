"""Core exceptions for ZeroToken API."""


class ZeroTokenException(Exception):
    """Base exception for ZeroToken API."""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ProviderNotFoundError(ZeroTokenException):
    """Requested provider is not recognized."""

    def __init__(self, provider: str):
        super().__init__(
            f"Provider '{provider}' is not supported. Use one of: agy, claude, codex.",
            status_code=400,
        )


class ConversationNotFoundError(ZeroTokenException):
    """Requested conversation ID does not exist."""

    def __init__(self, conversation_id: str):
        super().__init__(
            f"Conversation '{conversation_id}' was not found. To start a new conversation, omit 'conversation_id' or set it to null.",
            status_code=404,
        )


class ProviderUnavailableError(ZeroTokenException):
    """Requested provider CLI is not installed or not authenticated."""

    def __init__(self, provider: str, reason: str):
        super().__init__(
            f"Provider '{provider}' is currently unavailable: {reason}",
            status_code=503,
        )


class ProviderExecutionError(ZeroTokenException):
    """Error during provider turn execution."""

    def __init__(self, provider: str, reason: str, retryable: bool = False):
        super().__init__(
            f"Execution failed for provider '{provider}': {reason}",
            status_code=502,
        )
        self.retryable = retryable
