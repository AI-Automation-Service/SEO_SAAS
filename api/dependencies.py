from pathlib import Path

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from core.auth import decode_token
from core.config import AppConfig, load_config
from core.db.base import SessionLocal
from core.db.models import User
from core.knowledge import KnowledgeLoader
from core.models.context import ProjectContext
from core.project import ProjectLoader
from core.scaffold import ProjectScaffolder
from core.secrets import SecretManager
from shared.exceptions import ProjectConfigError, ProjectNotFoundError

_bearer = HTTPBearer(auto_error=True)


# ── Database ─────────────────────────────────────────────────────────────────

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Auth ─────────────────────────────────────────────────────────────────────

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise HTTPException(401, "Invalid or expired token")

    if payload.get("type") != "access":
        raise HTTPException(401, "Token is not an access token")

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(401, "Token missing subject claim")

    user = db.get(User, int(user_id))
    if not user or not user.is_active:
        raise HTTPException(401, "User not found or disabled")

    return user


def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(403, "Admin access required")
    return current_user


def get_config() -> AppConfig:
    return load_config()


def get_secret_manager() -> SecretManager:
    return SecretManager()


# ── Per-user project isolation ───────────────────────────────────────────────
# Projects live at  projects/{user_id}/{project_name}/
# so each user only ever sees their own data.

def get_user_projects_dir(
    current_user: User = Depends(get_current_user),
    config: AppConfig = Depends(get_config),
) -> Path:
    d = config.projects_dir / str(current_user.id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_project_loader(
    user_dir: Path = Depends(get_user_projects_dir),
) -> ProjectLoader:
    return ProjectLoader(user_dir)


def get_knowledge_loader(
    user_dir: Path = Depends(get_user_projects_dir),
) -> KnowledgeLoader:
    return KnowledgeLoader(user_dir)


def get_scaffolder(
    user_dir: Path = Depends(get_user_projects_dir),
) -> ProjectScaffolder:
    return ProjectScaffolder(user_dir)


def get_project_context(
    name: str,
    user_dir: Path = Depends(get_user_projects_dir),
    loader: ProjectLoader = Depends(get_project_loader),
    kl: KnowledgeLoader = Depends(get_knowledge_loader),
) -> ProjectContext:
    try:
        project_config = loader.load(name)
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ProjectConfigError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return ProjectContext(
        name=name,
        config=project_config,
        knowledge=kl.load(name),
        project_dir=user_dir / name,
    )
