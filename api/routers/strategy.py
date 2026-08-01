from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from agents.base import SkillAgent
from api.dependencies import get_current_user, get_db, get_project_context
from api.routers.api_keys import get_user_secret
from core.db.models import Keyword, SitePage, User
from core.models.context import ProjectContext

router = APIRouter(prefix="/projects/{name}/strategy", tags=["strategy"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _project_block(ctx: ProjectContext) -> str:
    cfg = ctx.config
    return (
        f"Business: {cfg.business_name} ({cfg.business_type})\n"
        f"Website: {cfg.website}\n"
        f"Country: {cfg.country}, Language: {cfg.language}\n"
        f"Tone of voice: {cfg.tone_of_voice}\n"
        f"Target audience: {cfg.target_audience}\n"
        f"SEO goals: {', '.join(cfg.seo_goals)}\n"
        f"Business goals: {', '.join(cfg.business_goals)}\n"
        f"Competitors: {', '.join(cfg.competitors) if cfg.competitors else 'None specified'}"
    )


def _cluster_summary(rows: list) -> str:
    clusters: dict[str, list] = {}
    for r in rows:
        key = r.cluster or "Unclustered"
        clusters.setdefault(key, []).append(r)

    lines = []
    for name, kws in sorted(clusters.items()):
        hub = next((k for k in kws if k.is_hub), None)
        hub_kw = hub.keyword if hub else kws[0].keyword
        stages = sorted({k.funnel_stage for k in kws if k.funnel_stage})
        statuses = sorted({k.status for k in kws})
        has_pages = sum(1 for k in kws if k.existing_url)
        extra = f", {has_pages} with existing pages" if has_pages else ""
        lines.append(
            f"- {name}: hub='{hub_kw}', {len(kws)} keywords, "
            f"funnel={stages}, statuses={statuses}{extra}"
        )
    return "\n".join(lines) if lines else "No clusters yet."


def _require_clustered(rows: list) -> None:
    if not rows:
        raise HTTPException(400, "No keywords found. Sync from GSC or upload a CSV first.")
    if not any(r.cluster for r in rows):
        raise HTTPException(400, "Keywords are not clustered yet. Run the Cluster Agent in the Keywords tab first.")


def _run_skill(skill_name: str, openai_key: str, message: str, timeout: int = 180) -> str:
    try:
        return SkillAgent(skill_name, openai_key).run(message, timeout=timeout)
    except FileNotFoundError as e:
        raise HTTPException(500, str(e))
    except Exception as e:
        raise HTTPException(502, f"OpenAI error: {e}")


def _sitemap_block(db: Session, user_id: int, project_name: str) -> str:
    pages = (
        db.query(SitePage)
        .filter(SitePage.user_id == user_id, SitePage.project_name == project_name)
        .all()
    )
    if not pages:
        return ""
    sample = ", ".join(f"/{p.slug}" for p in pages[:15])
    return (
        f"\nExisting site pages: {len(pages)} pages found in sitemap.\n"
        f"Sample slugs: {sample}\n"
        "IMPORTANT: For topics that already have existing pages, recommend OPTIMIZING the existing page. "
        "Do NOT suggest creating new content for topics already covered."
    )


def _get_keywords(db: Session, user_id: int, project_name: str) -> list:
    return (
        db.query(Keyword)
        .filter(Keyword.user_id == user_id, Keyword.project_name == project_name)
        .all()
    )


# ── Schemas ───────────────────────────────────────────────────────────────────

class StrategyResult(BaseModel):
    skill: str
    output: str


class CompetitorPageRequest(BaseModel):
    competitor_url: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/plan", response_model=StrategyResult)
def run_seo_plan(
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    openai_key = get_user_secret("openai", current_user.id, db)
    rows = _get_keywords(db, current_user.id, context.name)
    _require_clustered(rows)

    cluster_count = len({r.cluster for r in rows if r.cluster})
    sitemap = _sitemap_block(db, current_user.id, context.name)
    msg = (
        f"{_project_block(context)}\n\n"
        f"Keyword data: {len(rows)} keywords across {cluster_count} clusters.\n\n"
        f"Cluster summary:\n{_cluster_summary(rows)}"
        f"{sitemap}\n\n"
        "Generate a complete 12-month SEO plan with 4 phases (Foundation weeks 1-4, "
        "Expansion weeks 5-12, Scale weeks 13-24, Authority months 7-12). "
        "Include: executive summary, KPI targets table (Baseline/3 Month/6 Month/12 Month), "
        "content priorities per cluster, and phased implementation roadmap. Output in Markdown."
    )
    return StrategyResult(skill="seo-plan", output=_run_skill("seo-plan", openai_key, msg))


@router.post("/content", response_model=StrategyResult)
def run_content_strategy(
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    openai_key = get_user_secret("openai", current_user.id, db)
    rows = _get_keywords(db, current_user.id, context.name)
    _require_clustered(rows)

    tofu = sum(1 for r in rows if r.funnel_stage == "tofu")
    mofu = sum(1 for r in rows if r.funnel_stage == "mofu")
    bofu = sum(1 for r in rows if r.funnel_stage == "bofu")

    sitemap = _sitemap_block(db, current_user.id, context.name)
    msg = (
        f"{_project_block(context)}\n\n"
        f"Funnel breakdown: TOFU={tofu}, MOFU={mofu}, BOFU={bofu}\n\n"
        f"Cluster summary:\n{_cluster_summary(rows)}"
        f"{sitemap}\n\n"
        "Generate a content strategy with:\n"
        "1. 3-5 content pillars with rationale tied to keyword clusters\n"
        "2. Priority topics table: Topic | Funnel Stage | Intent | Content Type | Priority\n"
        "3. Topic cluster map (pillar → spokes)\n"
        "4. Publishing cadence recommendation per pillar\n"
        "Output in Markdown."
    )
    return StrategyResult(skill="content-strategy", output=_run_skill("content-strategy", openai_key, msg))


@router.post("/architecture", response_model=StrategyResult)
def run_site_architecture(
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    openai_key = get_user_secret("openai", current_user.id, db)
    rows = _get_keywords(db, current_user.id, context.name)
    _require_clustered(rows)

    url_sample = "\n".join(
        f"  {r.keyword} → {r.suggested_url}"
        for r in rows if r.suggested_url
    )[:2000]

    sitemap = _sitemap_block(db, current_user.id, context.name)
    msg = (
        f"{_project_block(context)}\n\n"
        f"Cluster summary:\n{_cluster_summary(rows)}"
        f"{sitemap}\n\n"
        f"Sample keyword → suggested URL mappings:\n{url_sample}\n\n"
        "Generate a site architecture plan with:\n"
        "1. ASCII page hierarchy tree with URLs\n"
        "2. URL pattern table: Page Type | Pattern | Example\n"
        "3. Navigation spec: header nav items (max 6) + footer columns\n"
        "4. Internal linking plan: hub pages and their spokes with anchor text recommendations\n"
        "Output in Markdown."
    )
    return StrategyResult(skill="site-architecture", output=_run_skill("site-architecture", openai_key, msg))


@router.post("/flow/{keyword_id}", response_model=StrategyResult)
def run_seo_flow(
    keyword_id: int,
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    openai_key = get_user_secret("openai", current_user.id, db)
    kw = (
        db.query(Keyword)
        .filter(
            Keyword.id == keyword_id,
            Keyword.user_id == current_user.id,
            Keyword.project_name == context.name,
        )
        .first()
    )
    if not kw:
        raise HTTPException(404, "Keyword not found.")

    msg = (
        f"Business: {context.config.business_name} ({context.config.business_type})\n"
        f"Website: {context.config.website}\n\n"
        f"Keyword: {kw.keyword}\n"
        f"Status: {kw.status}\n"
        f"Position: {kw.position or 'not ranking'}\n"
        f"Impressions: {kw.impressions or 0}, Clicks: {kw.clicks or 0}, "
        f"CTR: {f'{kw.ctr:.1%}' if kw.ctr else 'N/A'}\n"
        f"Cluster: {kw.cluster or 'unclustered'} ({'hub' if kw.is_hub else 'spoke'})\n"
        f"Intent: {kw.intent or 'N/A'}, Funnel: {kw.funnel_stage or 'N/A'}\n"
        f"Existing URL: {kw.existing_url or 'no page yet'}\n"
        f"Suggested URL: {kw.suggested_url or 'N/A'}\n\n"
        "Apply the FLOW framework (Find → Leverage → Optimize → Win) to this keyword. "
        "Identify which FLOW stage applies based on the data. "
        "Give 4-6 specific, actionable steps. Be concrete — name exact on-page elements, "
        "content additions, or links to build. Output in Markdown."
    )
    return StrategyResult(skill="seo-flow", output=_run_skill("seo-flow", openai_key, msg, timeout=120))


@router.post("/competitor-page", response_model=StrategyResult)
def run_competitor_page(
    body: CompetitorPageRequest,
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    openai_key = get_user_secret("openai", current_user.id, db)
    if body.competitor_url not in context.config.competitors:
        raise HTTPException(
            400,
            "Competitor URL not found in project config. Add it in your project settings first.",
        )

    msg = (
        f"Our product: {context.config.business_name} ({context.config.business_type})\n"
        f"Our website: {context.config.website}\n"
        f"Target audience: {context.config.target_audience}\n"
        f"Tone of voice: {context.config.tone_of_voice}\n"
        f"Our SEO goals: {', '.join(context.config.seo_goals)}\n\n"
        f"Competitor: {body.competitor_url}\n\n"
        "Generate a full SEO-optimized comparison page. Include:\n"
        "1. Meta title + meta description (target keyword: '[our brand] vs [competitor name]')\n"
        "2. H1 + intro section (150-200 words)\n"
        "3. Feature comparison table (10+ features, honest assessment)\n"
        "4. Pros and cons for each product\n"
        "5. Verdict section with recommendation\n"
        "6. FAQ section (5 questions optimized for 'People Also Ask')\n"
        "7. CTA section\n"
        "Output the full page in Markdown, ready to copy into WordPress."
    )
    return StrategyResult(
        skill="seo-competitor-pages",
        output=_run_skill("seo-competitor-pages", openai_key, msg),
    )
