"""
Shopify SEO improve pipeline.

Mirrors the WordPress improve.py flow but for Shopify:
  - No builder detection (Shopify body_html is always clean HTML)
  - Meta via native metafields (global namespace) — always editable
  - Resource types: product / collection / page / blog_post

Routes:
  POST /projects/{name}/shopify/improve/analyze
  POST /projects/{name}/shopify/improve/apply/{change_id}
  POST /projects/{name}/shopify/improve/rollback/{change_id}
  GET  /projects/{name}/shopify/improve/history
"""

import json
import logging
import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from agents.base import SkillAgent
from api.dependencies import get_current_user, get_db, get_project_context
from api.routers.identity.api_keys import get_user_secret
from api.utils.knowledge import fetch_knowledge
from core.change_utils import build_shopify_meta_updates
from core.db.models import Keyword, PageChange, User
from core.models.context import ProjectContext
from core.secrets import SecretManager
from integrations.cms.shopify import ShopifyAdapter
from shared.exceptions import IntegrationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{name}/shopify/improve", tags=["shopify-improve"])

# Hub + spokes analyzed in a single /analyze run
_MAX_RESOURCES_PER_RUN = 6

_META_CHANGE_NOTE = "seo_meta: SEO title and description queued via Shopify metafields."


# ── Adapter factory ────────────────────────────────────────────────────────────

def _get_shopify_adapter(context: ProjectContext) -> ShopifyAdapter:
    cfg = context.config.integrations.shopify
    if not cfg.enabled:
        raise HTTPException(400, "Shopify integration is not connected. Go to Integrations tab first.")
    try:
        token = SecretManager().get(cfg.token_env)
    except Exception as e:
        raise HTTPException(400, f"Shopify credentials error: {e}") from e
    return ShopifyAdapter(store_url=cfg.store_url, access_token=token)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _visible_word_count(html: str) -> int:
    return len(re.sub(r'<[^>]+>', ' ', html).split())


def _build_business_context(context: ProjectContext, db: Session, user_id: int) -> str:
    kb = fetch_knowledge(db, user_id, context.name)
    if kb:
        parts = []
        if kb.about:             parts.append(f"About: {kb.about.strip()}")
        if kb.products_services: parts.append(f"Products/Services: {kb.products_services.strip()}")
        if kb.target_audience:   parts.append(f"Target Audience: {kb.target_audience.strip()}")
        if kb.brand_voice:       parts.append(f"Brand Voice: {kb.brand_voice.strip()}")
        if parts:
            return "\n".join(parts)

    cfg = context.config
    return " | ".join(filter(None, [
        cfg.business_name, cfg.business_type, cfg.tone_of_voice, cfg.target_audience
    ])) or "Not specified"


def _run_json_agent(skill: str, openai_key: str, model: str, message: str, timeout: int) -> dict | None:
    """Run a skill agent in JSON mode. Returns None when the model returns invalid JSON."""
    raw = SkillAgent(skill, openai_key, model=model).run(message, timeout=timeout, json_mode=True)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Shopify skill '%s' returned invalid JSON.", skill)
        return None


def _build_meta_updates(
    agent_result: dict,
    seo_meta: dict,
    resource_type: str,
    resource_id: int,
) -> dict | None:
    """Compare agent-suggested meta against what is live and build the update payload."""
    return build_shopify_meta_updates(
        seo_meta.get("meta_title"),
        seo_meta.get("meta_description"),
        (agent_result.get("suggested_meta_title") or "").strip() or None,
        (agent_result.get("suggested_meta_description") or "").strip() or None,
        resource_type,
        resource_id,
    )


def _resource_ref(record: PageChange) -> dict:
    """Minimal resource dict for ShopifyAdapter.update_resource_body()."""
    return {
        "id": record.wp_post_id,
        "type": record.wp_post_type,
        "blog_id": (record.statistics or {}).get("blog_id"),
    }


def _load_change(db: Session, change_id: int, user_id: int, project_name: str) -> PageChange:
    record = db.query(PageChange).filter(
        PageChange.id == change_id,
        PageChange.user_id == user_id,
        PageChange.project_name == project_name,
        PageChange.platform == "shopify",
    ).first()
    if not record:
        raise HTTPException(404, "Shopify change not found.")
    return record


# ── Core pipeline ──────────────────────────────────────────────────────────────

