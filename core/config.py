from pathlib import Path
from pydantic_settings import BaseSettings


class AppConfig(BaseSettings):
    # OpenAI — optional at app level (per-user BYOK key stored in DB for SaaS usage)
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    log_level: str = "INFO"
    projects_dir: Path = Path("projects")

    # Database — defaults to SQLite; swap to postgresql+psycopg2://... for production
    database_url: str = "sqlite:///./seo_os.db"

    # Auth — required in production; validated at startup via create_tables()
    jwt_secret: str = ""
    encryption_key: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


def load_config() -> AppConfig:
    return AppConfig()
