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

# ── Global style rules — injected once into Phase 1, referenced by name in Phase 2 ──
_GLOBAL_RULES = """
════════════════════════════════════════
GLOBAL RULES — apply to every word you write
════════════════════════════════════════

VOICE & TONE
• Write as a knowledgeable human practitioner — direct, specific, authoritative
• Match the tone of voice from Business Context
• Address the reader as "you" — not "businesses" or "organizations"

SENTENCE & PARAGRAPH VARIETY (required — do not write walls of uniform paragraphs)
• Vary sentence length: mix short punchy sentences (8-15 words) with longer ones (25-35 words)
• Vary paragraph format within each H2 section — use at least 2 of:
    - Short prose paragraphs (2-4 sentences)
    - Bullet list (4-6 items)
    - Numbered steps (when order matters)
    - Comparison table (when comparing options)
    - Bold callout: **Key insight:** followed by 1-2 sentences

E-E-A-T SIGNAL (required in every H2 section — choose one or more)
• A concrete real-world example ("For instance, a manufacturing company in Cairo...")
• A specific statistic with its source placeholder: [Citation: describe source]
• A realistic scenario showing the concept in practice
• A named case study or known industry event (only if genuinely known — do not invent)

STYLE DON'TS
• No AI giveaway phrases: "delve into", "it's worth noting", "in today's fast-paced world",
  "game-changer", "at the end of the day", "in the realm of", "tapestry", "shed light on"
• No corporate clichés: "leverage", "utilize", "synergy", "holistic", "robust", "seamless", "cutting-edge"
• No filler openers: never start a paragraph with "Furthermore,", "Moreover,", "Additionally,"
• No inflated adjectives: "innovative", "transformative", "revolutionary", "groundbreaking"
• No repetitive sentence starters across consecutive paragraphs

CITATIONS
• Do NOT invent URLs — real links are often hallucinated and break trust
• Instead use citation placeholders: [Citation: brief description, e.g. "World Bank data on MENA outsourcing 2024"]
• These will be resolved by the editorial team before publishing

PLACEHOLDERS
• NEVER output bracket content like [Author Name], [Your Business Name], [date]
• Use real values from Business Context — if a value is missing, write around it naturally
"""


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
    website: str,
    target_wc: int,
) -> str:
    half = target_wc // 2
    ymyl_note = (
        "YES — every factual claim must include a citation placeholder. "
        "Add health/legal/financial disclaimers where relevant."
        if ymyl else "No"
    )
    return f"""You are running PHASE 1 of a two-phase SEO article writing pipeline.

{_GLOBAL_RULES}

════════════════════════════════════════
BUSINESS CONTEXT
════════════════════════════════════════
{business_block}
{f"{chr(10)}Brand & Strategy Notes:{chr(10)}{knowledge_block}" if knowledge_block else ""}

════════════════════════════════════════
SEO SPECIFICATION
════════════════════════════════════════
Primary keyword : {keyword}
Search intent   : {intent}
YMYL            : {ymyl_note}

Semantic coverage — weave these naturally throughout the article (do not list them):
• 3-5 semantic variations of the primary keyword
• 3-5 related entities (people, organisations, concepts, tools) relevant to the topic
• 2-3 "People Also Ask" questions Google shows for this keyword (answer them inside the article body)

════════════════════════════════════════
ARTICLE STRUCTURE — Phase 1 (first {half}+ words)
════════════════════════════════════════
Write the FIRST HALF of a {target_wc}-word article. Produce exactly 4 H2 sections.

STEP 1 — Introduction (100-150 words)
• Hook sentence that addresses the reader's primary problem
• 60-80 word direct answer to the primary keyword query (AI Overview / AEO target)
• Brief preview of what the article covers
• End the introduction block with: <!-- Image: [describe the ideal image for this topic] -->

STEP 2 — H2 Section 1 (250-400 words)
• Open with a 60-80 word direct answer paragraph
• Follow with 3-4 paragraphs OR a mix of prose + bullet list + example
• Include 1 E-E-A-T signal (concrete example, statistic with [Citation: …], or real scenario)
• Include 1 citation placeholder: [Citation: describe source needed]
• Include 1 internal link: [{website}/relevant-page/](descriptive anchor text)

STEP 3 — H2 Section 2 (250-400 words)
• Same depth requirements as Section 1
• End the section with: <!-- Image: [describe supporting image] -->
• Include 1 E-E-A-T signal, 1 citation placeholder

STEP 4 — H2 Section 3 (250-400 words)
• Use a different content format than Section 2 (e.g. numbered steps or comparison table)
• Include 1 E-E-A-T signal, 1 citation placeholder

STEP 5 — H2 Section 4 (250-400 words)
• Include 1 E-E-A-T signal, 1 citation placeholder

Formatting rules:
• H1 as # heading; H2 as ## heading — write "## Title", never "## H2: Title"
• sections_outline and sections_remaining: plain heading text — no "H2:", "H3:", or numbering prefix

════════════════════════════════════════
INTERNAL SEO SELF-CHECK (do not output — verify before submitting)
════════════════════════════════════════
✓ Primary keyword appears in H1
✓ Primary keyword appears in meta_title and meta_description
✓ Primary keyword appears in the first paragraph of the introduction
✓ Semantic variations used naturally (not stuffed)
✓ Each H2 section has at least one E-E-A-T signal
✓ At least 2 citation placeholders present
✓ At least 1 internal link present
✓ Image placeholder after introduction
✓ No banned phrases, no placeholder brackets, no invented URLs

════════════════════════════════════════
OUTPUT FORMAT
════════════════════════════════════════
Return a single JSON object with EXACTLY these keys — no extra keys, no markdown fences:
{{
  "meta_title": "50-60 char meta title containing primary keyword",
  "meta_description": "140-160 char meta description — keyword + clear value proposition",
  "slug": "url-slug-lowercase-hyphens",
  "h1": "Article headline — contains primary keyword, matches meta_title closely",
  "schema_type": "Article or BlogPosting or NewsArticle",
  "sections_outline": ["Section 1 heading", "Section 2 heading", "Section 3 heading", "Section 4 heading"],
  "content_phase1": "<full Markdown content — introduction + 4 H2 sections — target {half}+ words>",
  "sections_remaining": ["Section 5 heading", "Section 6 heading", "FAQ", "Conclusion"]
}}
"""


