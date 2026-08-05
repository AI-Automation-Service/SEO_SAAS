from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from api.dependencies import get_admin_user, get_db
from api.routers.identity.account import _delete_user_data
from core.db.models import User

router = APIRouter(prefix="/admin", tags=["admin"])

VALID_PLANS = {"free", "pro", "agency"}
PLAN_LIMITS = {"free": 3, "pro": 10, "agency": 50}


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    plan: str
    max_projects: int
    is_active: bool
    is_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class StatsOut(BaseModel):
    total_users: int
    active_users: int
    admin_users: int


class UpdatePlanRequest(BaseModel):
    plan: str


@router.get("/users", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.put("/users/{user_id}/plan", status_code=204)
def update_user_plan(
    user_id: int,
    body: UpdatePlanRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    if body.plan not in VALID_PLANS:
        raise HTTPException(400, f"Invalid plan '{body.plan}'. Valid: {sorted(VALID_PLANS)}")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    user.plan = body.plan
    user.max_projects = PLAN_LIMITS[body.plan]
    db.commit()


@router.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    if user_id == admin.id:
        raise HTTPException(400, "Cannot delete your own account via admin panel")
    if not db.query(User).filter(User.id == user_id).first():
        raise HTTPException(404, "User not found")
    _delete_user_data(user_id, db)
    db.commit()


@router.get("/stats", response_model=StatsOut)
def get_stats(
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    total, active, admins = db.query(
        func.count(),
        func.sum(case((User.is_active == True, 1), else_=0)),  # noqa: E712
        func.sum(case((User.is_admin == True, 1), else_=0)),   # noqa: E712
    ).one()
    return StatsOut(total_users=total, active_users=active or 0, admin_users=admins or 0)