def _run_shopify_pipeline(
    keyword: str,
    secondary_keywords: str,
    resource: dict,
    hub_url: str,
    seo_meta: dict,
    openai_key: str,
    user_id: int,
    project_name: str,
    cluster_name: str,
    context: ProjectContext,
    db: Session,
) -> PageChange:
    """
    Run analyzer → editor for one Shopify resource. Returns a PageChange record.
    resource: normalized dict from ShopifyAdapter with keys id, title, handle, body_html, type, link
    seo_meta: dict with meta_title, meta_description from ShopifyAdapter.get_seo_meta()
    """
    resource_id = resource["id"]
    resource_type = resource.get("type", "product")
    resource_title = resource.get("title", "")
    body_html = resource.get("body_html", "")
    current_url = f"{context.config.website.rstrip('/')}{resource['link']}"
    business_context = _build_business_context(context, db, user_id)

    # ── Step 1: Analyzer (gpt-4o-mini) ────────────────────────────────────────
    analyzer_msg = f"""## main_keyword
{keyword}

## secondary_keywords
{secondary_keywords}

## resource_type
{resource_type}

## resource_title
{resource_title}

## current_url
{current_url}

## hub_url
{hub_url}

## business_context
{business_context}

## html_content
{body_html}
"""

    analysis = _run_json_agent("seo-analyzer-shopify", openai_key, "gpt-4o-mini", analyzer_msg, 60)
    if analysis is None:
        raise ValueError("Shopify analyzer returned invalid JSON.")

    # ── Step 2: Editor (gpt-4o), or meta-only when no content work is needed ──
    new_body_html = body_html
    changes_made: list[str] = []

    if analysis.get("action_needed", False):
        editor_msg = f"""## main_keyword
{keyword}

## resource_type
{resource_type}

## hub_url
{hub_url}

## business_context
{business_context}

## current_meta_title
{seo_meta.get('meta_title', '')}

## current_meta_description
{seo_meta.get('meta_description', '')}

## recommendations
{json.dumps(analysis.get('recommendations', []), indent=2)}

## html_content
{body_html}
"""
        edit_result = _run_json_agent("seo-editor-shopify", openai_key, "gpt-4o", editor_msg, 120)
        if edit_result is None:
            raise ValueError("Shopify editor returned invalid JSON.")

        new_body_html = edit_result.get("new_content") or body_html
        changes_made = [
            f"{c['type']}: {c['description']}"
            for c in edit_result.get("changes_made", [])
            if isinstance(c, dict) and c.get("status") == "applied"
        ]
        meta_source = edit_result
    else:
        # Even when no content changes are needed, run seo-meta-shopify for meta
        meta_msg = f"""## main_keyword
{keyword}

## resource_type
{resource_type}

## resource_title
{resource_title}

## current_meta_title
{seo_meta.get('meta_title', '')}

## current_meta_description
{seo_meta.get('meta_description', '')}

## business_context
{business_context}

## is_homepage
false
"""
        meta_source = _run_json_agent("seo-meta-shopify", openai_key, "gpt-4o-mini", meta_msg, 60) or {}

    # Meta updates — always possible on Shopify via metafields
    meta_updates = _build_meta_updates(meta_source, seo_meta, resource_type, resource_id)
    if meta_updates:
        changes_made.append(_META_CHANGE_NOTE)

    has_change = new_body_html != body_html or bool(meta_updates)
    change_summary = (
        analysis.get("summary", "")
        if has_change
        else analysis.get("no_action_reason") or "Resource is already well-optimized — no changes needed."
    )

    statistics = {
        **(analysis.get("statistics") or {}),
        "word_count": _visible_word_count(body_html),
    }
    if resource.get("blog_id"):
        statistics["blog_id"] = resource["blog_id"]

    record = PageChange(
        user_id=user_id,
        project_name=project_name,
        cluster_name=cluster_name,
        wp_post_id=resource_id,
        wp_post_url=current_url,
        wp_post_type=resource_type,
        original_content=body_html,
        new_content=new_body_html,
        change_summary=change_summary,
        changes_made=changes_made,
        statistics=statistics,
        meta_updates=meta_updates,
        platform="shopify",
        action_type="page_edit",
        shopify_resource_id=resource_id,
        shopify_resource_type=resource_type,
        status="pending" if has_change else "no_action",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# ── Schemas ────────────────────────────────────────────────────────────────────

class ShopifyAnalyzeRequest(BaseModel):
    cluster_name: str


class ShopifyChangeOut(BaseModel):
    id: int
    action_type: str = "page_edit"
    platform: str = "shopify"
    cluster_name: str
    wp_post_id: int
    wp_post_url: str
    wp_post_type: str
    shopify_resource_id: Optional[int] = None
    shopify_resource_type: Optional[str] = None
    change_summary: str
    changes_made: Optional[list[str]] = None
    statistics: Optional[dict] = None
    meta_updates: Optional[dict] = None
    original_content: str
    new_content: str
    status: str
    created_at: datetime
    approved_at: Optional[datetime] = None
    applied_by: Optional[str] = None

    class Config:
        from_attributes = True


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/analyze", response_model=list[ShopifyChangeOut])
def analyze_cluster(
    body: ShopifyAnalyzeRequest,
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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

    hub = next((r for r in rows if r.is_hub), rows[0])
    if not hub.existing_url:
        raise HTTPException(400, "Hub keyword has no existing page URL. Run GSC sync first.")

    shopify = _get_shopify_adapter(context)
    openai_key = get_user_secret("openai", current_user.id, db)

    hub_resource = shopify.find_resource_by_url(hub.existing_url)
    if not hub_resource:
        raise HTTPException(404, f"Shopify resource not found for URL: {hub.existing_url}")

    hub_url = hub.suggested_url or hub.existing_url
    hub_secondary = ", ".join(r.keyword for r in rows if not r.is_hub) or "None"

    try:
        hub_record = _run_shopify_pipeline(
            keyword=hub.keyword,
            secondary_keywords=hub_secondary,
            resource=hub_resource,
            hub_url=hub_url,
            seo_meta=shopify.get_seo_meta(hub_resource["type"], hub_resource["id"]),
            openai_key=openai_key,
            user_id=current_user.id,
            project_name=context.name,
            cluster_name=body.cluster_name,
            context=context,
            db=db,
        )
    except Exception as e:
        raise HTTPException(500, f"Hub analysis failed: {e}") from e

    results: list[PageChange] = [hub_record]
    seen_urls = {hub.existing_url}

    for spoke in rows:
        if len(results) >= _MAX_RESOURCES_PER_RUN:
            break
        if spoke.is_hub or not spoke.existing_url or spoke.existing_url in seen_urls:
            continue
        seen_urls.add(spoke.existing_url)

        try:
            resource = shopify.find_resource_by_url(spoke.existing_url)
            if not resource:
                logger.warning("No Shopify resource for spoke URL: %s", spoke.existing_url)
                continue
            spoke_secondary = ", ".join(r.keyword for r in rows if r.keyword != spoke.keyword) or "None"
            results.append(_run_shopify_pipeline(
                keyword=spoke.keyword,
                secondary_keywords=spoke_secondary,
                resource=resource,
                hub_url=hub_url,
                seo_meta=shopify.get_seo_meta(resource["type"], resource["id"]),
                openai_key=openai_key,
                user_id=current_user.id,
                project_name=context.name,
                cluster_name=body.cluster_name,
                context=context,
                db=db,
            ))
        except Exception:
            logger.exception("Shopify spoke analysis failed for %s", spoke.existing_url)
            continue

    return results


@router.post("/apply/{change_id}", response_model=ShopifyChangeOut)
def apply_change(
    change_id: int,
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = _load_change(db, change_id, current_user.id, context.name)
    if record.status != "pending":
        raise HTTPException(400, f"Change is already '{record.status}'.")

    shopify = _get_shopify_adapter(context)

    # Push content if changed
    if record.original_content != record.new_content:
        try:
            shopify.update_resource_body(_resource_ref(record), record.new_content)
        except IntegrationError as e:
            raise HTTPException(502, f"Shopify content update error: {e}") from e

    # Push meta via Shopify metafields
    if record.meta_updates:
        raw_title = (record.meta_updates.get("suggested_meta_title") or "").strip()
        raw_desc = (record.meta_updates.get("suggested_meta_description") or "").strip()
        # Hard-cap title at 60 chars (trim at last word boundary)
        if len(raw_title) > 60:
            raw_title = raw_title[:60].rsplit(" ", 1)[0].rstrip(" |—-")
        try:
            shopify.update_seo_meta(
                resource_type=record.wp_post_type,
                resource_id=record.wp_post_id,
                meta_title=raw_title or None,
                meta_description=raw_desc or None,
            )
        except IntegrationError as e:
            raise HTTPException(502, f"Shopify meta update error: {e}") from e

    record.status = "approved"
    record.approved_at = datetime.utcnow()
    record.applied_by = "subscriber"
    db.commit()
    db.refresh(record)

    try:
        from core.state_machine import advance_state
        advance_state(context, "ACTIVE")
    except Exception:
        logger.warning("Could not advance project state for '%s'.", context.name, exc_info=True)

    return record


@router.post("/rollback/{change_id}", response_model=ShopifyChangeOut)
def rollback_change(
    change_id: int,
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = _load_change(db, change_id, current_user.id, context.name)
    if record.status != "approved":
        raise HTTPException(400, "Only approved changes can be rolled back.")

    shopify = _get_shopify_adapter(context)

    if record.original_content != record.new_content:
        try:
            shopify.update_resource_body(_resource_ref(record), record.original_content)
        except IntegrationError as e:
            raise HTTPException(502, f"Shopify rollback error: {e}") from e

    if record.meta_updates:
        try:
            shopify.update_seo_meta(
                resource_type=record.wp_post_type,
                resource_id=record.wp_post_id,
                meta_title=record.meta_updates.get("original_meta_title"),
                meta_description=record.meta_updates.get("original_meta_description"),
            )
        except IntegrationError as e:
            raise HTTPException(502, f"Shopify meta rollback error: {e}") from e

    record.status = "rolled_back"
    db.commit()
    db.refresh(record)
    return record


@router.get("/history", response_model=list[ShopifyChangeOut])
def get_history(
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(PageChange)
        .filter(
            PageChange.user_id == current_user.id,
            PageChange.project_name == context.name,
            PageChange.platform == "shopify",
        )
        .order_by(PageChange.created_at.desc())
        .all()
    )