def _phase2_message(
    keyword: str,
    business_block: str,
    business_name: str,
    website: str,
    phase1: dict,
    target_wc: int,
) -> str:
    actual_p1_wc = _word_count(phase1.get("content_phase1", ""))
    remaining_wc = max(target_wc - actual_p1_wc, target_wc // 2)
    sections = phase1.get("sections_remaining", [])
    body_sections = [s for s in sections if s not in ("FAQ", "Conclusion")]
    p1_tail = (phase1.get("content_phase1", "") or "")[-600:]
    section_steps = "".join(
        f"STEP {i + 1} — H2: {s} (250-400 words)\n"
        f"• Open with a direct answer paragraph (60-80 words)\n"
        f"• Include 1 E-E-A-T signal (concrete example, statistic, or real scenario)\n"
        f"• Include 1 citation placeholder: [Citation: describe source needed]\n"
        f"• Mix content formats (prose + list or prose + table) — avoid uniform paragraphs\n\n"
        for i, s in enumerate(body_sections)
    )
    return f"""You are running PHASE 2 of a two-phase SEO article writing pipeline.

The GLOBAL RULES from Phase 1 apply in full — voice, variety, E-E-A-T, citation placeholders, no banned phrases, no invented URLs, no bracket placeholders.

════════════════════════════════════════
BUSINESS CONTEXT
════════════════════════════════════════
{business_block}

════════════════════════════════════════
PHASE 1 HANDOFF
════════════════════════════════════════
Primary keyword : {keyword}
H1              : {phase1.get("h1")}
Phase 1 covered : {", ".join(phase1.get("sections_outline", [])[:4])}
Phase 1 length  : {actual_p1_wc} words (measured by backend)
Still to write  : {", ".join(sections)}

Continuation point — pick up naturally from here, do NOT repeat:
…{p1_tail}

════════════════════════════════════════
ARTICLE STRUCTURE — Phase 2 (remaining {remaining_wc}+ words)
════════════════════════════════════════
{section_steps}STEP {len(body_sections) + 1} — FAQ Section (~350 words)
• Write exactly 5 H3 questions that readers genuinely ask about this topic on Google
• Each answer: 60-80 words — direct, specific, no filler
• Use only facts already established in the article — do not introduce new claims here

STEP {len(body_sections) + 2} — Conclusion (100-150 words)
• Summarise 3 key takeaways in 1-2 sentences each
• Close with a CTA that names "{business_name}" specifically
• Do NOT write "Your Business Name" or any placeholder

════════════════════════════════════════
INTERNAL SEO SELF-CHECK (do not output — verify before submitting)
════════════════════════════════════════
✓ Primary keyword "{keyword}" appears naturally in at least 2 Phase 2 sections
✓ Each H2 has at least 1 E-E-A-T signal
✓ At least 2 more citation placeholders present
✓ 1-2 internal links to {website} included
✓ FAQ answers do not contradict Phase 1 content
✓ CTA names the real business, not a placeholder
✓ No heading prefixes (H2: / H3:), no invented URLs, no banned phrases

════════════════════════════════════════
OUTPUT FORMAT
════════════════════════════════════════
Return a single JSON object with EXACTLY these keys — no extra keys, no markdown fences:
{{
  "content_phase2": "<full Markdown — all remaining H2 sections + FAQ + Conclusion — target {remaining_wc}+ words>",
  "schema_json_ld": "<script type=\\"application/ld+json\\">{{...valid JSON-LD for {phase1.get("schema_type", "Article")}...}}</script>"
}}
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
    website = (context.config.website or "").rstrip("/")
    knowledge_block = _knowledge_block(db, current_user.id, context.name)

    # ── Phase 1 ────────────────────────────────────────────────────────────────
    p1_msg = _phase1_message(
        body.keyword, body.intent, body.ymyl,
        business_block, knowledge_block, website, body.target_word_count,
    )

    t0 = time.monotonic()
    try:
        raw_p1 = SkillAgent("seo-article-writer", openai_key, model="gpt-4o").run(
            p1_msg, timeout=300, json_mode=True, max_tokens=6000
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
    p2_msg = _phase2_message(body.keyword, business_block, business_name, website, phase1, body.target_word_count)

    t0 = time.monotonic()
    try:
        raw_p2 = SkillAgent("seo-article-writer", openai_key, model="gpt-4o").run(
            p2_msg, timeout=300, json_mode=True, max_tokens=6000
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
            "phase1_words": actual_p1_wc,
            "phase2_words": _word_count(p2_content),
            "meta_title": (phase1.get("meta_title") or "").strip(),
            "meta_description": (phase1.get("meta_description") or "").strip(),
            "focus_keyword": body.keyword,
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
