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


def write_secret(key: str, value: str) -> None:
    """Persist a secret to .env and load it into the running process immediately."""
    from dotenv import find_dotenv, set_key

    env_file = find_dotenv(raise_error_if_not_found=False) or ".env"
    set_key(env_file, key, value, quote_mode="never")
    os.environ[key] = value
