"""
Subscriber feedback endpoints.

POST /projects/{name}/improve/feedback/{change_id}  — record approve/reject + comment
GET  /projects/{name}/improve/preferences           — get distilled preference rules
POST /projects/{name}/improve/preferences/refresh   — re-distill from feedback history
"""

import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from agents.base import SkillAgent
from api.dependencies import get_current_user, get_db, get_project_context
from api.routers.api_keys import get_user_secret
from core.db.models import PageChange, ProjectFeedback, ProjectPreferences, User
from core.models.context import ProjectContext

router = APIRouter(prefix="/projects/{name}/improve", tags=["feedback"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class FeedbackRequest(BaseModel):
    verdict: str          # "approve" or "reject"
    comment: Optional[str] = None


class FeedbackOut(BaseModel):
    id: int
    change_id: int
    verdict: str
    comment: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PreferencesOut(BaseModel):
    rules: list[str]
    updated_at: Optional[datetime] = None


# ── Helpers ────────────────────────────────────────────────────────────────────

def _distill_preferences(
    feedback_entries: list[ProjectFeedback],
    changes: list[PageChange],
    openai_key: str,
) -> list[str]:
    """
    Run feedback-distiller (gpt-4o-mini) over the feedback history.
    Returns up to 10 actionable style/content rules.
    """
    if not feedback_entries:
        return []

    change_map = {c.id: c for c in changes}
    lines = []
    for fb in feedback_entries[-30:]:  # last 30 entries
        change = change_map.get(fb.change_id)
        summary = change.change_summary if change else "Unknown change"
        lines.append(
            f"- [{fb.verdict.upper()}] {summary}"
            + (f" | Subscriber note: {fb.comment}" if fb.comment else "")
        )

    prompt = f"""You are analyzing subscriber feedback on AI-generated SEO content changes.
Based on the approval/rejection patterns below, extract up to 10 concrete, actionable rules
that future AI agents should follow when generating content for this subscriber.

Rules must be:
- Specific and actionable (not vague like "be better")
- About content style, tone, structure, or SEO approach
- Based on observed patterns in the feedback
- Written as instructions for an AI (e.g. "Always include a direct answer in the first paragraph")

Feedback history (newest first):
{chr(10).join(lines)}

Output a JSON object: {{"rules": ["rule 1", "rule 2", ...]}}
Maximum 10 rules. If no clear patterns emerge, return fewer rules or an empty list.
Only include rules you can confidently derive from the feedback."""

    try:
        raw = SkillAgent("seo-analyzer", openai_key, model="gpt-4o-mini").run(
            prompt, timeout=60, json_mode=True
        )
        data = json.loads(raw)
        rules = data.get("rules", [])
        return [r for r in rules if isinstance(r, str) and r.strip()][:10]
    except Exception:
        return []


def get_project_preferences(
    db: Session, user_id: int, project_name: str
) -> list[str]:
    """Return distilled preference rules for use in agent prompts."""
    row = db.query(ProjectPreferences).filter(
        ProjectPreferences.user_id == user_id,
        ProjectPreferences.project_name == project_name,
    ).first()
    if not row or not row.rules:
        return []
    return list(row.rules)


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/feedback/{change_id}", response_model=FeedbackOut)
def submit_feedback(
    change_id: int,
    body: FeedbackRequest,
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.verdict not in ("approve", "reject"):
        raise HTTPException(400, "verdict must be 'approve' or 'reject'")

    change = db.query(PageChange).filter(
        PageChange.id == change_id,
        PageChange.user_id == current_user.id,
        PageChange.project_name == context.name,
    ).first()
    if not change:
        raise HTTPException(404, "Change not found.")

    fb = ProjectFeedback(
        user_id=current_user.id,
        project_name=context.name,
        change_id=change_id,
        verdict=body.verdict,
        comment=body.comment,
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)

    # Store rejection reason on the change record if rejected
    if body.verdict == "reject" and body.comment:
        change.rejection_reason = body.comment
        db.commit()

    # Async distillation: re-distill preferences after every 5th feedback entry
    total_feedback = db.query(ProjectFeedback).filter(
        ProjectFeedback.user_id == current_user.id,
        ProjectFeedback.project_name == context.name,
    ).count()

    if total_feedback % 5 == 0:
        try:
            _trigger_distillation(current_user.id, context.name, db)
        except Exception:
            pass  # distillation is async-optional — never block feedback response

    return fb


@router.get("/preferences", response_model=PreferencesOut)
def get_preferences(
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.query(ProjectPreferences).filter(
        ProjectPreferences.user_id == current_user.id,
        ProjectPreferences.project_name == context.name,
    ).first()
    if not row:
        return PreferencesOut(rules=[], updated_at=None)
    return PreferencesOut(rules=row.rules or [], updated_at=row.updated_at)


@router.post("/preferences/refresh", response_model=PreferencesOut)
def refresh_preferences(
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually re-distill preferences from full feedback history."""
    openai_key = get_user_secret("openai", current_user.id, db)
    _trigger_distillation(current_user.id, context.name, db, openai_key=openai_key)

    row = db.query(ProjectPreferences).filter(
        ProjectPreferences.user_id == current_user.id,
        ProjectPreferences.project_name == context.name,
    ).first()
    return PreferencesOut(rules=row.rules or [] if row else [], updated_at=row.updated_at if row else None)


def _trigger_distillation(
    user_id: int,
    project_name: str,
    db: Session,
    openai_key: str | None = None,
) -> None:
    if openai_key is None:
        try:
            from api.routers.api_keys import get_user_secret
            openai_key = get_user_secret("openai", user_id, db)
        except Exception:
            return

    feedback_entries = (
        db.query(ProjectFeedback)
        .filter(
            ProjectFeedback.user_id == user_id,
            ProjectFeedback.project_name == project_name,
        )
        .order_by(ProjectFeedback.created_at.desc())
        .all()
    )
    if not feedback_entries:
        return

    change_ids = [fb.change_id for fb in feedback_entries]
    changes = (
        db.query(PageChange)
        .filter(PageChange.id.in_(change_ids))
        .all()
    )

    rules = _distill_preferences(feedback_entries, changes, openai_key)

    row = db.query(ProjectPreferences).filter(
        ProjectPreferences.user_id == user_id,
        ProjectPreferences.project_name == project_name,
    ).first()

    if row:
        row.rules = rules
        row.updated_at = datetime.utcnow()
    else:
        db.add(ProjectPreferences(
            user_id=user_id,
            project_name=project_name,
            rules=rules,
        ))
    db.commit()
