import csv
import io
import json
import re
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from agents.base import SkillAgent
from api.dependencies import get_current_user, get_db, get_project_context, get_secret_manager
from api.routers.api_keys import get_user_secret
from core.db.models import Keyword, ProjectKnowledge, SitePage, User
from core.models.context import ProjectContext
from core.secrets import SecretManager
from integrations.base import IntegrationError
from integrations.google.search_console import SearchConsoleAdapter
from shared.exceptions import SecretNotFoundError

router = APIRouter(prefix="/projects/{name}/keywords", tags=["keywords"])


# ── Classification helpers ───────────────────────────────────────────────────

_QUESTION_WORDS = {
    "how", "what", "why", "when", "where", "who", "which",
    "can", "does", "is", "are", "will", "should", "do",
}
_TRANSACTIONAL = {
    "buy", "price", "cost", "cheap", "discount", "shop", "order",
    "purchase", "deal", "promo", "quote", "hire",
}
_COMMERCIAL = {
    "best", "top", "review", "compare", "vs", "versus",
    "alternative", "alternatives", "recommend", "recommended", "vs.",
}


def _keyword_type(keyword: str) -> str:
    first = keyword.lower().strip().split()
    return "question" if first and first[0] in _QUESTION_WORDS else "standard"


def _intent(keyword: str) -> str:
    words = set(keyword.lower().split())
    if words & _TRANSACTIONAL:
        return "transactional"
    if words & _COMMERCIAL:
        return "commercial"
    return "informational"


def _funnel(intent: str) -> str:
    return {"transactional": "bofu", "commercial": "mofu"}.get(intent, "tofu")


def _status(clicks: Optional[int], impressions: Optional[int], position: Optional[float]) -> str:
    if not impressions:
        return "gap"
    if position and position <= 3 and clicks:
        return "covered"
    if position and position <= 10 and clicks:
        return "quick_win"
    return "opportunity"


def _snippet_opp(ktype: str, position: Optional[float], impressions: Optional[int]) -> bool:
    if ktype != "question":
        return False
    return bool(position and position <= 20) or bool(impressions and impressions > 100)


# ── Schemas ──────────────────────────────────────────────────────────────────

class KeywordOut(BaseModel):
    id: int
    keyword: str
    keyword_type: str
    cluster: Optional[str] = None
    is_hub: bool
    intent: Optional[str] = None
    funnel_stage: Optional[str] = None
    status: str
    action: str
    volume: Optional[int] = None
    competition: Optional[float] = None
    clicks: Optional[int] = None
    impressions: Optional[int] = None
    position: Optional[float] = None
    ctr: Optional[float] = None
    existing_url: Optional[str] = None
    suggested_url: Optional[str] = None
    snippet_opportunity: bool
    competitor_gap: bool
    source: str
    page_type: Optional[str] = None
    updated_at: datetime

    class Config:
        from_attributes = True


class KeywordUpdate(BaseModel):
    cluster: Optional[str] = None
    is_hub: Optional[bool] = None
    intent: Optional[str] = None
    funnel_stage: Optional[str] = None
    status: Optional[str] = None
    action: Optional[str] = None
    keyword_type: Optional[str] = None
    suggested_url: Optional[str] = None
    competitor_gap: Optional[bool] = None


class KeywordSummary(BaseModel):
    total: int
    covered: int
    quick_wins: int
    gaps: int
    opportunities: int
    clusters: int
    unclustered: int


# ── Query helpers ─────────────────────────────────────────────────────────────

