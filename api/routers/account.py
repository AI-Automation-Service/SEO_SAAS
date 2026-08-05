from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, get_db
from core.auth import hash_password, verify_password
from core.config import load_config
from core.db.models import (
    AIHistory, CronJob, CronRun, Keyword, PageChange, ProjectFeedback,
    ProjectKnowledge, ProjectPreferences, SitePage, StrategyOutput, User, UserApiKey,
)

router = APIRouter(prefix="/account", tags=["account"])


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def strong_enough(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("New password must be at least 8 characters")
        return v


class UsageResponse(BaseModel):
    email: str
    full_name: str
    plan: str
    max_projects: int
    project_count: int
    is_admin: bool


def _delete_user_data(user_id: int, db: Session) -> None:
    """Delete all rows owned by the user, then the user row itself."""
    cron_subq = db.query(CronJob.id).filter(CronJob.user_id == user_id).scalar_subquery()
    db.query(CronRun).filter(CronRun.cron_job_id.in_(cron_subq)).delete(synchronize_session=False)
    for model in (CronJob, ProjectFeedback, ProjectPreferences, AIHistory, UserApiKey,
                  Keyword, ProjectKnowledge, StrategyOutput, SitePage, PageChange):
        db.query(model).filter(model.user_id == user_id).delete(synchronize_session=False)
    db.query(User).filter(User.id == user_id).delete(synchronize_session=False)


@router.put("/password", status_code=204)
def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(400, "Current password is incorrect")
    current_user.hashed_password = hash_password(body.new_password)
    db.commit()


@router.get("/usage", response_model=UsageResponse)
def get_usage(current_user: User = Depends(get_current_user)):
    config = load_config()
    user_dir = config.projects_dir / str(current_user.id)
    count = len([d for d in user_dir.iterdir() if d.is_dir()]) if user_dir.exists() else 0
    return UsageResponse(
        email=current_user.email,
        full_name=current_user.full_name,
        plan=current_user.plan,
        max_projects=current_user.max_projects,
        project_count=count,
        is_admin=current_user.is_admin,
    )


@router.delete("", status_code=204)
def delete_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _delete_user_data(current_user.id, db)
    db.commit()
