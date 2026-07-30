from abc import ABC, abstractmethod


class BaseIntegration(ABC):
    """Common interface all integrations must implement."""

    @abstractmethod
    def validate_credentials(self) -> bool:
        """Verify credentials are valid before any operation."""

    @abstractmethod
    def health_check(self) -> dict:
        """Return a status dict: {ok: bool, message: str}."""
