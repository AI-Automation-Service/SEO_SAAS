from dataclasses import dataclass

from shared.exceptions import IntegrationError


class IntegrationAuthError(IntegrationError):
    """Credentials rejected by the remote service."""


class IntegrationConnectionError(IntegrationError):
    """Could not reach the remote endpoint."""


class IntegrationRateLimitError(IntegrationError):
    def __init__(self, message: str, retry_after: int | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class IntegrationConfigError(IntegrationError):
    """Required config (URL, credentials) is missing or incomplete."""


@dataclass
class ConnectionStatus:
    name: str
    connected: bool
    error: str | None = None
