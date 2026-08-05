import json
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, get_db, get_project_context, get_secret_manager
from core.config import load_config
from core.db.models import User
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


def _check_wordpress(
    context: ProjectContext,
    secrets: SecretManager,
    *,
    user_id: int | None = None,
    db: Session | None = None,
) -> IntegrationStatusItem:
    cfg = context.config.integrations.wordpress
    if not cfg.enabled:
        return IntegrationStatusItem(name="wordpress", connected=False, error="Not enabled in project.yaml")
    try:
        if cfg.token_env:
            adapter = WordPressAdapter(url=cfg.url, site_token=secrets.get(cfg.token_env))
        else:
            adapter = WordPressAdapter(
                url=cfg.url,
                username=secrets.get(cfg.username_env),
                password=secrets.get(cfg.password_env),
            )
        adapter.test_connection()
        return IntegrationStatusItem(name="wordpress", connected=True)
    except (IntegrationError, SecretNotFoundError) as e:
        return IntegrationStatusItem(name="wordpress", connected=False, error=str(e))


def _get_oauth_refresh_token(user_id: int, db: Session) -> str | None:
    """Return the subscriber's Google OAuth refresh token, or None if not stored."""
    try:
        from api.routers.api_keys import get_user_secret
        return get_user_secret("google_refresh_token", user_id, db)
    except HTTPException:
        return None


def _build_google_status(
    name: str,
    prop_value: str,
    prop_label: str,
    AdapterClass,
    context: ProjectContext,
    secrets: SecretManager,
    *,
    user_id: int | None = None,
    db: Session | None = None,
) -> IntegrationStatusItem:
    if not prop_value:
        return IntegrationStatusItem(name=name, connected=False, error=f"{prop_label} not configured")
    if user_id and db:
        refresh_token = _get_oauth_refresh_token(user_id, db)
        if refresh_token:
            try:
                app_cfg = load_config()
                AdapterClass(
                    prop_value,
                    refresh_token=refresh_token,
                    client_id=app_cfg.google_oauth_client_id,
                    client_secret=app_cfg.google_oauth_client_secret,
                ).test_connection()
                return IntegrationStatusItem(name=name, connected=True)
            except IntegrationError as e:
                return IntegrationStatusItem(name=name, connected=False, error=str(e))
    creds_file, err = _resolve_google_creds(context, secrets)
    if err:
        return IntegrationStatusItem(name=name, connected=False, error=err)
    try:
        AdapterClass(prop_value, credentials_file=creds_file).test_connection()
        return IntegrationStatusItem(name=name, connected=True)
    except IntegrationError as e:
        return IntegrationStatusItem(name=name, connected=False, error=str(e))


def _check_gsc(
    context: ProjectContext,
    secrets: SecretManager,
    *,
    user_id: int | None = None,
    db: Session | None = None,
) -> IntegrationStatusItem:
    cfg = context.config.integrations.google
    return _build_google_status(
        "google_search_console",
        cfg.gsc_site_url if cfg else "",
        "gsc_site_url",
        SearchConsoleAdapter,
        context,
        secrets,
        user_id=user_id,
        db=db,
    )


def _check_ga4(
    context: ProjectContext,
    secrets: SecretManager,
    *,
    user_id: int | None = None,
    db: Session | None = None,
) -> IntegrationStatusItem:
    cfg = context.config.integrations.google
    return _build_google_status(
        "google_analytics",
        cfg.ga4_property_id if cfg else "",
        "ga4_property_id",
        AnalyticsAdapter,
        context,
        secrets,
        user_id=user_id,
        db=db,
    )


_CHECKERS = {
    "wordpress": _check_wordpress,
    "google_search_console": _check_gsc,
    "google_analytics": _check_ga4,
}


@router.get("/status", response_model=IntegrationStatusResponse)
def integration_status(
    context: ProjectContext = Depends(get_project_context),
    secrets: SecretManager = Depends(get_secret_manager),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return IntegrationStatusResponse(
        project=context.name,
        integrations=[
            checker(context, secrets, user_id=current_user.id, db=db)
            for checker in _CHECKERS.values()
        ],
    )


@router.post("/test/{integration}", response_model=IntegrationStatusItem)
def test_integration(
    integration: str,
    context: ProjectContext = Depends(get_project_context),
    secrets: SecretManager = Depends(get_secret_manager),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    checker = _CHECKERS.get(integration)
    if checker is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown integration '{integration}'. Valid: {list(_CHECKERS.keys())}",
        )
    return checker(context, secrets, user_id=current_user.id, db=db)


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

    config_file = context.project_dir / "config" / "project.yaml"

    # Sync root `website` field from WordPress URL so Overview shows the real site
    if body.wordpress and body.wordpress.get("url"):
        updates["website"] = body.wordpress["url"]

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
):
    """
    Upload Google service account JSON. Writes the file to
    projects/{user_id}/{name}/config/google-credentials.json and sets the
    credentials_env var automatically in .env.
    """
    try:
        parsed = json.loads(body.credentials_json)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    if parsed.get("type") != "service_account":
        raise HTTPException(
            status_code=400,
            detail="Expected a Google service account JSON (type: service_account).",
        )

    creds_file = context.project_dir / "config" / "google-credentials.json"
    creds_file.write_text(body.credentials_json, encoding="utf-8")

    env_key = context.config.integrations.google.credentials_env
    if not env_key:
        project_key = context.name.upper().replace("-", "_")
        env_key = f"GOOGLE_{project_key}_CREDENTIALS_FILE"
        config_file = context.project_dir / "config" / "project.yaml"
        update_project_yaml(config_file, {"integrations": {"google": {"credentials_env": env_key}}})

    write_secret(env_key, str(creds_file.resolve()))

    return {
        "project": context.name,
        "credentials_file": str(creds_file),
        "env_key": env_key,
        "stored": True,
    }