def _project_keywords(db: Session, user_id: int, project_name: str):
    return db.query(Keyword).filter(
        Keyword.user_id == user_id,
        Keyword.project_name == project_name,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/summary", response_model=KeywordSummary)
def keyword_summary(
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = _project_keywords(db, current_user.id, context.name).all()
    clusters = {r.cluster for r in rows if r.cluster}
    return KeywordSummary(
        total=len(rows),
        covered=sum(1 for r in rows if r.status == "covered"),
        quick_wins=sum(1 for r in rows if r.status == "quick_win"),
        gaps=sum(1 for r in rows if r.status == "gap"),
        opportunities=sum(1 for r in rows if r.status == "opportunity"),
        clusters=len(clusters),
        unclustered=sum(1 for r in rows if not r.cluster),
    )


@router.get("", response_model=list[KeywordOut])
def list_keywords(
    status: Optional[str] = Query(None),
    cluster: Optional[str] = Query(None),
    keyword_type: Optional[str] = Query(None),
    funnel: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort: str = Query("impressions"),
    order: str = Query("desc"),
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = _project_keywords(db, current_user.id, context.name)

    if status:
        q = q.filter(Keyword.status == status)
    if cluster:
        q = q.filter(Keyword.cluster == cluster)
    if keyword_type:
        q = q.filter(Keyword.keyword_type == keyword_type)
    if funnel:
        q = q.filter(Keyword.funnel_stage == funnel)
    if search:
        q = q.filter(Keyword.keyword.ilike(f"%{search}%"))

    _sort_cols = {
        "keyword": Keyword.keyword,
        "clicks": Keyword.clicks,
        "impressions": Keyword.impressions,
        "position": Keyword.position,
        "volume": Keyword.volume,
        "status": Keyword.status,
        "cluster": Keyword.cluster,
        "ctr": Keyword.ctr,
    }
    col = _sort_cols.get(sort, Keyword.impressions)
    q = q.order_by(col.asc().nullslast() if order == "asc" else col.desc().nullsfirst())

    return q.limit(1000).all()


@router.post("/sync")
def sync_from_gsc(
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    secrets: SecretManager = Depends(get_secret_manager),
    db: Session = Depends(get_db),
):
    """Pull keyword + page data from GSC (90 days) and upsert into keywords table."""
    cfg = context.config.integrations.google
    if not cfg.enabled:
        raise HTTPException(400, "Google integration is not enabled for this project.")
    if not cfg.gsc_site_url:
        raise HTTPException(400, "GSC site URL is not configured.")
    if not cfg.credentials_env:
        raise HTTPException(400, "Google credentials not uploaded. Complete the Google setup in the Integrations tab.")
    try:
        creds_file = secrets.get(cfg.credentials_env)
    except SecretNotFoundError as e:
        raise HTTPException(400, str(e))

    try:
        adapter = SearchConsoleAdapter(credentials_file=creds_file, site_url=cfg.gsc_site_url)
        rows = adapter.get_keyword_pages(days=90, row_limit=500)
    except IntegrationError as e:
        raise HTTPException(502, f"GSC error: {e}")

    if not rows:
        return {
            "synced": 0,
            "message": "No data returned from GSC. "
                       "The site may be new or have no queries in the last 90 days.",
        }

    # When a keyword appears on multiple pages, keep the page with the most clicks
    best: dict[str, dict] = {}
    for row in rows:
        kw = row["query"].strip().lower()
        if kw not in best or row["clicks"] > best[kw]["clicks"]:
            best[kw] = row

    upserted = 0
    for kw, data in best.items():
        ktype = _keyword_type(kw)
        intent_val = _intent(kw)
        new_status = _status(data["clicks"], data["impressions"], data["position"])
        snip = _snippet_opp(ktype, data["position"], data["impressions"])

        existing = (
            db.query(Keyword)
            .filter(
                Keyword.user_id == current_user.id,
                Keyword.project_name == context.name,
                Keyword.keyword == kw,
            )
            .first()
        )
        if existing:
            existing.clicks = data["clicks"]
            existing.impressions = data["impressions"]
            existing.position = data["position"]
            existing.ctr = data["ctr"]
            existing.existing_url = data.get("page")
            existing.status = new_status
            existing.snippet_opportunity = snip
            existing.updated_at = datetime.utcnow()
            if existing.source == "planner":
                existing.source = "both"
            elif existing.source == "manual":
                existing.source = "gsc"
        else:
            db.add(Keyword(
                user_id=current_user.id,
                project_name=context.name,
                keyword=kw,
                keyword_type=ktype,
                intent=intent_val,
                funnel_stage=_funnel(intent_val),
                status=new_status,
                clicks=data["clicks"],
                impressions=data["impressions"],
                position=data["position"],
                ctr=data["ctr"],
                existing_url=data.get("page"),
                snippet_opportunity=snip,
                source="gsc",
            ))
        upserted += 1

    db.commit()
    return {"synced": upserted, "message": f"Synced {upserted} keywords from GSC."}


@router.post("/upload")
async def upload_planner_csv(
    file: UploadFile = File(...),
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Parse a Google Keyword Planner .csv export and upsert keywords."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "File must be a .csv exported from Google Keyword Planner.")

    content = await file.read()
    try:
        text = content.decode("utf-8-sig")  # strip UTF-8 BOM if present
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    headers = [h.strip() for h in (reader.fieldnames or [])]

    kw_col = next((h for h in headers if h.lower() == "keyword"), None)
    if not kw_col:
        raise HTTPException(
            400,
            f"Could not find 'Keyword' column in CSV. Columns found: {', '.join(headers)}",
        )

    vol_col = next((h for h in headers if "avg" in h.lower() and "search" in h.lower()), None)
    comp_idx_col = next(
        (h for h in headers if "competition (indexed" in h.lower()), None
    )

    upserted = 0
    for row in reader:
        kw = row.get(kw_col, "").strip().lower()
        if not kw:
            continue

        volume: Optional[int] = None
        if vol_col:
            raw = row.get(vol_col, "").strip().replace(",", "").replace('"', "")
            try:
                volume = int(float(raw))
            except (ValueError, TypeError):
                pass

        competition: Optional[float] = None
        if comp_idx_col:
            raw = row.get(comp_idx_col, "").strip()
            try:
                # Planner exports 0–100; store as 0.0–1.0
                competition = round(float(raw) / 100, 2)
            except (ValueError, TypeError):
                pass

        ktype = _keyword_type(kw)
        intent_val = _intent(kw)

        existing = (
            db.query(Keyword)
            .filter(
                Keyword.user_id == current_user.id,
                Keyword.project_name == context.name,
                Keyword.keyword == kw,
            )
            .first()
        )
        if existing:
            if volume is not None:
                existing.volume = volume
            if competition is not None:
                existing.competition = competition
            existing.source = "both" if existing.source == "gsc" else "planner"
            existing.updated_at = datetime.utcnow()
        else:
            db.add(Keyword(
                user_id=current_user.id,
                project_name=context.name,
                keyword=kw,
                keyword_type=ktype,
                intent=intent_val,
                funnel_stage=_funnel(intent_val),
                status="gap",
                volume=volume,
                competition=competition,
                source="planner",
            ))
        upserted += 1

    db.commit()
    return {"imported": upserted, "message": f"Imported {upserted} keywords from Keyword Planner."}


def _match_sitemap(rows: list, db: Session, user_id: int, project_name: str) -> None:
    """For keywords without existing_url, try to match against sitemap page slugs."""
    unmatched = [r for r in rows if not r.existing_url]
    if not unmatched:
        return
    pages = db.query(SitePage).filter(
        SitePage.user_id == user_id,
        SitePage.project_name == project_name,
    ).all()
    if not pages:
        return
    for row in unmatched:
        kw_slug = re.sub(r"[^a-z0-9\s]", "", row.keyword.lower())
        kw_slug = re.sub(r"\s+", "-", kw_slug.strip())
        if not kw_slug:
            continue
        for page in pages:
            if kw_slug in page.slug:
                row.existing_url = page.url
                break


def _format_keyword_line(row) -> str:
    data = []
    if row.clicks is not None:
        data.append(f"clicks:{row.clicks}")
    if row.impressions is not None:
        data.append(f"impr:{row.impressions:,}")
    if row.position is not None:
        data.append(f"pos:{row.position:.1f}")
    if row.ctr is not None:
        data.append(f"ctr:{row.ctr * 100:.1f}%")
    if row.volume is not None:
        data.append(f"vol:{row.volume:,}")
    data.append(f"status:{row.status}")
    if row.existing_url:
        path = urlparse(row.existing_url).path or row.existing_url
        data.append(f"page:{path}")
    return f"- {row.keyword} [{', '.join(data)}]"


_CLUSTER_USER_MSG = """\
Cluster the following keywords into semantic topic groups for content planning.

Each keyword shows available performance signals:
- clicks/impr: real Google Search Console data (last 90 days)
- pos: average Google ranking position (1=top, lower is better)
- ctr: click-through rate from Google search results
- vol: estimated monthly search volume
- status: quick_win/opportunity/covered/gap
- page: URL on this site that currently ranks for this keyword

Keywords:
{keywords}

Return ONLY a valid JSON object in this exact format — no extra text, no markdown:
{{"keywords": [
  {{
    "keyword": "<exact keyword text from input, no signals>",
    "cluster": "<short cluster name 2-4 words, e.g. Hotel Booking>",
    "intent": "<informational|commercial|navigational|transactional>",
    "funnel_stage": "<tofu|mofu|bofu>",
    "suggested_url": "<clean URL slug e.g. /blog/hotel-booking-cairo>"
  }}
]}}

Rules:
- Keywords with the SAME page URL must go in the SAME cluster — they already share a page
- Keywords with a UNIQUE page URL that no other keyword shares get their own cluster
- Group remaining keywords by semantic topic
- Return every keyword from the input — do not skip any
- The "keyword" field must be the exact keyword text only, no signals"""

_BATCH_SIZE = 150


@router.post("/cluster")
def run_cluster_agent(
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cluster keywords using the seo-cluster skill agent (GPT-4o-mini, JSON mode)."""
    openai_key = get_user_secret("openai", current_user.id, db)

    rows = _project_keywords(db, current_user.id, context.name).all()
    if not rows:
        raise HTTPException(400, "No keywords found. Sync from GSC or upload a CSV first.")

    try:
        agent = SkillAgent("seo-cluster", openai_key, model="gpt-4o-mini")
    except FileNotFoundError as e:
        raise HTTPException(500, str(e))

    # Build knowledge context once for all batches
    kb = db.query(ProjectKnowledge).filter(
        ProjectKnowledge.user_id == current_user.id,
        ProjectKnowledge.project_name == context.name,
    ).first()
    kb_prefix = ""
    if kb:
        parts = []
        if kb.about: parts.append(f"Business: {kb.about.strip()[:300]}")
        if kb.products_services: parts.append(f"Products/Services: {kb.products_services.strip()[:200]}")
        if kb.target_audience: parts.append(f"Target audience: {kb.target_audience.strip()[:200]}")
        if parts:
            kb_prefix = "Context:\n" + "\n".join(parts) + "\n\n"

    all_results: list[dict] = []

    for i in range(0, len(rows), _BATCH_SIZE):
        batch_rows = rows[i : i + _BATCH_SIZE]
        user_msg = kb_prefix + _CLUSTER_USER_MSG.format(
            keywords="\n".join(_format_keyword_line(r) for r in batch_rows)
        )

        try:
            raw = agent.run(user_msg, timeout=90, json_mode=True)
        except Exception as e:
            raise HTTPException(502, f"OpenAI error: {e}")

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as e:
            raise HTTPException(502, f"OpenAI returned invalid JSON: {e}. Response: {raw[:300]}")

        if isinstance(parsed, list):
            items = parsed
        elif isinstance(parsed, dict):
            items = next((v for v in parsed.values() if isinstance(v, list)), [])
        else:
            items = []

        all_results.extend(items)

    results_map = {r["keyword"].lower(): r for r in all_results if isinstance(r, dict) and "keyword" in r}

    updated = 0
    for row in rows:
        data = results_map.get(row.keyword.lower())
        if not data:
            continue
        row.cluster = data.get("cluster") or row.cluster
        row.is_hub = False
        row.intent = data.get("intent") or row.intent
        row.funnel_stage = data.get("funnel_stage") or row.funnel_stage
        row.suggested_url = data.get("suggested_url") or row.suggested_url
        row.updated_at = datetime.utcnow()
        updated += 1

    _match_sitemap(rows, db, current_user.id, context.name)
    db.commit()

    # Hub selection on fresh rows to avoid stale ORM session state
    # Reset all hubs, then pick highest impressions per cluster
    _project_keywords(db, current_user.id, context.name).update({"is_hub": False})
    fresh = _project_keywords(db, current_user.id, context.name).all()
    cluster_map: dict[str, list] = {}
    for r in fresh:
        if r.cluster:
            cluster_map.setdefault(r.cluster, []).append(r)
    for cluster_rows in cluster_map.values():
        best = max(
            cluster_rows,
            key=lambda r: (r.impressions or 0, r.volume or 0, -len(r.keyword)),
        )
        best.is_hub = True
    db.commit()
    cluster_count = len({r.cluster for r in rows if r.cluster})
    return {
        "clustered": updated,
        "clusters": cluster_count,
        "message": f"Clustered {updated} keywords into {cluster_count} groups.",
    }


@router.patch("/{keyword_id}", response_model=KeywordOut)
def update_keyword(
    keyword_id: int,
    body: KeywordUpdate,
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = (
        db.query(Keyword)
        .filter(
            Keyword.id == keyword_id,
            Keyword.user_id == current_user.id,
            Keyword.project_name == context.name,
        )
        .first()
    )
    if not row:
        raise HTTPException(404, "Keyword not found.")

    for field, val in body.model_dump(exclude_none=True).items():
        setattr(row, field, val)
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row


@router.delete("")
def reset_keywords(
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete all keywords for this project so the user can re-sync or re-upload."""
    count = (
        db.query(Keyword)
        .filter(
            Keyword.user_id == current_user.id,
            Keyword.project_name == context.name,
        )
        .delete()
    )
    db.commit()
    return {"deleted": count, "message": f"Cleared {count} keywords."}


@router.delete("/{keyword_id}")
def delete_keyword(
    keyword_id: int,
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    deleted = (
        db.query(Keyword)
        .filter(
            Keyword.id == keyword_id,
            Keyword.user_id == current_user.id,
            Keyword.project_name == context.name,
        )
        .delete()
    )
    db.commit()
    if not deleted:
        raise HTTPException(404, "Keyword not found.")
    return {"deleted": keyword_id}
