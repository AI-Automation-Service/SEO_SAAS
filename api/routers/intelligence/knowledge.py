from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, get_db, get_project_context
from core.db.models import ProjectKnowledge, User
from core.models.context import ProjectContext

router = APIRouter(prefix="/projects/{name}/knowledge", tags=["knowledge"])


class KnowledgeIn(BaseModel):
    about: Optional[str] = None
    products_services: Optional[str] = None
    target_audience: Optional[str] = None
    brand_voice: Optional[str] = None
    competitors_notes: Optional[str] = None
    seo_context: Optional[str] = None


class KnowledgeOut(KnowledgeIn):
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


@router.get("", response_model=KnowledgeOut)
def get_knowledge(
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = (
        db.query(ProjectKnowledge)
        .filter(
            ProjectKnowledge.user_id == current_user.id,
            ProjectKnowledge.project_name == context.name,
        )
        .first()
    )
    if not row:
        return KnowledgeOut()
    return row


@router.put("", response_model=KnowledgeOut)
def save_knowledge(
    body: KnowledgeIn,
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = (
        db.query(ProjectKnowledge)
        .filter(
            ProjectKnowledge.user_id == current_user.id,
            ProjectKnowledge.project_name == context.name,
        )
        .first()
    )
    if row:
        row.about = body.about
        row.products_services = body.products_services
        row.target_audience = body.target_audience
        row.brand_voice = body.brand_voice
        row.competitors_notes = body.competitors_notes
        row.seo_context = body.seo_context
        row.updated_at = datetime.utcnow()
    else:
        row = ProjectKnowledge(
            user_id=current_user.id,
            project_name=context.name,
            **body.model_dump(),
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return row
