from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, get_db, get_project_context
from core.db.models import SitePage, User
from core.models.context import ProjectContext
from core.sitemap import fetch_sitemap_urls

router = APIRouter(prefix="/projects/{name}/sitemap", tags=["sitemap"])


class SitemapSummary(BaseModel):
    total: int
    last_synced: Optional[datetime] = None


def sync_sitemap_pages(website: str, user_id: int, project_name: str, db: Session) -> int:
    """Fetch sitemap and upsert pages. Returns count of pages found."""
    pages = fetch_sitemap_urls(website)
    now = datetime.utcnow()
    for page in pages:
        existing = (
            db.query(SitePage)
            .filter(
                SitePage.user_id == user_id,
                SitePage.project_name == project_name,
                SitePage.url == page["url"],
            )
            .first()
        )
        if existing:
            existing.slug = page["slug"]
            existing.synced_at = now
        else:
            db.add(SitePage(
                user_id=user_id,
                project_name=project_name,
                url=page["url"],
                slug=page["slug"],
                synced_at=now,
            ))
    db.commit()
    return len(pages)


@router.post("/sync")
def sync_sitemap(
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    website = str(context.config.website)
    count = sync_sitemap_pages(website, current_user.id, context.name, db)
    if count == 0:
        raise HTTPException(
            404,
            "No sitemap found or sitemap is empty. "
            "Make sure your site has an XML sitemap at /sitemap.xml or /sitemap_index.xml.",
        )
    return {"synced": count, "message": f"Found {count} existing pages in sitemap."}


@router.get("/summary", response_model=SitemapSummary)
def sitemap_summary(
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(SitePage)
        .filter(
            SitePage.user_id == current_user.id,
            SitePage.project_name == context.name,
        )
        .all()
    )
    last_synced = max((r.synced_at for r in rows), default=None) if rows else None
    return SitemapSummary(total=len(rows), last_synced=last_synced)
