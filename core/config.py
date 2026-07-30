from pathlib import Path
from pydantic_settings import BaseSettings


class AppConfig(BaseSettings):
    openai_api_key: str
    openai_model: str = "gpt-4o"
    log_level: str = "INFO"
    projects_dir: Path = Path("projects")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


def load_config() -> AppConfig:
    return AppConfig()
