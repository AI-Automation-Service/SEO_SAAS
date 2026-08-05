"""
CRUD endpoints for managing per-project cron jobs.
POST /projects/{name}/cron         — create or update a cron job
GET  /projects/{name}/cron         — list all cron jobs for this project
PUT  /projects/{name}/cron/{type}  — enable/disable or change frequency
GET  /projects/{name}/cron/runs    — recent run history
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, get_db, get_project_context
from core.db.models import CronJob, CronRun, User
from core.models.context import ProjectContext

router = APIRouter(prefix="/projects/{name}/cron", tags=["cron"])

_JOB_DEFAULTS: dict[str, int] = {
    "gsc_sync":         7,
    "ranking_monitor":  7,
    "content_refresh":  30,
    "content_calendar": 7,
    "cluster_improve":  7,
    "meta_audit":       30,
}


class CronJobOut(BaseModel):
    id: int
    job_type: str
    frequency_days: int
    enabled: bool
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CronRunOut(BaseModel):
    id: int
    cron_job_id: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    changes_created: int
    auto_applied: int
    status: str
    error_detail: Optional[str] = None
    retry_count: int

    class Config:
        from_attributes = True


class CronJobCreate(BaseModel):
    job_type: str
    frequency_days: Optional[int] = None
    enabled: bool = True


class CronJobUpdate(BaseModel):
    enabled: Optional[bool] = None
    frequency_days: Optional[int] = None


@router.get("", response_model=list[CronJobOut])
def list_cron_jobs(
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(CronJob)
        .filter(CronJob.user_id == current_user.id, CronJob.project_name == context.name)
        .all()
    )


@router.post("", response_model=CronJobOut)
def create_or_update_cron_job(
    body: CronJobCreate,
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.job_type not in _JOB_DEFAULTS:
        raise HTTPException(400, f"Unknown job type. Valid types: {list(_JOB_DEFAULTS)}")

    freq = body.frequency_days or _JOB_DEFAULTS[body.job_type]
    existing = db.query(CronJob).filter(
        CronJob.user_id == current_user.id,
        CronJob.project_name == context.name,
        CronJob.job_type == body.job_type,
    ).first()

    if existing:
        existing.frequency_days = freq
        existing.enabled = body.enabled
        existing.next_run_at = datetime.utcnow() + timedelta(days=freq)
        db.commit()
        db.refresh(existing)
        return existing

    job = CronJob(
        user_id=current_user.id,
        project_name=context.name,
        job_type=body.job_type,
        frequency_days=freq,
        enabled=body.enabled,
        next_run_at=datetime.utcnow() + timedelta(days=freq),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.put("/{job_type}", response_model=CronJobOut)
def update_cron_job(
    job_type: str,
    body: CronJobUpdate,
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = db.query(CronJob).filter(
        CronJob.user_id == current_user.id,
        CronJob.project_name == context.name,
        CronJob.job_type == job_type,
    ).first()
    if not job:
        raise HTTPException(404, f"Cron job '{job_type}' not found.")

    if body.enabled is not None:
        job.enabled = body.enabled
    if body.frequency_days is not None:
        job.frequency_days = body.frequency_days
        job.next_run_at = datetime.utcnow() + timedelta(days=body.frequency_days)

    db.commit()
    db.refresh(job)
    return job


@router.get("/runs", response_model=list[CronRunOut])
def list_cron_runs(
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job_ids = [
        j.id for j in db.query(CronJob).filter(
            CronJob.user_id == current_user.id,
            CronJob.project_name == context.name,
        ).all()
    ]
    if not job_ids:
        return []
    return (
        db.query(CronRun)
        .filter(CronRun.cron_job_id.in_(job_ids))
        .order_by(CronRun.started_at.desc())
        .limit(50)
        .all()
    )


@router.post("/{job_type}/run-now", response_model=dict)
def run_job_now(
    job_type: str,
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually trigger a cron job immediately (runs synchronously — may be slow)."""
    job = db.query(CronJob).filter(
        CronJob.user_id == current_user.id,
        CronJob.project_name == context.name,
        CronJob.job_type == job_type,
    ).first()
    if not job:
        raise HTTPException(404, f"Cron job '{job_type}' not found.")

    from scheduler.cron import _dispatch_job
    _dispatch_job(current_user.id, context.name, job_type, job.id)
    return {"message": f"Job '{job_type}' triggered for project '{context.name}'."}
