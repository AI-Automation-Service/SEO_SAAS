"""
seo-article-writer two-phase pipeline.

Phase 1: outline + first half (~950 words).
Phase 2: receives Phase 1 JSON, completes the article (~1050 words).
Result → PageChange(action_type=new_draft, platform=wordpress) in the Change Queue.
Plagiarism check runs after Phase 2 if a Copyscape key is available.
"""

import json
import re
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from agents.base import SkillAgent
from api.dependencies import get_current_user, get_db, get_project_context
from api.routers.identity.api_keys import get_user_secret
from api.routers.content.improve import _knowledge_block
from api.utils.knowledge import fetch_knowledge
from core.db.models import AIHistory, PageChange, User
from core.models.context import ProjectContext
from shared.exceptions import SecretNotFoundError

router = APIRouter(prefix="/projects/{name}/article", tags=["article"])

# Anti-AI phrase list — applied to both phases
_BANNED_PHRASES = [
    "delve into", "tapestry", "it's worth noting", "furthermore", "in conclusion, it's clear",
    "navigate", "in the realm of", "at the end of the day", "game-changer", "dive deep",
    "shed light", "in today's fast-paced", "revolutionize", "leverage", "utilize",
]

_ANTI_AI_RULE = (
    "BANNED WORDS/PHRASES — never use any of these: "
    + ", ".join(f'"{p}"' for p in _BANNED_PHRASES)
    + ". Write like a knowledgeable human, not an AI assistant."
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _strip_placeholders(text: str, business_name: str) -> str:
    """Replace common GPT placeholder patterns with real values or remove them."""
    safe_name = business_name.strip() if business_name else ""
    # Replace bracket-wrapped placeholders
    text = re.sub(r'\[Your Business Name\]', safe_name or "us", text, flags=re.IGNORECASE)
    text = re.sub(r'\[Author Name\]', "", text, flags=re.IGNORECASE)
    text = re.sub(r'\[Company Name\]', safe_name or "us", text, flags=re.IGNORECASE)
    text = re.sub(r'\[[^\]]{1,60}\]', "", text)  # any remaining [placeholder]
    # Replace bare (no brackets) known placeholder strings
    if safe_name:
        text = re.sub(r'\bYour Business Name\b', safe_name, text, flags=re.IGNORECASE)
    # Remove stray "By John Doe" / generic author lines GPT sometimes adds
    text = re.sub(r'\nBy John Doe[^\n]*\n', '\n', text)
    text = re.sub(r'\nBy \[?[^\n]{0,40}\]? · Last updated:[^\n]*\n', '\n', text)
    return text


def _slugify(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug).strip("-")
    return slug[:80]


def _word_count(text: str) -> int:
    return len(text.split())


def _project_context_block(ctx: ProjectContext) -> str:
    cfg = ctx.config
    return (
        f"Business: {cfg.business_name}\n"
        f"Type: {cfg.business_type}\n"
        f"Country: {cfg.country}\n"
        f"Language: {cfg.language}\n"
        f"Tone of voice: {cfg.tone_of_voice}\n"
        f"Target audience: {cfg.target_audience}\n"
        f"Website: {cfg.website}"
    )


def _log_call(
    db: Session,
    user_id: int,
    project_name: str,
    agent_name: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    duration_ms: int,
    article_job_id: str,
    change_id: int | None = None,
    status: str = "success",
    error_detail: str | None = None,
) -> None:
    try:
        db.add(AIHistory(
            user_id=user_id,
            project_name=project_name,
            agent_name=agent_name,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            duration_ms=duration_ms,
            article_job_id=article_job_id,
            change_id=change_id,
            status=status,
            error_detail=error_detail,
        ))
        db.commit()
    except Exception:
        pass


# ── Plagiarism check ───────────────────────────────────────────────────────────

def _check_plagiarism(article_text: str, db: Session, user_id: int) -> dict:
    """
    Check article against Copyscape. Returns plagiarism result dict.
    Falls back to skipped if no key is available.
    """
    import os
    import httpx

    # Try subscriber key first, then platform key
    copyscape_user = None
    copyscape_key = None
    try:
        copyscape_user = get_user_secret("copyscape_user", user_id, db)
        copyscape_key = get_user_secret("copyscape_key", user_id, db)
    except Exception:
        copyscape_user = os.environ.get("COPYSCAPE_USER")
        copyscape_key = os.environ.get("COPYSCAPE_KEY")

    if not copyscape_user or not copyscape_key:
        return {
            "status": "skipped",
            "flag": False,
            "score": None,
            "report": None,
        }

    try:
        resp = httpx.post(
            "https://www.copyscape.com/api/",
            data={
                "u": copyscape_user,
                "k": copyscape_key,
                "o": "csearch",
                "e": "UTF-8",
                "c": "10",
                "t": article_text[:25000],
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}

        count = int(data.get("count", 0))
        if count == 0:
            return {"status": "clean", "flag": False, "score": 0.0, "report": None}

        results = data.get("result", [])
        if isinstance(results, dict):
            results = [results]

        max_pct = max(float(r.get("percentmatched", 0)) for r in results) if results else 0.0
        report = [
            {"url": r.get("url"), "percent": float(r.get("percentmatched", 0))}
            for r in results
        ]

        if max_pct >= 20:
            plag_status = "flagged"
        else:
            plag_status = "clean"

        return {
            "status": plag_status,
            "flag": max_pct >= 20,
            "score": max_pct,
            "report": report,
        }
    except Exception as e:
        # If Copyscape fails, skip gracefully
        return {"status": "skipped", "flag": False, "score": None, "report": None}


# ── Request / Response schemas ─────────────────────────────────────────────────

class GenerateArticleRequest(BaseModel):
    keyword: str
    cluster_name: str
    intent: str = "informational"   # informational / commercial / transactional
    ymyl: bool = False
    target_word_count: int = 2100


class ArticleOut(BaseModel):
    change_id: int
    article_job_id: str
    keyword: str
    content_html: str = ""
    draft_title: str
    draft_slug: str
    draft_word_count: int
    plagiarism_status: str
    plagiarism_score: Optional[float] = None
    plagiarism_flag: bool = False
    content_preview: str = ""
    status: str


# ── Phase prompts ──────────────────────────────────────────────────────────────

def _phase1_message(
    keyword: str,
    intent: str,
    ymyl: bool,
    business_block: str,
    knowledge_block: str,
    target_wc: int,
) -> str:
    half = target_wc // 2
    return f"""You are running PHASE 1 of a two-phase article writing task.

## Primary Keyword
{keyword}

## Business Context
{business_block}

{f"## Business Knowledge\\n{knowledge_block}" if knowledge_block else ""}

## Intent
{intent}

## YMYL
{"Yes — apply extra scrutiny: every factual claim must be sourced, include disclaimers where relevant" if ymyl else "No"}

## {_ANTI_AI_RULE}

## Your Task (Phase 1)
Produce the FIRST HALF of a {target_wc}-word SEO article.
HARD REQUIREMENT: content_phase1 MUST contain at least {half} words. Do not stop writing until you reach {half} words.

Output a JSON object with EXACTLY these keys:
{{
  "meta_title": "50-60 char meta title containing primary keyword",
  "meta_description": "140-160 char meta description",
  "slug": "url-slug-lowercase-hyphens",
  "h1": "Article headline (matches meta title closely)",
  "schema_type": "Article|BlogPosting|NewsArticle",
  "sections_outline": ["Section heading text", "Section heading text", ...],
  "content_phase1": "Introduction (100-150 words) + EXACTLY 4 H2 sections each 250-300 words. Total MUST exceed {half} words.",
  "word_count_phase1": <integer count of words in content_phase1>,
  "sections_remaining": ["Section heading text", "Section heading text", "FAQ", "Conclusion"]
}}

Rules for content_phase1:
- Write EXACTLY 4 H2 body sections — not 2, not 3, exactly 4
- Each H2 section MUST be 250-300 words: write 4-5 paragraphs with specific details, examples, and actionable advice
- Do NOT move to the next section until the current one is at least 250 words
- H1 as # heading; H2 as ## heading — NEVER "## H2: Title", just "## Title"
- sections_outline and sections_remaining must be plain heading text — no "H2:", "H3:", or any prefix
- First paragraph of each section: 50-80 word direct answer (AEO/AI Overview target)
- Self-check before submitting: count the words in content_phase1. If under {half}, expand the shortest sections until you reach {half}.
- NEVER output bracket placeholders like [Author Name], [Your Business Name], [date] — use real values from Business Context
- {_ANTI_AI_RULE}
"""


def _phase2_message(
    keyword: str,
    business_block: str,
    business_name: str,
    phase1: dict,
    target_wc: int,
) -> str:
    # Measure Phase 1 content directly — don't trust GPT's self-reported count
    actual_p1_wc = _word_count(phase1.get("content_phase1", ""))
    remaining_wc = max(target_wc - actual_p1_wc, target_wc // 2)
    sections = phase1.get("sections_remaining", [])
    # Only pass the tail of Phase 1 for continuity — passing the full content burns
    # output-token budget and results in GPT-4o producing far less Phase 2 content.
    p1_tail = (phase1.get("content_phase1", "") or "")[-600:]
    return f"""You are running PHASE 2 of a two-phase article writing task.

## Primary Keyword
{keyword}

## Business Context
{business_block}

## Phase 1 Summary
- H1: {phase1.get("h1")}
- Phase 1 covered: {", ".join(phase1.get("sections_outline", [])[:4])}
- Word count so far: {phase1.get("word_count_phase1", 0)} words
- Sections to complete now: {", ".join(sections)}

## End of Phase 1 (last lines — DO NOT repeat, continue naturally from here)
...{p1_tail}

## {_ANTI_AI_RULE}

## Your Task (Phase 2)
Write the REMAINING content to complete the article.
HARD REQUIREMENT: content_phase2 MUST contain at least {remaining_wc} words. Do not stop writing until you reach {remaining_wc} words.

H2 body sections to write ({len(sections) - 2} sections):
{chr(10).join(f"- {s}" for s in sections if s not in ("FAQ", "Conclusion"))}

Each H2 section above MUST be 250-300 words (4-5 paragraphs). Do NOT move to the next section until the current one is at least 250 words.

Then write:
- FAQ section: 5 H3 questions with 60-80 word answers each (total ~350 words)
- Conclusion: 75-100 words + CTA that mentions "{business_name}" by name (do NOT write "Your Business Name" or any placeholder)
- JSON-LD schema snippet for {phase1.get("schema_type", "Article")}

Output a JSON object with EXACTLY these keys:
{{
  "content_phase2": "Full Markdown of all remaining sections. MUST exceed {remaining_wc} words.",
  "word_count_phase2": <integer count of words in content_phase2>,
  "schema_json_ld": "<script type=\\"application/ld+json\\">...</script>"
}}

Rules:
- Continue naturally from where Phase 1 left off — do NOT repeat any Phase 1 content
- NEVER write "## H2: Title" or "### H3: Title" — write "## Title" and "### Title" only
- NEVER output bracket placeholders like [Author Name], [Your Business Name], [date] — use real values from Business Context
- Self-check before submitting: if content_phase2 is under {remaining_wc} words, expand the shortest sections
- FAQ: questions must be natural reader follow-ups — never invent facts not in the article
- {_ANTI_AI_RULE}
"""


# ── Endpoint ───────────────────────────────────────────────────────────────────

@router.post("/generate", response_model=ArticleOut)
def generate_article(
    body: GenerateArticleRequest,
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    import time

    openai_key = get_user_secret("openai", current_user.id, db)
    article_job_id = str(uuid.uuid4())
    business_block = _project_context_block(context)
    business_name = (context.config.business_name or "").strip()
    knowledge_block = _knowledge_block(db, current_user.id, context.name)

    # ── Phase 1 ────────────────────────────────────────────────────────────────
    p1_msg = _phase1_message(
        body.keyword, body.intent, body.ymyl,
        business_block, knowledge_block, body.target_word_count,
    )

    t0 = time.monotonic()
    try:
        raw_p1 = SkillAgent("seo-article-writer", openai_key, model="gpt-4o").run(
            p1_msg, timeout=240, json_mode=True, max_tokens=4096
        )
    except Exception as e:
        raise HTTPException(502, f"Article writer Phase 1 failed: {e}")
    p1_ms = int((time.monotonic() - t0) * 1000)

    try:
        phase1 = json.loads(raw_p1)
    except json.JSONDecodeError:
        raise HTTPException(500, "Article writer Phase 1 returned invalid JSON.")

    # Rough token estimate for logging (100 chars ≈ 25 tokens)
    p1_in = len(p1_msg) // 4
    p1_out = len(raw_p1) // 4
    p1_cost = round(p1_in / 1000 * 0.0025 + p1_out / 1000 * 0.010, 6)
    _log_call(db, current_user.id, context.name, "seo-article-writer-p1", "gpt-4o",
              p1_in, p1_out, p1_cost, p1_ms, article_job_id)

    # ── Phase 2 ────────────────────────────────────────────────────────────────
    p2_msg = _phase2_message(body.keyword, business_block, business_name, phase1, body.target_word_count)

    t0 = time.monotonic()
    try:
        raw_p2 = SkillAgent("seo-article-writer", openai_key, model="gpt-4o").run(
            p2_msg, timeout=240, json_mode=True, max_tokens=4096
        )
    except Exception as e:
        raise HTTPException(502, f"Article writer Phase 2 failed: {e}")
    p2_ms = int((time.monotonic() - t0) * 1000)

    try:
        phase2 = json.loads(raw_p2)
    except json.JSONDecodeError:
        raise HTTPException(500, "Article writer Phase 2 returned invalid JSON.")

    p2_in = len(p2_msg) // 4
    p2_out = len(raw_p2) // 4
    p2_cost = round(p2_in / 1000 * 0.0025 + p2_out / 1000 * 0.010, 6)
    _log_call(db, current_user.id, context.name, "seo-article-writer-p2", "gpt-4o",
              p2_in, p2_out, p2_cost, p2_ms, article_job_id)

    # ── Assemble final article ─────────────────────────────────────────────────
    p1_content = phase1.get("content_phase1", "")
    p2_content = phase2.get("content_phase2", "")
    schema_block = phase2.get("schema_json_ld", "")

    full_article = "\n\n".join(filter(None, [p1_content, p2_content, schema_block]))
    full_article = _strip_placeholders(full_article, business_name)
    total_wc = _word_count(full_article)

    draft_title = phase1.get("h1") or phase1.get("meta_title") or body.keyword.title()
    # Always derive slug from the raw keyword — GPT drops stop words ("in", "of", …)
    draft_slug = _slugify(body.keyword)

    # ── Plagiarism check ───────────────────────────────────────────────────────
    plag = _check_plagiarism(full_article, db, current_user.id)
    plagiarism_status = plag["status"]
    plagiarism_flag = plag["flag"]
    plagiarism_score = plag.get("score")
    plagiarism_report = plag.get("report")

    # ── Create PageChange (new_draft) ──────────────────────────────────────────
    change_summary = (
        f"New article draft: \"{draft_title}\" "
        f"({total_wc} words, {body.intent}, plagiarism: {plagiarism_status})"
    )
    if plagiarism_flag and plagiarism_score:
        change_summary += f" — similarity score: {plagiarism_score:.0f}%"

    record = PageChange(
        user_id=current_user.id,
        project_name=context.name,
        action_type="new_draft",
        platform="wordpress",
        source_agent="seo-article-writer",
        cluster_name=body.cluster_name,
        wp_post_id=0,          # no existing post — will be set after WP create
        wp_post_url="",        # filled in after publish
        wp_post_type="post",
        original_content="",   # no original — this is a new draft
        new_content=full_article,
        change_summary=change_summary,
        changes_made=["article_writer: new draft created via two-phase pipeline"],
        statistics={
            "word_count": total_wc,
            "phase1_words": phase1.get("word_count_phase1", 0),
            "phase2_words": phase2.get("word_count_phase2", 0),
        },
        draft_title=draft_title,
        draft_slug=draft_slug,
        draft_word_count=total_wc,
        plagiarism_flag=plagiarism_flag,
        plagiarism_score=plagiarism_score,
        plagiarism_report={"results": plagiarism_report} if plagiarism_report else None,
        plagiarism_status=plagiarism_status,
        status="pending",
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # Link AI history entries to the change
    try:
        db.query(AIHistory).filter(
            AIHistory.article_job_id == article_job_id
        ).update({"change_id": record.id})
        db.commit()
    except Exception:
        pass

    # Trigger content-rewriter for ALL flagged content — both 20–40% and above 40% (§24)
    original_plagiarism_score = plagiarism_score
    if plagiarism_flag and plagiarism_score is not None:
        try:
            from agents.content_rewriter import rewrite_flagged_paragraphs
            record = rewrite_flagged_paragraphs(record, openai_key, db, article_job_id)
        except Exception:
            pass  # rewrite failure is non-fatal — article still enters queue

    # For originally >40% scores: keep autopilot blocked even after a successful rewrite (§24)
    if plagiarism_flag and original_plagiarism_score is not None and original_plagiarism_score > 40:
        record.plagiarism_status = "flagged"
        db.commit()

    db.refresh(record)
    import re as _re
    preview_text = _re.sub(r'<[^>]+>', ' ', record.new_content or "").strip()
    return ArticleOut(
        change_id=record.id,
        article_job_id=article_job_id,
        content_html=record.new_content or "",
        keyword=body.keyword,
        draft_title=record.draft_title or draft_title,
        draft_slug=record.draft_slug or draft_slug,
        draft_word_count=record.draft_word_count or total_wc,
        plagiarism_status=record.plagiarism_status,
        plagiarism_score=record.plagiarism_score,
        plagiarism_flag=record.plagiarism_flag,
        content_preview=preview_text,
        status=record.status,
    )
