import json
import re
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from agents.base import SkillAgent
from api.dependencies import get_current_user, get_db, get_project_context
from api.routers.api_keys import get_user_secret
from core.db.models import Keyword, PageChange, User
from core.models.context import ProjectContext
from core.secrets import SecretManager
from integrations.cms.wordpress import WordPressAdapter
from integrations.base import IntegrationError
from shared.exceptions import SecretNotFoundError

router = APIRouter(prefix="/projects/{name}/improve", tags=["improve"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_wp_adapter(context: ProjectContext) -> WordPressAdapter:
    wp_cfg = context.config.integrations.wordpress
    if not wp_cfg.enabled:
        raise HTTPException(400, "WordPress integration is not connected. Go to Integrations tab first.")
    secrets = SecretManager()
    try:
        return WordPressAdapter(
            url=wp_cfg.url,
            username=secrets.get(wp_cfg.username_env),
            password=secrets.get(wp_cfg.password_env),
        )
    except (SecretNotFoundError, Exception) as e:
        raise HTTPException(400, f"WordPress credentials error: {e}")


def _detect_builder(content: str) -> str:
    if "<!-- wp:" in content:
        return "gutenberg"
    if "[et_pb_" in content or "[divi_" in content:
        return "divi"
    if "data-elementor" in content:
        return "elementor"
    if "[vc_row]" in content or "[vc_column]" in content:
        return "wpbakery"
    return "classic"


def _visible_word_count(html: str) -> int:
    return len(re.sub(r'<[^>]+>', ' ', html).split())


def _detect_page_profile(post_data: dict, is_hub: bool, hub_existing_url: str) -> dict:
    """
    Build a capability profile from the WordPress page data before running any agents.
    Determines what the system can do for this specific page at zero AI cost.
    """
    is_homepage = is_hub and not urlparse(hub_existing_url).path.strip("/")
    content = post_data.get("content", "")
    word_count = _visible_word_count(content)
    is_theme_controlled = is_homepage and word_count < 100

    builder = _detect_builder(content)
    content_editable = builder in ("gutenberg", "classic") and not is_theme_controlled

    has_yoast = post_data.get("has_yoast", False)
    has_rankmath = post_data.get("has_rankmath", False)
    seo_plugin = "yoast" if has_yoast else ("rankmath" if has_rankmath else "none")
    meta_editable = seo_plugin != "none"

    can_improve = content_editable or meta_editable

    blocked_reason: str | None = None
    if not can_improve:
        if builder in ("elementor", "divi", "wpbakery"):
            blocked_reason = (
                f"{builder.title()} page builder detected — content editing is not yet supported for this builder. "
                f"No Yoast SEO or RankMath plugin was found either. "
                f"Install Yoast SEO or RankMath to enable automatic SEO title and description updates."
            )
        elif is_theme_controlled:
            blocked_reason = (
                "This homepage content is managed by your theme template — "
                "post_content edits are not rendered on the frontend. "
                "No Yoast SEO or RankMath plugin was found. "
                "Install Yoast SEO or RankMath to enable automatic SEO title and description updates."
            )
        else:
            blocked_reason = (
                "No improvements possible: page content is not editable and no SEO plugin (Yoast/RankMath) is active."
            )

    return {
        "seo_plugin": seo_plugin,
        "builder": builder,
        "is_homepage": is_homepage,
        "is_theme_controlled": is_theme_controlled,
        "content_editable": content_editable,
        "meta_editable": meta_editable,
        "can_improve": can_improve,
        "blocked_reason": blocked_reason,
    }


def _wp_push(wp: WordPressAdapter, record: PageChange, content: str) -> None:
    if record.wp_post_type == "page":
        wp.update_page(record.wp_post_id, content)
    else:
        wp.update_post(record.wp_post_id, content)


def _change_history_block(history: list[PageChange]) -> str:
    if not history:
        return "No previous improvements made to this page."
    lines = ["Previous improvements (most recent first):"]
    for c in history:
        lines.append(f"- [{c.created_at.strftime('%Y-%m-%d')}] {c.change_summary} (status: {c.status})")
    return "\n".join(lines)


def _run_page_pipeline(
    keyword: str,
    secondary_keywords: str,
    post_data: dict,
    pillar_url: str,
    history: list,
    project,
    openai_key: str,
    user_id: int,
    project_name: str,
    cluster_name: str,
    db: Session,
    is_hub: bool = False,
    hub_existing_url: str = "",
    seo_plugin: str = "none",
) -> PageChange:
    # Override per-page detection with the authoritative namespace-based result
    post_data["has_yoast"] = seo_plugin == "yoast"
    post_data["has_rankmath"] = seo_plugin == "rankmath"
    profile = _detect_page_profile(post_data, is_hub, hub_existing_url)
    current_date = datetime.utcnow().strftime("%B %Y")

    # Pre-flight: nothing can be done — return immediately at zero AI cost
    if not profile["can_improve"]:
        record = PageChange(
            user_id=user_id,
            project_name=project_name,
            cluster_name=cluster_name,
            wp_post_id=post_data["id"],
            wp_post_url=post_data["link"],
            wp_post_type=post_data["type"],
            original_content=post_data["content"],
            new_content=post_data["content"],
            change_summary=profile["blocked_reason"] or "No improvements possible.",
            changes_made=[],
            statistics=None,
            meta_updates=None,
            status="no_action",
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    business_context = " | ".join(filter(None, [
        project.business_name,
        project.business_type,
        project.tone_of_voice,
        project.target_audience,
    ])) or "Not specified"

    # ── Step 1: Analyzer (gpt-4o-mini) ───────────────────────────────────────
    analyzer_msg = f"""## main_keyword
{keyword}

## secondary_keywords
{secondary_keywords}

## hub_url
{pillar_url}

## current_url
{post_data['link']}

## is_homepage
{str(profile['is_homepage']).lower()}

## author
{project.business_name or 'Site Owner'}

## has_yoast
{post_data['has_yoast']}

## has_rankmath
{post_data['has_rankmath']}

## builder
{profile['builder']}

## business_context
{business_context}

## change_history
{_change_history_block(history)}

## html_content (Title: {post_data['title']})
{post_data['content']}
"""

    raw_analysis = SkillAgent("seo-analyzer", openai_key, model="gpt-4o-mini").run(
        analyzer_msg, timeout=60, json_mode=True
    )
    try:
        analysis = json.loads(raw_analysis)
    except json.JSONDecodeError:
        raise ValueError("Analyzer returned invalid JSON.")

    action_needed = analysis.get("action_needed", False)

    changes_made: list = []
    new_content: str = post_data["content"]
    meta_updates: dict | None = None

    # Run editor when content needs improvement OR SEO plugin is present (for meta)
    if action_needed or profile["meta_editable"]:
        # ── Step 2: Editor (gpt-4o) ───────────────────────────────────────────
        editor_msg = f"""## main_keyword
{keyword}

## hub_url
{pillar_url}

## is_homepage
{str(profile['is_homepage']).lower()}

## is_theme_controlled
{str(profile['is_theme_controlled']).lower()}

## author
{project.business_name or 'Site Owner'}

## current_date
{current_date}

## has_yoast
{post_data['has_yoast']}

## has_rankmath
{post_data['has_rankmath']}

## builder
{profile['builder']}

## current_meta_title
{post_data.get('current_meta_title', '')}

## current_meta_description
{post_data.get('current_meta_description', '')}

## business_context
{business_context}

## recommendations
{json.dumps(analysis.get('recommendations', []), indent=2)}

## html_content (Title: {post_data['title']})
{post_data['content']}
"""

        raw_edit = SkillAgent("seo-editor", openai_key, model="gpt-4o").run(
            editor_msg, timeout=120, json_mode=True
        )
        try:
            edit_result = json.loads(raw_edit)
        except json.JSONDecodeError:
            raise ValueError("Editor returned invalid JSON.")

        # Content changes — only apply when content is actually editable
        if profile["content_editable"] and action_needed:
            changes_made = [
                f"{c['type']}: {c['description']}"
                for c in edit_result.get("changes_made", [])
                if isinstance(c, dict) and c.get("status") == "applied"
            ]
            new_content = edit_result.get("new_content") or post_data["content"]

        # Meta changes — only store when plugin is present
        if profile["meta_editable"]:
            meta_title = (edit_result.get("suggested_meta_title") or "").strip()
            meta_description = (edit_result.get("suggested_meta_description") or "").strip()
            if meta_title or meta_description:
                meta_updates = {
                    "plugin": profile["seo_plugin"],
                    "suggested_meta_title": meta_title or None,
                    "suggested_meta_description": meta_description or None,
                }
                plugin_label = "Yoast" if profile["seo_plugin"] == "yoast" else "RankMath"
                changes_made.append(
                    f"seo_meta: SEO title and description queued for {plugin_label} update."
                )

    # Build the human-readable summary
    has_content_change = new_content != post_data["content"]
    has_meta = bool(meta_updates)
    plugin_label = "Yoast" if profile["seo_plugin"] == "yoast" else "RankMath"

    if profile["is_theme_controlled"]:
        change_summary = (
            f"Homepage content is managed by your theme template — post_content edits are not visible on the frontend. "
            f"SEO title and description will be updated via {plugin_label}."
        )
    elif not profile["content_editable"] and has_meta:
        change_summary = (
            f"{profile['builder'].title()} page detected — content editing is not yet supported for this builder. "
            f"SEO title and description will be updated via {plugin_label}."
        )
    elif has_content_change or has_meta:
        change_summary = analysis.get("summary", "")
    else:
        change_summary = analysis.get("no_action_reason") or "Page is already well-optimized — no changes needed."

    record = PageChange(
        user_id=user_id,
        project_name=project_name,
        cluster_name=cluster_name,
        wp_post_id=post_data["id"],
        wp_post_url=post_data["link"],
        wp_post_type=post_data["type"],
        original_content=post_data["content"],
        new_content=new_content,
        change_summary=change_summary,
        changes_made=changes_made,
        statistics=analysis.get("statistics"),
        meta_updates=meta_updates,
        status="pending" if (has_content_change or has_meta) else "no_action",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


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
    statistics: Optional[dict] = None
    meta_updates: Optional[dict] = None
    original_content: str
    new_content: str
    status: str
    created_at: datetime
    approved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/analyze", response_model=list[ChangeOut])
def analyze_cluster(
    body: AnalyzeRequest,
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

    wp = _get_wp_adapter(context)

    try:
        hub_post_data = wp.find_post_by_url(hub.existing_url)
    except IntegrationError as e:
        raise HTTPException(502, f"WordPress error: {e}")
    if not hub_post_data:
        raise HTTPException(404, f"Page not found in WordPress for URL: {hub.existing_url}")

    history = (
        db.query(PageChange)
        .filter(
            PageChange.user_id == current_user.id,
            PageChange.project_name == context.name,
            PageChange.cluster_name == body.cluster_name,
        )
        .order_by(PageChange.created_at.desc())
        .limit(10)
        .all()
    )

    project = context.config
    pillar_url = hub.suggested_url or hub.existing_url or ""
    openai_key = get_user_secret("openai", current_user.id, db)

    # Detect SEO plugin once via namespace registry — reliable even when meta values are empty
    seo_plugin = wp.detect_seo_plugin()

    results: list[PageChange] = []

    # ── Hub ───────────────────────────────────────────────────────────────────
    hub_secondary = ", ".join(r.keyword for r in rows if not r.is_hub) or "None"
    try:
        hub_record = _run_page_pipeline(
            keyword=hub.keyword,
            secondary_keywords=hub_secondary,
            post_data=hub_post_data,
            pillar_url=pillar_url,
            history=history,
            project=project,
            openai_key=openai_key,
            user_id=current_user.id,
            project_name=context.name,
            cluster_name=body.cluster_name,
            db=db,
            is_hub=True,
            hub_existing_url=hub.existing_url,
            seo_plugin=seo_plugin,
        )
        results.append(hub_record)
    except (ValueError, Exception) as e:
        raise HTTPException(500, f"Hub analysis failed: {e}")

    # ── Spokes (unique URLs only) ─────────────────────────────────────────────
    seen_urls = {hub.existing_url}
    unique_spokes: list = []
    for r in rows:
        if not r.is_hub and r.existing_url and r.existing_url not in seen_urls:
            seen_urls.add(r.existing_url)
            unique_spokes.append(r)

    for spoke in unique_spokes[:5]:
        try:
            spoke_post_data = wp.find_post_by_url(spoke.existing_url)
            if not spoke_post_data:
                continue
            spoke_secondary = ", ".join(r.keyword for r in rows if r.keyword != spoke.keyword) or "None"
            spoke_record = _run_page_pipeline(
                keyword=spoke.keyword,
                secondary_keywords=spoke_secondary,
                post_data=spoke_post_data,
                pillar_url=pillar_url,
                history=history,
                project=project,
                openai_key=openai_key,
                user_id=current_user.id,
                project_name=context.name,
                cluster_name=body.cluster_name,
                db=db,
                is_hub=False,
                hub_existing_url=hub.existing_url,
                seo_plugin=seo_plugin,
            )
            results.append(spoke_record)
        except Exception:
            continue

    return results


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

    wp = _get_wp_adapter(context)
    content_changed = record.original_content != record.new_content

    # Push content only if it actually changed
    if content_changed:
        try:
            _wp_push(wp, record, record.new_content)
        except IntegrationError as e:
            raise HTTPException(502, f"WordPress content update error: {e}")

    # Push SEO meta via Yoast or RankMath if present
    if record.meta_updates:
        mu = record.meta_updates
        try:
            wp.update_seo_meta(
                record.wp_post_id,
                record.wp_post_type,
                mu["plugin"],
                mu.get("suggested_meta_title"),
                mu.get("suggested_meta_description"),
            )
        except IntegrationError as e:
            if not content_changed:
                # Meta-only change — surface the error
                raise HTTPException(502, f"SEO meta update error: {e}")
            # Content already pushed — meta failure is non-fatal

    record.status = "approved"
    record.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(record)
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

    wp = _get_wp_adapter(context)
    # Rollback content only if it was changed
    if record.original_content != record.new_content:
        try:
            _wp_push(wp, record, record.original_content)
        except IntegrationError as e:
            raise HTTPException(502, f"WordPress rollback error: {e}")

    record.status = "rolled_back"
    db.commit()
    db.refresh(record)
    return record


@router.get("/history", response_model=list[ChangeOut])
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
        )
        .order_by(PageChange.created_at.desc())
        .all()
    )
