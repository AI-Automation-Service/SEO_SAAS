"""
content-rewriter: rewrites flagged paragraphs from a PageChange.

Triggered when plagiarism_status = "flagged". Rewrites only the paragraphs
that exceeded the similarity threshold — not the full article. Updates
the existing PageChange in place and re-runs the plagiarism check.
"""

import json
import re
import time
from typing import TYPE_CHECKING

from agents.base import SkillAgent, _estimate_cost
from core.db.models import AIHistory

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from core.db.models import PageChange


def _log_call(
    db: "Session",
    user_id: int,
    project_name: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    duration_ms: int,
    change_id: int,
    article_job_id: str | None,
) -> None:
    try:
        db.add(AIHistory(
            user_id=user_id,
            project_name=project_name,
            agent_name="content-rewriter",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            duration_ms=duration_ms,
            change_id=change_id,
            article_job_id=article_job_id,
        ))
        db.commit()
    except Exception:
        pass


def _split_paragraphs(text: str) -> list[str]:
    """Split content into paragraph blocks."""
    return [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]


def _identify_flagged_indices(content: str, plag_report: dict | None) -> list[int]:
    """
    Return 0-based paragraph indices that are flagged as similar.
    Falls back to all paragraphs if no specific report is available.
    """
    if not plag_report:
        # No per-paragraph data — rewrite paragraphs 1–5 (introduction body)
        paragraphs = _split_paragraphs(content)
        return list(range(1, min(6, len(paragraphs))))

    flagged_indices = plag_report.get("flagged_paragraph_indices", [])
    if flagged_indices:
        return [int(i) for i in flagged_indices]

    # Copyscape returned match URLs but no paragraph indices
    paragraphs = _split_paragraphs(content)
    return list(range(1, min(6, len(paragraphs))))


def rewrite_flagged_paragraphs(
    record: "PageChange",
    openai_key: str,
    db: "Session",
    article_job_id: str | None = None,
) -> "PageChange":
    """
    Rewrite flagged paragraphs in a PageChange and update it in place.
    Returns the updated record.
    """
    from api.routers.article import _check_plagiarism

    content = record.new_content
    plag_report = record.plagiarism_report
    paragraphs = _split_paragraphs(content)
    flagged = _identify_flagged_indices(content, plag_report)

    if not flagged or not paragraphs:
        return record

    rewrite_prompt = (
        "You are a professional content rewriter specializing in SEO articles. "
        "Rewrite the following paragraph to:\n"
        "1. Express the same information in completely original language\n"
        "2. Maintain SEO intent and keyword relevance\n"
        "3. Sound natural and authoritative — not like an AI\n"
        "4. Keep approximately the same length\n\n"
        "BANNED WORDS: delve into, tapestry, it's worth noting, furthermore, leverage, utilize, "
        "game-changer, navigate, shed light, revolutionize.\n\n"
        "Return ONLY the rewritten paragraph. No preamble, no explanation.\n\n"
    )

    model = "gpt-4o"
    t0 = time.monotonic()

    for idx in flagged:
        if idx >= len(paragraphs):
            continue
        original_para = paragraphs[idx]
        if len(original_para) < 50:
            continue

        msg = rewrite_prompt + f"Paragraph to rewrite:\n{original_para}"
        try:
            rewritten = SkillAgent("copywriting", openai_key, model=model).run(msg, timeout=60)
            paragraphs[idx] = rewritten.strip() or original_para
        except Exception:
            pass  # keep original paragraph on failure

    duration_ms = int((time.monotonic() - t0) * 1000)
    new_content = "\n\n".join(paragraphs)

    in_toks = sum(len(p) for p in paragraphs) // 4
    out_toks = len(new_content) // 4
    cost = _estimate_cost(model, in_toks * len(flagged), out_toks)
    _log_call(db, record.user_id, record.project_name, model,
              in_toks * len(flagged), out_toks, cost, duration_ms,
              record.id, article_job_id)

    # Update the record in place
    record.new_content = new_content
    record.plagiarism_status = "rewritten"

    # Re-run plagiarism check after rewrite
    new_plag = _check_plagiarism(new_content, db, record.user_id)
    record.plagiarism_flag = new_plag["flag"]
    record.plagiarism_score = new_plag.get("score")
    record.plagiarism_status = new_plag["status"] if new_plag["status"] != "skipped" else "rewritten"
    if new_plag.get("report"):
        record.plagiarism_report = {"results": new_plag["report"], "after_rewrite": True}

    db.commit()
    db.refresh(record)
    return record
