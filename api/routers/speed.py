import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, get_db, get_project_context
from api.routers.api_keys import get_user_secret
from core.db.models import User
from core.models.context import ProjectContext
from core.pagespeed import fetch_pagespeed

router = APIRouter(prefix="/projects/{name}/speed", tags=["speed"])


@router.get("")
def get_speed(
    strategy: str = Query("mobile", pattern="^(mobile|desktop)$"),
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    url = str(context.config.website)

    # Use user's Google API key if stored; fall back to unauthenticated (rate-limited)
    try:
        api_key = get_user_secret("google_api_key", current_user.id, db)
    except HTTPException:
        api_key = None

    try:
        return fetch_pagespeed(url, strategy=strategy, api_key=api_key)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"PageSpeed API returned {e.response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"PageSpeed API error: {e}")
