import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from agents.base import SkillAgent
from api.dependencies import get_current_user, get_db, get_project_context
from api.routers.api_keys import get_user_secret
from core.db.models import Keyword, PageChange, User
from core.models.context import ProjectContext
from integrations.cms.wordpress import WordPressAdapter
from integrations.base import IntegrationError
from shared.exceptions import SecretNotFoundError

router = APIRouter(prefix="/projects/{name}/improve", tags=["improve"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_wp_adapter(context: ProjectContext, user_id: int, db: Session) -> WordPressAdapter:
    wp_cfg = context.config.integrations.wordpress
    if not wp_cfg or not wp_cfg.get("enabled"):
        raise HTTPException(400, "WordPress integration is not connected. Go to Integrations tab first.")
    try:
        wp_url = wp_cfg.get("url") or ""
        wp_user = wp_cfg.get("username") or ""
        wp_pass = ""
        try:
            wp_pass = get_user_secret("wp_app_password", user_id, db)
        except SecretNotFoundError:
            wp_pass = wp_cfg.get("app_password") or ""
        if not wp_pass:
            raise HTTPException(400, "WordPress application password not found.")
        return WordPressAdapter(url=wp_url, username=wp_user, password=wp_pass)
    except IntegrationError as e:
        raise HTTPException(400, str(e))


def _detect_builder(content: str) -> str:
    if "<!-- wp:" in content:
        return "gutenberg"
    if "[et_pb_" in content or "[divi_" in content:
        return "divi"
    if "data-elementor" in content:
        return "elementor"
    return "classic"


def _cluster_keywords_block(rows: list) -> str:
    lines = []
    for r in rows:
        parts = []
        if r.impressions is not None:
            parts.append(f"impr:{r.impressions:,}")
        if r.position is not None:
            parts.append(f"pos:{r.position:.1f}")
        parts.append(f"status:{r.status}")
        if r.existing_url:
            parts.append(f"url:{r.existing_url}")
        lines.append(f"- {r.keyword} [{', '.join(parts)}]")
    return "\n".join(lines)


def _change_history_block(history: list[PageChange]) -> str:
    if not history:
        return "No previous improvements made to this page."
    lines = ["Previous improvements (most recent first):"]
    for c in history:
        lines.append(f"- [{c.created_at.strftime('%Y-%m-%d')}] {c.change_summary} (status: {c.status})")
    return "\n".join(lines)


# ── Schemas ───────────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    cluster_name: str


class ChangeOut(BaseModel):
    id: int
    cluster_name: str
    wp_post_id: int
    wp_post_url: str
    wp_post_type: str
    change_summary: str
    changes_made: Optional[list[str]] = None
    original_content: str
    new_content: str
    status: str
    created_at: datetime
    approved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/analyze", response_model=ChangeOut)
def analyze_cluster(
    body: AnalyzeRequest,
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Get cluster keywords
    rows = (
        db.query(Keyword)
        .filter(
            Keyword.user_id == current_user.id,
            Keyword.project_name == context.name,
            Keyword.cluster == body.cluster_name,
        )
        .all()
    )
    if not rows:
        raise HTTPException(404, f"Cluster '{body.cluster_name}' not found.")

    # Find hub keyword and its URL
    hub = next((r for r in rows if r.is_hub), rows[0])
    page_url = hub.existing_url
    if not page_url:
        raise HTTPException(400, "Hub keyword has no existing page URL. Run GSC sync first.")

    # Fetch page from WordPress
    wp = _get_wp_adapter(context, current_user.id, db)
    try:
        post_data = wp.find_post_by_url(page_url)
    except IntegrationError as e:
        raise HTTPException(502, f"WordPress error: {e}")

    if not post_data:
        raise HTTPException(404, f"Page not found in WordPress for URL: {page_url}")

    # Block unsupported builders
    builder = _detect_builder(post_data["content"])
    if builder in ("elementor", "divi"):
        raise HTTPException(400, f"This page uses {builder.title()} page builder. Automatic editing is not yet supported for {builder.title()}. Check the follow-up roadmap.")

    # Get change history for this cluster
    history = (
        db.query(PageChange)
        .filter(
            PageChange.user_id == current_user.id,
            PageChange.project_name == context.name,
            PageChange.cluster_name == body.cluster_name,
        )
        .order_by(PageChange.created_at.desc())
        .limit(5)
        .all()
    )

    # Find pillar page URL (hub's suggested_url or existing_url)
    pillar_url = hub.suggested_url or hub.existing_url or ""

    # Build agent prompt
    openai_key = get_user_secret("openai", current_user.id, db)
    agent = SkillAgent("seo-improve", openai_key, model="gpt-4o")

    user_msg = f"""## Cluster: {body.cluster_name}

## Hub Keyword
{hub.keyword} (pos: {hub.position or 'unknown'}, impr: {hub.impressions or 0})

## Pillar Page URL
{pillar_url}

## All Keywords in This Cluster
{_cluster_keywords_block(rows)}

## Page Builder
{builder}

## SEO Plugin
has_yoast: {post_data['has_yoast']}
has_rankmath: {post_data['has_rankmath']}

## Change History
{_change_history_block(history)}

## Current Page Content
Title: {post_data['title']}
URL: {post_data['link']}

{post_data['content']}
"""

    raw = agent.run(user_msg, timeout=120, json_mode=True)

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(500, "Agent returned invalid JSON. Please try again.")

    action_needed = result.get("action_needed", False)
    summary = result.get("summary", "")
    changes_made = result.get("changes_made", [])
    new_content = result.get("new_content") or post_data["content"]
    no_action_reason = result.get("no_action_reason")

    # Store in DB
    record = PageChange(
        user_id=current_user.id,
        project_name=context.name,
        cluster_name=body.cluster_name,
        wp_post_id=post_data["id"],
        wp_post_url=post_data["link"],
        wp_post_type=post_data["type"],
        original_content=post_data["content"],
        new_content=new_content,
        change_summary=no_action_reason if not action_needed else summary,
        changes_made=json.dumps(changes_made),
        status="no_action" if not action_needed else "pending",
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    record.changes_made = changes_made  # type: ignore[assignment]
    return record


@router.post("/apply/{change_id}", response_model=ChangeOut)
def apply_change(
    change_id: int,
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.query(PageChange).filter(
        PageChange.id == change_id,
        PageChange.user_id == current_user.id,
        PageChange.project_name == context.name,
    ).first()
    if not record:
        raise HTTPException(404, "Change not found.")
    if record.status != "pending":
        raise HTTPException(400, f"Change is already '{record.status}'.")

    wp = _get_wp_adapter(context, current_user.id, db)
    try:
        if record.wp_post_type == "page":
            wp.update_page(record.wp_post_id, record.new_content)
        else:
            wp.update_post(record.wp_post_id, record.new_content)
    except IntegrationError as e:
        raise HTTPException(502, f"WordPress error: {e}")

    record.status = "approved"
    record.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(record)

    try:
        record.changes_made = json.loads(record.changes_made or "[]")  # type: ignore[assignment]
    except Exception:
        record.changes_made = []  # type: ignore[assignment]
    return record


@router.post("/rollback/{change_id}", response_model=ChangeOut)
def rollback_change(
    change_id: int,
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.query(PageChange).filter(
        PageChange.id == change_id,
        PageChange.user_id == current_user.id,
        PageChange.project_name == context.name,
    ).first()
    if not record:
        raise HTTPException(404, "Change not found.")
    if record.status != "approved":
        raise HTTPException(400, "Only approved changes can be rolled back.")

    wp = _get_wp_adapter(context, current_user.id, db)
    try:
        if record.wp_post_type == "page":
            wp.update_page(record.wp_post_id, record.original_content)
        else:
            wp.update_post(record.wp_post_id, record.original_content)
    except IntegrationError as e:
        raise HTTPException(502, f"WordPress error: {e}")

    record.status = "rolled_back"
    db.commit()
    db.refresh(record)

    try:
        record.changes_made = json.loads(record.changes_made or "[]")  # type: ignore[assignment]
    except Exception:
        record.changes_made = []  # type: ignore[assignment]
    return record


@router.get("/history", response_model=list[ChangeOut])
def get_history(
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    records = (
        db.query(PageChange)
        .filter(
            PageChange.user_id == current_user.id,
            PageChange.project_name == context.name,
        )
        .order_by(PageChange.created_at.desc())
        .all()
    )
    for r in records:
        try:
            r.changes_made = json.loads(r.changes_made or "[]")  # type: ignore[assignment]
        except Exception:
            r.changes_made = []  # type: ignore[assignment]
    return records
