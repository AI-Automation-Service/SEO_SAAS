from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings


class AppConfig(BaseSettings):
    # OpenAI — optional at app level (per-user BYOK key stored in DB for SaaS usage)
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # Google PageSpeed Insights — server key, never per-user BYOK (§17)
    google_api_key: str = ""

    # Google OAuth — Phase 3 subscriber GSC + GA4 access (§22)
    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""
    google_oauth_redirect_uri: str = ""

    # Shopify Partner App OAuth — Phase 3 (§23)
    shopify_api_key: str = ""
    shopify_api_secret: str = ""
    shopify_redirect_base: str = ""  # e.g. https://app.seo-os.com (no trailing slash)

    log_level: str = "INFO"
    projects_dir: Path = Path("projects")

    # Database — defaults to SQLite; swap to postgresql+psycopg2://... for production
    database_url: str = "sqlite:///./seo_os.db"

    # Auth — required in production; validated at startup via create_tables()
    jwt_secret: str = ""
    encryption_key: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache(maxsize=None)
def load_config() -> AppConfig:
    return AppConfig()
