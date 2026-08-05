import json
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

import markdown as md
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from agents.base import SkillAgent
from api.dependencies import get_current_user, get_db, get_project_context, get_secret_manager
from api.routers.api_keys import get_user_secret
from api.utils.knowledge import fetch_knowledge
from core.db.models import Keyword, SitePage, StrategyOutput, User
from core.models.context import ProjectContext
from core.secrets import SecretManager
from integrations.base import IntegrationError
from integrations.cms.base import PostDraft
from integrations.cms.wordpress import WordPressAdapter
from shared.exceptions import SecretNotFoundError

router = APIRouter(prefix="/projects/{name}/strategy", tags=["strategy"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _project_block(ctx: ProjectContext) -> str:
    cfg = ctx.config
    lines = [
        f"Business: {cfg.business_name} ({cfg.business_type})",
        f"Website: {cfg.website}",
        f"Country: {cfg.country}, Language: {cfg.language}",
    ]
    if cfg.business_location:
        lines.append(f"Location: {cfg.business_location}")
    lines += [
        f"Tone of voice: {cfg.tone_of_voice}",
        f"Target audience: {cfg.target_audience}",
        f"Primary conversion goal: {cfg.primary_conversion or 'not specified'}",
        f"SEO plugin: {cfg.seo_plugin or 'not specified'}",
        f"SEO goals: {', '.join(cfg.seo_goals)}",
        f"Business goals: {', '.join(cfg.business_goals)}",
        f"Competitors: {', '.join(cfg.competitors) if cfg.competitors else 'None specified'}",
    ]
    return "\n".join(lines)


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


def _knowledge_block(db: Session, user_id: int, project_name: str) -> str:
    kb = fetch_knowledge(db, user_id, project_name)
    if not kb:
        return ""
    parts = []
    if kb.about:
        parts.append(f"About the Business:\n{kb.about.strip()}")
    if kb.products_services:
        parts.append(f"Products & Services:\n{kb.products_services.strip()}")
    if kb.target_audience:
        parts.append(f"Target Audience:\n{kb.target_audience.strip()}")
    if kb.brand_voice:
        parts.append(f"Brand Voice & Tone:\n{kb.brand_voice.strip()}")
    if kb.competitors_notes:
        parts.append(f"Competitor Notes:\n{kb.competitors_notes.strip()}")
    if kb.seo_context:
        parts.append(f"SEO Context:\n{kb.seo_context.strip()}")
    if not parts:
        return ""
    return "\n\n=== KNOWLEDGE BASE ===\n" + "\n\n".join(parts) + "\n=== END KNOWLEDGE BASE ==="


def _get_keywords(db: Session, user_id: int, project_name: str) -> list:
    return (
        db.query(Keyword)
        .filter(Keyword.user_id == user_id, Keyword.project_name == project_name)
        .all()
    )


def _save_output(db: Session, user_id: int, project_name: str, strategy_type: str, output: str) -> None:
    row = (
        db.query(StrategyOutput)
        .filter(
            StrategyOutput.user_id == user_id,
            StrategyOutput.project_name == project_name,
            StrategyOutput.strategy_type == strategy_type,
        )
        .first()
    )
    if row:
        row.output = output
        row.updated_at = datetime.utcnow()
    else:
        db.add(StrategyOutput(
            user_id=user_id,
            project_name=project_name,
            strategy_type=strategy_type,
            output=output,
        ))
    db.commit()


# ── Schemas ───────────────────────────────────────────────────────────────────

class StrategyResult(BaseModel):
    skill: str
    output: str
    execution_plan: Optional[dict] = None


class CompetitorPageRequest(BaseModel):
    competitor_url: str


class UpdateOutputRequest(BaseModel):
    output: str


# ── Saved output endpoints ────────────────────────────────────────────────────

@router.get("/saved")
def get_saved_outputs(
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    rows = (
        db.query(StrategyOutput)
        .filter(
            StrategyOutput.user_id == current_user.id,
            StrategyOutput.project_name == context.name,
        )
        .all()
    )
    return {r.strategy_type: r.output for r in rows}


@router.put("/saved/{strategy_type}", response_model=StrategyResult)
def update_saved_output(
    strategy_type: str,
    body: UpdateOutputRequest,
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _save_output(db, current_user.id, context.name, strategy_type, body.output)
    return StrategyResult(skill=strategy_type, output=body.output)


@router.delete("/saved/{strategy_type}", status_code=204)
def delete_saved_output(
    strategy_type: str,
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(StrategyOutput).filter(
        StrategyOutput.user_id == current_user.id,
        StrategyOutput.project_name == context.name,
        StrategyOutput.strategy_type == strategy_type,
    ).delete()
    db.commit()


# ── Generation endpoints ──────────────────────────────────────────────────────

def _build_execution_plan_json(
    rows: list,
    ctx: ProjectContext,
    markdown_plan: str,
    openai_key: str,
) -> dict:
    """
    Ask GPT-4o-mini to extract a structured JSON execution plan from the Markdown roadmap.
    Returns the JSON dict; falls back to a minimal stub on failure.
    """
    clusters = {}
    for r in rows:
        if not r.cluster:
            continue
        c = clusters.setdefault(r.cluster, {"hub": None, "spokes": [], "keywords": []})
        c["keywords"].append(r.keyword)
        if r.is_hub:
            c["hub"] = r.keyword
        elif r.existing_url:
            c["spokes"].append(r.existing_url)

    cluster_list = [
        {
            "name": name,
            "hub_keyword": data["hub"] or data["keywords"][0],
            "keyword_count": len(data["keywords"]),
        }
        for name, data in clusters.items()
    ]

    prompt = (
        "You are a structured data extractor. Given the 12-month SEO plan below, "
        "produce a JSON execution plan. Output ONLY valid JSON, no markdown wrapper.\n\n"
        "Required structure:\n"
        "{\n"
        '  "phases": [\n'
        '    {"name": "foundation", "weeks": "1-4", "focus": "...", "cluster_targets": ["cluster1"]},\n'
        '    {"name": "expansion", "weeks": "5-12", "focus": "...", "cluster_targets": []},\n'
        '    {"name": "scale", "weeks": "13-24", "focus": "...", "cluster_targets": []},\n'
        '    {"name": "authority", "weeks": "25-52", "focus": "...", "cluster_targets": []}\n'
        "  ],\n"
        '  "content_calendar": [\n'
        '    {"cluster": "cluster_name", "action": "new_article|improve", "phase": "foundation", '
        '"priority": "P0|P1|P2|P3", "target_keyword": "..."}\n'
        "  ],\n"
        '  "improvement_queue": [\n'
        '    {"cluster": "cluster_name", "priority": "P0|P1|P2|P3", "reason": "..."}\n'
        "  ],\n"
        '  "kpi_targets": {"3_month": {}, "6_month": {}, "12_month": {}}\n'
        "}\n\n"
        f"Available clusters: {cluster_list}\n\n"
        f"SEO Plan (Markdown):\n{markdown_plan[:4000]}"
    )

    try:
        raw = SkillAgent("seo-plan", openai_key, model="gpt-4o-mini").run(
            prompt, timeout=90, json_mode=True
        )
        return json.loads(raw)
    except Exception:
        # Minimal fallback so the plan always has a machine-readable form
        return {
            "phases": [
                {"name": "foundation", "weeks": "1-4", "focus": "Quick wins and pillar content", "cluster_targets": []},
                {"name": "expansion", "weeks": "5-12", "focus": "Spoke content and internal linking", "cluster_targets": []},
                {"name": "scale", "weeks": "13-24", "focus": "Content depth and authority signals", "cluster_targets": []},
                {"name": "authority", "weeks": "25-52", "focus": "Link building and brand authority", "cluster_targets": []},
            ],
            "content_calendar": [],
            "improvement_queue": [
                {"cluster": name, "priority": "P1", "reason": "Pending plan analysis"}
                for name in list(clusters.keys())[:10]
            ],
            "kpi_targets": {},
        }


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
    knowledge = _knowledge_block(db, current_user.id, context.name)
    msg = (
        f"{_project_block(context)}"
        f"{knowledge}\n\n"
        f"Keyword data: {len(rows)} keywords across {cluster_count} clusters.\n\n"
        f"Cluster summary:\n{_cluster_summary(rows)}"
        f"{sitemap}\n\n"
        "Generate a complete 12-month SEO plan with 4 phases (Foundation weeks 1-4, "
        "Expansion weeks 5-12, Scale weeks 13-24, Authority months 7-12). "
        "Include: executive summary, KPI targets table (Baseline/3 Month/6 Month/12 Month), "
        "content priorities per cluster, and phased implementation roadmap. Output in Markdown."
    )
    markdown_output = _run_skill("seo-plan", openai_key, msg)
    _save_output(db, current_user.id, context.name, "plan", markdown_output)

    # Build JSON execution plan from the Markdown roadmap
    execution_plan = _build_execution_plan_json(rows, context, markdown_output, openai_key)
    _save_output(db, current_user.id, context.name, "plan_json", json.dumps(execution_plan))

    # Advance project state to PLANNED
    try:
        from core.state_machine import advance_state
        advance_state(context, "PLANNED")
    except Exception:
        pass

    return StrategyResult(skill="seo-plan", output=markdown_output, execution_plan=execution_plan)


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
    knowledge = _knowledge_block(db, current_user.id, context.name)
    msg = (
        f"{_project_block(context)}"
        f"{knowledge}\n\n"
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
    output = _run_skill("content-strategy", openai_key, msg)
    _save_output(db, current_user.id, context.name, "content", output)
    return StrategyResult(skill="content-strategy", output=output)


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
    knowledge = _knowledge_block(db, current_user.id, context.name)
    msg = (
        f"{_project_block(context)}"
        f"{knowledge}\n\n"
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
    output = _run_skill("site-architecture", openai_key, msg)
    _save_output(db, current_user.id, context.name, "architecture", output)
    return StrategyResult(skill="site-architecture", output=output)


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

    knowledge = _knowledge_block(db, current_user.id, context.name)
    msg = (
        f"Business: {context.config.business_name} ({context.config.business_type})\n"
        f"Website: {context.config.website}"
        f"{knowledge}\n\n"
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


@router.post("/improve-page/{keyword_id}", response_model=StrategyResult)
def run_improve_page(
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
    if not kw.existing_url:
        raise HTTPException(400, "No existing page URL for this keyword.")

    gsc_section = ""
    if kw.position or kw.impressions:
        gsc_section = (
            f"\nGSC Performance:\n"
            f"  Position: {kw.position or 'N/A'}\n"
            f"  Impressions: {kw.impressions or 0}\n"
            f"  Clicks: {kw.clicks or 0}\n"
            f"  CTR: {f'{kw.ctr:.1%}' if kw.ctr else 'N/A'}\n"
        )

    knowledge = _knowledge_block(db, current_user.id, context.name)
    msg = (
        f"Business: {context.config.business_name} ({context.config.business_type})\n"
        f"Website: {context.config.website}\n"
        f"Country: {context.config.country}, Language: {context.config.language}"
        f"{knowledge}\n\n"
        f"Existing page to improve:\n"
        f"  URL: {kw.existing_url}\n"
        f"  Primary keyword: {kw.keyword}\n"
        f"  Page type: {kw.page_type or 'unknown'} (WordPress {kw.page_type or 'page/post'})\n"
        f"  Cluster: {kw.cluster or 'unclustered'} ({'hub page' if kw.is_hub else 'supporting page'})\n"
        f"  Intent: {kw.intent or 'N/A'}, Funnel: {kw.funnel_stage or 'N/A'}\n"
        f"  Status: {kw.status}"
        f"{gsc_section}\n"
        "This page already exists on the site. Do NOT suggest creating a new page.\n\n"
        "Provide a detailed improvement plan covering:\n"
        "1. On-page SEO: title tag, meta description, H1, heading structure — write the exact improved versions\n"
        "2. Content gaps: what sections, topics, or depth is missing based on the keyword and funnel stage\n"
        "3. FAQ block: write 3-5 FAQ questions + answers optimized for People Also Ask (use QAPage schema, not FAQPage)\n"
        "4. Internal links: suggest 3-5 specific pages on the site to link FROM this page (with suggested anchor text)\n"
        "5. External links: suggest 1-2 authoritative external sources to cite\n"
        "6. Schema markup: identify the best schema type for this page and provide the JSON-LD snippet\n"
        "7. Quick wins: if GSC data shows high impressions but low CTR, address title/description first\n\n"
        "Output in Markdown with clear headings. Be specific and actionable."
    )
    return StrategyResult(skill="seo-page", output=_run_skill("seo-page", openai_key, msg, timeout=120))


@router.post("/competitor-page", response_model=StrategyResult)
def run_competitor_page(
    body: CompetitorPageRequest,
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    openai_key = get_user_secret("openai", current_user.id, db)
    cfg = context.config
    knowledge = _knowledge_block(db, current_user.id, context.name)
    msg = (
        f"Our business: {cfg.business_name}\n"
        f"Business type: {cfg.business_type}\n"
        f"Website: {cfg.website}\n"
        f"Country: {cfg.country}, Language: {cfg.language}\n"
        f"Target audience: {cfg.target_audience}\n"
        f"Tone of voice: {cfg.tone_of_voice}\n"
        f"Primary conversion goal: {cfg.primary_conversion or 'lead generation'}\n"
        f"SEO goals: {', '.join(cfg.seo_goals)}\n"
        f"Business goals: {', '.join(cfg.business_goals)}\n"
        f"{knowledge}\n\n"
        f"Competitor website: {body.competitor_url}\n\n"
        "CRITICAL RULES — you must follow these exactly:\n"
        "- NEVER use placeholder text such as [Feature], [Target Audience], $X/mo, Feature 1, "
        "Your Business Name, [specific tool], [date], or any bracketed text.\n"
        "- Use ONLY the real business name, real features, and real information from the context above.\n"
        "- For the competitor, use your knowledge of that company's actual product, pricing, and features.\n"
        "- If you are unsure of a competitor detail, say 'not publicly disclosed' or 'varies by plan' — "
        "never invent a placeholder.\n"
        "- Write in the specified tone of voice. Address the target audience directly.\n\n"
        "Generate a full SEO-optimized comparison page in Markdown. Include:\n"
        "1. Meta title + meta description targeting the keyword '[our brand] vs [competitor name]'\n"
        "2. H1 + intro (150-200 words) — speak to the target audience's real pain points\n"
        "3. Feature comparison table (10+ real features, honest and specific)\n"
        "4. Pros and cons for each — based on real strengths and weaknesses\n"
        "5. Verdict — clear recommendation with reasoning\n"
        "6. FAQ section — 5 questions matching real 'People Also Ask' queries for this comparison\n"
        "7. CTA — aligned with the primary conversion goal\n"
        "Output clean Markdown ready to publish to WordPress."
    )
    output = _run_skill("seo-competitor-pages", openai_key, msg)
    _save_output(db, current_user.id, context.name, f"competitor:{body.competitor_url}", output)
    return StrategyResult(skill="seo-competitor-pages", output=output)


def _competitor_title_and_slug(business_name: str, competitor_url: str) -> tuple[str, str]:
    import re
    host = urlparse(competitor_url).hostname or competitor_url
    host = host.removeprefix("www.")
    competitor_name = host.split(".")[0].replace("-", " ").title()
    title = f"{business_name} vs {competitor_name}"
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return title, slug


class QueueCompetitorOut(BaseModel):
    change_id: int
    draft_title: str
    draft_slug: str
    status: str


@router.post("/queue-competitor", response_model=QueueCompetitorOut)
def queue_competitor_page(
    body: CompetitorPageRequest,
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Queue the saved competitor page as a new_draft PageChange.
    Subscriber approves in the Change Queue, which then pushes it to WordPress as a draft post.
    Replaces the old publish-competitor endpoint (which pushed directly).
    """
    from core.db.models import PageChange

    strategy_type = f"competitor:{body.competitor_url}"
    row = (
        db.query(StrategyOutput)
        .filter(
            StrategyOutput.user_id == current_user.id,
            StrategyOutput.project_name == context.name,
            StrategyOutput.strategy_type == strategy_type,
        )
        .first()
    )
    if not row:
        raise HTTPException(404, "No saved output for this competitor. Generate it first.")

    title, slug = _competitor_title_and_slug(context.config.business_name, body.competitor_url)
    html = md.markdown(row.output, extensions=["tables", "fenced_code"])
    wc = len(row.output.split())

    record = PageChange(
        user_id=current_user.id,
        project_name=context.name,
        action_type="new_draft",
        platform="wordpress",
        source_agent="seo-competitor-pages",
        cluster_name="competitor",
        wp_post_id=0,
        wp_post_url="",
        wp_post_type="page",
        original_content="",
        new_content=html,
        change_summary=f"Competitor comparison page: \"{title}\" ({wc} words)",
        changes_made=["competitor_page: comparison page queued for WordPress draft"],
        draft_title=title,
        draft_slug=slug,
        draft_word_count=wc,
        plagiarism_status="skipped",
        status="pending",
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return QueueCompetitorOut(
        change_id=record.id,
        draft_title=title,
        draft_slug=slug,
        status="pending",
    )


@router.post("/publish-competitor")
def publish_competitor_page(
    body: CompetitorPageRequest,
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    secrets: SecretManager = Depends(get_secret_manager),
):
    """Deprecated: use /queue-competitor instead. Kept for backward compatibility."""
    strategy_type = f"competitor:{body.competitor_url}"
    row = (
        db.query(StrategyOutput)
        .filter(
            StrategyOutput.user_id == current_user.id,
            StrategyOutput.project_name == context.name,
            StrategyOutput.strategy_type == strategy_type,
        )
        .first()
    )
    if not row:
        raise HTTPException(404, "No saved output for this competitor. Generate it first.")

    wp_cfg = context.config.integrations.wordpress
    if not wp_cfg.enabled:
        raise HTTPException(400, "WordPress integration is not enabled.")

    try:
        adapter = WordPressAdapter(
            url=wp_cfg.url,
            username=secrets.get(wp_cfg.username_env),
            password=secrets.get(wp_cfg.password_env),
        )
    except (SecretNotFoundError, Exception) as e:
        raise HTTPException(400, f"WordPress credentials error: {e}")

    html = md.markdown(row.output, extensions=["tables", "fenced_code"])
    title, slug = _competitor_title_and_slug(context.config.business_name, body.competitor_url)

    try:
        result = adapter.create_page(PostDraft(title=title, content=html, slug=slug, status="draft"))
    except IntegrationError as e:
        raise HTTPException(502, str(e))

    return {"id": result.id, "url": result.url, "title": result.title, "status": result.status}
