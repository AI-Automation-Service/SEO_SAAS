"""
Google OAuth flow — subscriber GSC + GA4 access (§17, §22 Phase 3).

Single OAuth flow covers both Search Console and Analytics.
The resulting refresh_token is stored per-subscriber in user_api_keys as
'google_refresh_token'.  Adapters detect this token and use it instead of a
service-account file when the subscriber has connected via OAuth.

Endpoints:
  GET  /api/oauth/google/start       → {url: str}
  POST /api/oauth/google/callback    body {code, redirect_uri?} → {ok: True}
"""

import urllib.parse

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, get_db
from api.routers.identity.api_keys import _save_key
from core.config import load_config
from core.db.models import User

router = APIRouter(prefix="/oauth/google", tags=["oauth"])

_SCOPES = " ".join([
    "https://www.googleapis.com/auth/webmasters.readonly",
    "https://www.googleapis.com/auth/analytics.readonly",
])
_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL = "https://oauth2.googleapis.com/token"


@router.get("/start")
def google_oauth_start(current_user: User = Depends(get_current_user)):
    """Return the Google OAuth URL the subscriber should be redirected to."""
    cfg = load_config()
    if not cfg.google_oauth_client_id:
        raise HTTPException(503, "Google OAuth is not configured on this server.")

    params = {
        "client_id": cfg.google_oauth_client_id,
        "redirect_uri": cfg.google_oauth_redirect_uri,
        "response_type": "code",
        "scope": _SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "state": str(current_user.id),
    }
    url = f"{_AUTH_URL}?{urllib.parse.urlencode(params)}"
    return {"url": url}


class GoogleCallbackRequest(BaseModel):
    code: str
    redirect_uri: str | None = None


@router.post("/callback")
def google_oauth_callback(
    body: GoogleCallbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Exchange the auth code for a refresh token and persist it."""
    cfg = load_config()
    if not cfg.google_oauth_client_id:
        raise HTTPException(503, "Google OAuth is not configured on this server.")

    redirect_uri = body.redirect_uri or cfg.google_oauth_redirect_uri

    try:
        with httpx.Client(timeout=30) as client:
            r = client.post(
                _TOKEN_URL,
                data={
                    "code": body.code,
                    "client_id": cfg.google_oauth_client_id,
                    "client_secret": cfg.google_oauth_client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
        r.raise_for_status()
        token_data = r.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(400, f"Google token exchange failed: {e.response.text[:200]}")
    except Exception as e:
        raise HTTPException(502, f"Could not reach Google: {e}")

    refresh_token = token_data.get("refresh_token")
    if not refresh_token:
        raise HTTPException(400, "Google did not return a refresh_token — ensure 'access_type=offline' and 'prompt=consent' are set.")

    _save_key(db, current_user.id, "google_refresh_token", refresh_token)
    return {"ok": True}
