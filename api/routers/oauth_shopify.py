"""
Shopify Partner App OAuth flow (§17, §23 Phase 3).

Flow:
  1. GET  /api/projects/{name}/oauth/shopify/start?shop=mystore.myshopify.com
     → {url: str}  (subscriber redirected there)

  2. GET  /api/projects/{name}/oauth/shopify/callback?shop=&code=&hmac=&state=
     → verifies HMAC, exchanges code for access_token, stores in project secrets,
       then redirects subscriber back to the integrations tab.

The access_token is stored as a project-level secret (env var per project) so
multi-project accounts each get their own Shopify token — same as the current
manual token approach, but obtained via OAuth rather than manual copy/paste.
"""

import hashlib
import hmac as _hmac
import urllib.parse
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, get_db, get_project_context
from core.config import load_config
from core.db.models import User
from core.models.context import ProjectContext
from core.project_writer import update_project_yaml
from core.secrets import write_secret

router = APIRouter(prefix="/projects/{name}/oauth/shopify", tags=["oauth"])

_REQUIRED_SCOPES = "read_content,write_content,read_products,write_products,read_metafields,write_metafields"


@router.get("/start")
def shopify_oauth_start(
    shop: str = Query(..., description="mystore.myshopify.com"),
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
):
    """Return the Shopify OAuth URL for the subscriber's store."""
    cfg = load_config()
    if not cfg.shopify_api_key:
        raise HTTPException(503, "Shopify Partner App OAuth is not configured on this server.")

    shop = shop.strip().lower()
    if not shop.endswith(".myshopify.com"):
        shop = f"{shop}.myshopify.com"

    state = f"{current_user.id}:{context.name}"
    redirect_uri = _callback_url(cfg, context.name)

    params = {
        "client_id": cfg.shopify_api_key,
        "scope": _REQUIRED_SCOPES,
        "redirect_uri": redirect_uri,
        "state": state,
    }
    url = f"https://{shop}/admin/oauth/authorize?{urllib.parse.urlencode(params)}"
    return {"url": url}


@router.get("/callback")
def shopify_oauth_callback(
    shop: str = Query(...),
    code: str = Query(...),
    hmac: str = Query(...),
    state: str = Query(...),
    timestamp: str = Query(...),
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Verify HMAC, exchange code for access_token, store in project secrets."""
    cfg = load_config()
    if not cfg.shopify_api_key:
        raise HTTPException(503, "Shopify Partner App OAuth is not configured on this server.")

    # Verify HMAC — Shopify requires ALL params except hmac itself, sorted by key
    import urllib.parse as up
    all_params = {"code": code, "shop": shop, "state": state, "timestamp": timestamp}
    raw_query = "&".join(f"{k}={v}" for k, v in sorted(all_params.items()))
    expected = _hmac.new(
        cfg.shopify_api_secret.encode(), raw_query.encode(), hashlib.sha256
    ).hexdigest()
    if not _hmac.compare_digest(expected, hmac):
        raise HTTPException(400, "Invalid HMAC — request tampered or not from Shopify.")

    # Exchange code for permanent access token
    try:
        with httpx.Client(timeout=30) as client:
            r = client.post(
                f"https://{shop}/admin/oauth/access_token",
                json={
                    "client_id": cfg.shopify_api_key,
                    "client_secret": cfg.shopify_api_secret,
                    "code": code,
                },
            )
        r.raise_for_status()
        access_token = r.json()["access_token"]
    except (httpx.HTTPStatusError, KeyError) as e:
        raise HTTPException(400, f"Shopify token exchange failed: {e}")
    except Exception as e:
        raise HTTPException(502, f"Could not reach Shopify: {e}")

    # Store as project secret (same env-var pattern as manual token setup)
    env_key = context.name.upper().replace("-", "_")
    token_env = f"SHOPIFY_{env_key}_TOKEN"
    write_secret(token_env, access_token)

    config_file = context.project_dir / "config" / "project.yaml"
    update_project_yaml(config_file, {
        "integrations": {
            "shopify": {
                "enabled": True,
                "store_url": f"https://{shop}",
                "token_env": token_env,
            }
        }
    })

    return RedirectResponse(url="/#integrations?connected=shopify", status_code=302)


def _callback_url(cfg, project_name: str) -> str:
    """Build the OAuth callback URL — uses shopify_redirect_base if set, else relative path."""
    base = cfg.shopify_redirect_base
    if base:
        return f"{base.rstrip('/')}/api/projects/{project_name}/oauth/shopify/callback"
    return f"/api/projects/{project_name}/oauth/shopify/callback"
