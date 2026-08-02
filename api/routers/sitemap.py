import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, get_db, get_project_context
from core.db.models import Keyword, SitePage, User
from core.models.context import ProjectContext
from core.sitemap import fetch_sitemap_urls

router = APIRouter(prefix="/projects/{name}/sitemap", tags=["sitemap"])


class SitemapSummary(BaseModel):
    total: int
    last_synced: Optional[datetime] = None


class SitePageOut(BaseModel):
    id: int
    url: str
    slug: str
    page_type: str
    synced_at: datetime


def _slug_to_keyword(slug: str) -> str:
    """Convert URL slug to keyword text: blog/hotel-booking-cairo → hotel booking cairo"""
    last_part = slug.split("/")[-1]
    last_part = re.sub(r"\.\w+$", "", last_part)  # strip file extensions
    return re.sub(r"[-_]+", " ", last_part).strip()


def _upsert_keyword_from_page(
    db: Session,
    user_id: int,
    project_name: str,
    url: str,
    slug: str,
    page_type: str,
) -> None:
    """Create or update a Keyword row derived from a sitemap URL."""
    kw_text = _slug_to_keyword(slug)
    if not kw_text or len(kw_text) < 3:
        return

    existing = (
        db.query(Keyword)
        .filter(
            Keyword.user_id == user_id,
            Keyword.project_name == project_name,
            Keyword.keyword == kw_text,
        )
        .first()
    )

    if existing:
        if not existing.existing_url:
            existing.existing_url = url
        existing.page_type = page_type
    else:
        intent = "informational"
        db.add(Keyword(
            user_id=user_id,
            project_name=project_name,
            keyword=kw_text,
            keyword_type="question" if kw_text.split()[0].lower() in {
                "how", "what", "why", "when", "where", "who", "which",
                "can", "does", "is", "are", "will", "should", "do",
            } else "standard",
            intent=intent,
            funnel_stage="tofu",
            status="covered",
            action="none",
            source="sitemap",
            existing_url=url,
            page_type=page_type,
        ))


def sync_sitemap_pages(website: str, user_id: int, project_name: str, db: Session) -> int:
    """Fetch sitemap, upsert SitePages, and reverse-extract keywords. Returns page count."""
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
            existing.page_type = page["page_type"]
            existing.synced_at = now
        else:
            db.add(SitePage(
                user_id=user_id,
                project_name=project_name,
                url=page["url"],
                slug=page["slug"],
                page_type=page["page_type"],
                synced_at=now,
            ))

        _upsert_keyword_from_page(db, user_id, project_name, page["url"], page["slug"], page["page_type"])

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


@router.get("/pages", response_model=list[SitePageOut])
def list_pages(
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(SitePage)
        .filter(
            SitePage.user_id == current_user.id,
            SitePage.project_name == context.name,
        )
        .order_by(SitePage.page_type, SitePage.slug)
        .all()
    )


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
