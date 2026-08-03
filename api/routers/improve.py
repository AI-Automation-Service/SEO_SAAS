import json
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
    return "classic"


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
) -> PageChange:
    is_homepage = is_hub and not urlparse(hub_existing_url).path.strip("/")
    current_date = datetime.utcnow().strftime("%B %Y")

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
{str(is_homepage).lower()}

## author
{project.business_name or 'Site Owner'}

## has_yoast
{post_data['has_yoast']}

## has_rankmath
{post_data['has_rankmath']}

## builder
{_detect_builder(post_data['content'])}

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
    summary = analysis.get("summary", "")
    no_action_reason = analysis.get("no_action_reason")

    changes_made: list = []
    new_content: str = post_data["content"]

    if action_needed:
        # ── Step 2: Editor (gpt-4o) ───────────────────────────────────────────
        editor_msg = f"""## main_keyword
{keyword}

## hub_url
{pillar_url}

## is_homepage
{str(is_homepage).lower()}

## author
{project.business_name or 'Site Owner'}

## current_date
{current_date}

## has_yoast
{post_data['has_yoast']}

## has_rankmath
{post_data['has_rankmath']}

## builder
{_detect_builder(post_data['content'])}

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

        changes_made = [
            f"{c['type']}: {c['description']}"
            for c in edit_result.get("changes_made", [])
            if isinstance(c, dict) and c.get("status") == "applied"
        ]
        new_content = edit_result.get("new_content") or post_data["content"]

    record = PageChange(
        user_id=user_id,
        project_name=project_name,
        cluster_name=cluster_name,
        wp_post_id=post_data["id"],
        wp_post_url=post_data["link"],
        wp_post_type=post_data["type"],
        original_content=post_data["content"],
        new_content=new_content,
        change_summary=no_action_reason if not action_needed else summary,
        changes_made=changes_made,
        statistics=analysis.get("statistics"),
        status="no_action" if not action_needed else "pending",
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

    hub_builder = _detect_builder(hub_post_data["content"])
    if hub_builder in ("elementor", "divi"):
        raise HTTPException(
            400,
            f"The hub page uses {hub_builder.title()} page builder. "
            "Automatic editing is not yet supported for this builder.",
        )

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
        )
        results.append(hub_record)
    except (ValueError, Exception) as e:
        raise HTTPException(500, f"Hub analysis failed: {e}")

    # ── Spokes (up to 5 with existing_url, skip page builders) ───────────────
    spokes = [r for r in rows if not r.is_hub and r.existing_url][:5]
    for spoke in spokes:
        try:
            spoke_post_data = wp.find_post_by_url(spoke.existing_url)
            if not spoke_post_data:
                continue
            if _detect_builder(spoke_post_data["content"]) in ("elementor", "divi"):
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
    try:
        _wp_push(wp, record, record.new_content)
    except IntegrationError as e:
        raise HTTPException(502, f"WordPress error: {e}")

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
    try:
        _wp_push(wp, record, record.original_content)
    except IntegrationError as e:
        raise HTTPException(502, f"WordPress error: {e}")

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
