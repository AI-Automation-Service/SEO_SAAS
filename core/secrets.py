import os

from shared.exceptions import SecretNotFoundError


class SecretManager:
    def get(self, key: str) -> str:
        value = os.environ.get(key)
        if value is None:
            raise SecretNotFoundError(
                f"Secret '{key}' not found in environment. "
                f"Add it to your .env file on the VPS."
            )
        return value

    def get_optional(self, key: str) -> str | None:
        return os.environ.get(key)
