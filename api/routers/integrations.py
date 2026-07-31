from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.dependencies import get_project_context, get_secret_manager
from core.models.context import ProjectContext
from core.secrets import SecretManager
from integrations.base import IntegrationError
from integrations.cms.wordpress import WordPressAdapter
from integrations.google.analytics import AnalyticsAdapter
from integrations.google.search_console import SearchConsoleAdapter
from shared.exceptions import SecretNotFoundError

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
