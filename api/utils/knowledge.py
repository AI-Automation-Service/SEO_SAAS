from sqlalchemy.orm import Session

from core.db.models import ProjectKnowledge


def fetch_knowledge(
    db: Session, user_id: int, project_name: str
) -> ProjectKnowledge | None:
    return (
        db.query(ProjectKnowledge)
        .filter(
            ProjectKnowledge.user_id == user_id,
            ProjectKnowledge.project_name == project_name,
        )
        .first()
    )
