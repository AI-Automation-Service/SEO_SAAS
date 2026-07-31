import json
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.dependencies import get_config, get_project_context, get_secret_manager
from core.config import AppConfig
from core.models.context import ProjectContext
from core.project_writer import update_project_yaml
from core.secrets import SecretManager, write_secret
from integrations.base import IntegrationError
from integrations.cms.wordpress import WordPressAdapter
from integrations.google.analytics import AnalyticsAdapter
from integrations.google.search_console import SearchConsoleAdapter
from shared.exceptions import SecretNotFoundError

_SECRET_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")

router = APIRouter(prefix="/projects/{name}/integrations", tags=["integrations"])


class IntegrationStatusItem(BaseModel):
    name: str
    connected: bool
    error: str | None = None


class IntegrationStatusResponse(BaseModel):
    project: str
    integrations: list[IntegrationStatusItem]


def _resolve_google_creds(
    context: ProjectContext, secrets: SecretManager
) -> tuple[str | None, str | None]:
    """Returns (credentials_file, error). If error is set, credentials_file is None."""
    cfg = context.config.integrations.google
    if not cfg.enabled:
        return None, "Not enabled in project.yaml"
    try:
        return secrets.get(cfg.credentials_env), None
    except SecretNotFoundError as e:
        return None, str(e)


def _check_wordpress(context: ProjectContext, secrets: SecretManager) -> IntegrationStatusItem:
    cfg = context.config.integrations.wordpress
    if not cfg.enabled:
        return IntegrationStatusItem(name="wordpress", connected=False, error="Not enabled in project.yaml")
    try:
        adapter = WordPressAdapter(
            url=cfg.url,
            username=secrets.get(cfg.username_env),
            password=secrets.get(cfg.password_env),
        )
        adapter.test_connection()
        return IntegrationStatusItem(name="wordpress", connected=True)
    except (IntegrationError, SecretNotFoundError) as e:
        return IntegrationStatusItem(name="wordpress", connected=False, error=str(e))


def _check_gsc(context: ProjectContext, secrets: SecretManager) -> IntegrationStatusItem:
    creds_file, err = _resolve_google_creds(context, secrets)
    if err:
        return IntegrationStatusItem(name="google_search_console", connected=False, error=err)
    cfg = context.config.integrations.google
    if not cfg.gsc_site_url:
        return IntegrationStatusItem(
            name="google_search_console", connected=False, error="gsc_site_url not configured"
        )
    try:
        SearchConsoleAdapter(credentials_file=creds_file, site_url=cfg.gsc_site_url).test_connection()
        return IntegrationStatusItem(name="google_search_console", connected=True)
    except IntegrationError as e:
        return IntegrationStatusItem(name="google_search_console", connected=False, error=str(e))


def _check_ga4(context: ProjectContext, secrets: SecretManager) -> IntegrationStatusItem:
    creds_file, err = _resolve_google_creds(context, secrets)
    if err:
        return IntegrationStatusItem(name="google_analytics", connected=False, error=err)
    cfg = context.config.integrations.google
    if not cfg.ga4_property_id:
        return IntegrationStatusItem(
            name="google_analytics", connected=False, error="ga4_property_id not configured"
        )
    try:
        AnalyticsAdapter(credentials_file=creds_file, property_id=cfg.ga4_property_id).test_connection()
        return IntegrationStatusItem(name="google_analytics", connected=True)
    except IntegrationError as e:
        return IntegrationStatusItem(name="google_analytics", connected=False, error=str(e))


_CHECKERS = {
    "wordpress": _check_wordpress,
    "google_search_console": _check_gsc,
    "google_analytics": _check_ga4,
}


@router.get("/status", response_model=IntegrationStatusResponse)
def integration_status(
    context: ProjectContext = Depends(get_project_context),
    secrets: SecretManager = Depends(get_secret_manager),
):
    return IntegrationStatusResponse(
        project=context.name,
        integrations=[checker(context, secrets) for checker in _CHECKERS.values()],
    )


