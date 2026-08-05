"""
Observability — subscriber dashboard metrics (§19 P2-18, §26).

GET /projects/{name}/metrics  → AI credits, articles, pages improved,
                                approval rate, cron success rate, plagiarism breakdown.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, get_db, get_project_context
from core.db.models import AIHistory, CronRun, CronJob, PageChange, User
from core.models.context import ProjectContext

router = APIRouter(prefix="/projects/{name}/metrics", tags=["observability"])


class PlagiarismBreakdown(BaseModel):
    clean: int = 0
    flagged: int = 0
    rewritten: int = 0
    skipped: int = 0


class ProjectMetrics(BaseModel):
    ai_credits_used: float
    articles_created: int
    pages_improved: int
    changes_pending: int
    approval_rate: float
    cron_success_rate: float
    plagiarism: PlagiarismBreakdown
    period_days: int


@router.get("", response_model=ProjectMetrics)
def get_metrics(
    period_days: int = 30,
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    since = datetime.utcnow() - timedelta(days=period_days)
    uid = current_user.id
    pname = context.name

    # AI credits (sum cost_usd from AIHistory)
    ai_credits = db.query(func.coalesce(func.sum(AIHistory.cost_usd), 0.0)).filter(
        AIHistory.user_id == uid,
        AIHistory.project_name == pname,
        AIHistory.created_at >= since,
    ).scalar() or 0.0

    # Articles created (new_draft PageChanges)
    articles_created = db.query(func.count(PageChange.id)).filter(
        PageChange.user_id == uid,
        PageChange.project_name == pname,
        PageChange.action_type == "new_draft",
        PageChange.created_at >= since,
    ).scalar() or 0

    # Pages improved (approved page_edit changes)
    pages_improved = db.query(func.count(PageChange.id)).filter(
        PageChange.user_id == uid,
        PageChange.project_name == pname,
        PageChange.action_type == "page_edit",
        PageChange.status == "approved",
        PageChange.created_at >= since,
    ).scalar() or 0

    # Pending changes
    changes_pending = db.query(func.count(PageChange.id)).filter(
        PageChange.user_id == uid,
        PageChange.project_name == pname,
        PageChange.status == "pending",
    ).scalar() or 0

    # Approval rate
    total_decided = db.query(func.count(PageChange.id)).filter(
        PageChange.user_id == uid,
        PageChange.project_name == pname,
        PageChange.status.in_(["approved", "rolled_back"]),
        PageChange.created_at >= since,
    ).scalar() or 0
    approved = db.query(func.count(PageChange.id)).filter(
        PageChange.user_id == uid,
        PageChange.project_name == pname,
        PageChange.status == "approved",
        PageChange.created_at >= since,
    ).scalar() or 0
    approval_rate = round(approved / total_decided * 100, 1) if total_decided > 0 else 0.0

    # Cron success rate
    cron_job_ids = [
        row[0] for row in db.query(CronJob.id).filter(
            CronJob.user_id == uid,
            CronJob.project_name == pname,
        ).all()
    ]
    if cron_job_ids:
        total_runs = db.query(func.count(CronRun.id)).filter(
            CronRun.cron_job_id.in_(cron_job_ids),
            CronRun.started_at >= since,
        ).scalar() or 0
        success_runs = db.query(func.count(CronRun.id)).filter(
            CronRun.cron_job_id.in_(cron_job_ids),
            CronRun.status == "success",
            CronRun.started_at >= since,
        ).scalar() or 0
        cron_success_rate = round(success_runs / total_runs * 100, 1) if total_runs > 0 else 0.0
    else:
        cron_success_rate = 0.0

    # Plagiarism breakdown (new_draft changes only)
    plag_rows = db.query(PageChange.plagiarism_status, func.count(PageChange.id)).filter(
        PageChange.user_id == uid,
        PageChange.project_name == pname,
        PageChange.action_type == "new_draft",
        PageChange.created_at >= since,
    ).group_by(PageChange.plagiarism_status).all()

    plag = PlagiarismBreakdown()
    for status, count in plag_rows:
        if status == "clean":
            plag.clean = count
        elif status == "flagged":
            plag.flagged = count
        elif status == "rewritten":
            plag.rewritten = count
        else:
            plag.skipped += count

    return ProjectMetrics(
        ai_credits_used=round(ai_credits, 4),
        articles_created=articles_created,
        pages_improved=pages_improved,
        changes_pending=changes_pending,
        approval_rate=approval_rate,
        cron_success_rate=cron_success_rate,
        plagiarism=plag,
        period_days=period_days,
    )