@router.post("/test/{integration}", response_model=IntegrationStatusItem)
def test_integration(
    integration: str,
    context: ProjectContext = Depends(get_project_context),
    secrets: SecretManager = Depends(get_secret_manager),
):
    checker = _CHECKERS.get(integration)
    if checker is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown integration '{integration}'. Valid: {list(_CHECKERS.keys())}",
        )
    return checker(context, secrets)


# ---------------------------------------------------------------------------
# Configuration endpoints — set up a project through the SaaS
# ---------------------------------------------------------------------------

class UpdateIntegrationsConfigRequest(BaseModel):
    wordpress: dict | None = None
    google: dict | None = None
    shopify: dict | None = None


class SetSecretRequest(BaseModel):
    key: str
    value: str


class UploadGoogleCredentialsRequest(BaseModel):
    credentials_json: str


@router.patch("/config")
def update_integrations_config(
    body: UpdateIntegrationsConfigRequest,
    context: ProjectContext = Depends(get_project_context),
    app_config: AppConfig = Depends(get_config),
):
    """Update integration config (URLs, env var names, site URLs) in project.yaml."""
    updates: dict = {"integrations": {}}
    if body.wordpress is not None:
        updates["integrations"]["wordpress"] = body.wordpress
    if body.google is not None:
        updates["integrations"]["google"] = body.google
    if body.shopify is not None:
        updates["integrations"]["shopify"] = body.shopify

    if not updates["integrations"]:
        raise HTTPException(status_code=400, detail="No integration config provided.")

    config_file = app_config.projects_dir / context.name / "config" / "project.yaml"
    update_project_yaml(config_file, updates)
    return {"project": context.name, "updated": list(updates["integrations"].keys())}


@router.post("/secrets")
def set_secret(
    body: SetSecretRequest,
    context: ProjectContext = Depends(get_project_context),
):
    """Write a secret value to .env and load it immediately. Key must be UPPER_SNAKE_CASE."""
    if not _SECRET_KEY_RE.match(body.key):
        raise HTTPException(
            status_code=400,
            detail="Key must be UPPER_SNAKE_CASE (letters, digits, underscores; start with a letter).",
        )
    if not body.value.strip():
        raise HTTPException(status_code=400, detail="Secret value cannot be empty.")

    write_secret(body.key, body.value)
    return {"project": context.name, "key": body.key, "stored": True}


@router.post("/secrets/google-credentials")
def upload_google_credentials(
    body: UploadGoogleCredentialsRequest,
    context: ProjectContext = Depends(get_project_context),
    app_config: AppConfig = Depends(get_config),
):
    """
    Upload Google service account JSON. Writes the file to
    projects/{name}/config/google-credentials.json and sets the
    credentials_env var automatically in .env.
    """
    # Validate JSON
    try:
        parsed = json.loads(body.credentials_json)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    if parsed.get("type") != "service_account":
        raise HTTPException(
            status_code=400,
            detail="Expected a Google service account JSON (type: service_account).",
        )

    # Write credentials file (gitignored)
    creds_file = app_config.projects_dir / context.name / "config" / "google-credentials.json"
    creds_file.write_text(body.credentials_json, encoding="utf-8")

    # Determine or generate the env var name
    env_key = context.config.integrations.google.credentials_env
    if not env_key:
        project_key = context.name.upper().replace("-", "_")
        env_key = f"GOOGLE_{project_key}_CREDENTIALS_FILE"
        # Write it into project.yaml so the config knows which env var to look up
        config_file = app_config.projects_dir / context.name / "config" / "project.yaml"
        update_project_yaml(config_file, {"integrations": {"google": {"credentials_env": env_key}}})

    # Store the file path as the secret value
    write_secret(env_key, str(creds_file.resolve()))

    return {
        "project": context.name,
        "credentials_file": str(creds_file),
        "env_key": env_key,
        "stored": True,
    }
