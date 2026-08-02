import shutil
from datetime import datetime

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, get_knowledge_loader, get_project_loader, get_project_context, get_scaffolder, get_user_projects_dir
from api.models.responses import (
    ProjectCreated,
    ProjectDetail,
    ProjectSummary,
    ValidationResult,
)
from core.db.base import SessionLocal
from core.db.models import SitePage, User
from core.knowledge import KnowledgeLoader
from core.models.context import ProjectContext
from core.project import ProjectLoader
from pathlib import Path
from core.project_writer import update_project_yaml
from core.scaffold import ProjectScaffolder
from core.sitemap import fetch_sitemap_urls
from core.validation import validate_config
from shared.exceptions import ProjectConfigError, ProjectNotFoundError, SEOOSError

router = APIRouter(prefix="/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    name: str
    cms: str = "wordpress"


@router.get("", response_model=list[ProjectSummary])
def list_projects(loader: ProjectLoader = Depends(get_project_loader)):
    results = []
    for name in loader.list_projects():
        try:
            config = loader.load(name)
            results.append(
                ProjectSummary(
                    name=name,
                    website=str(config.website),
                    business_name=config.business_name,
                    cms=config.cms,
                    active=config.active,
                )
            )
        except ProjectConfigError:
            results.append(
                ProjectSummary(
                    name=name,
                    website="",
                    business_name="[config error — run validate to see details]",
                    cms="unknown",
                    active=False,
                )
            )
    return results


PROJECT_LIMIT = 1  # free plan; raise per subscription tier later

@router.post("", response_model=ProjectCreated, status_code=201)
def create_project(
    body: CreateProjectRequest,
    loader: ProjectLoader = Depends(get_project_loader),
    scaffolder: ProjectScaffolder = Depends(get_scaffolder),
):
    existing = loader.list_projects()
    if len(existing) >= PROJECT_LIMIT:
        raise HTTPException(
            status_code=403,
            detail=f"Plan limit reached — your current plan allows {PROJECT_LIMIT} project. "
                   "Upgrade your subscription to add more.",
        )
    try:
        project_dir = scaffolder.scaffold(body.name, cms=body.cms)
        return ProjectCreated(
            name=body.name,
            path=str(project_dir),
            message=f"Project '{body.name}' created.",
        )
    except SEOOSError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{name}", response_model=ProjectDetail)
def get_project(
    name: str,
    loader: ProjectLoader = Depends(get_project_loader),
    kl: KnowledgeLoader = Depends(get_knowledge_loader),
):
    try:
        config = loader.load(name)
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ProjectConfigError as e:
        raise HTTPException(status_code=422, detail=str(e))

    knowledge = kl.load(name)

    return ProjectDetail(
        name=name,
        website=str(config.website),
        business_name=config.business_name,
        business_type=config.business_type,
        country=config.country,
        language=config.language,
        cms=config.cms,
        seo_plugin=config.seo_plugin,
        image_source=config.image_source,
        active=config.active,
        knowledge_files=sorted(knowledge.keys()),
        competitors=config.competitors,
        tone_of_voice=config.tone_of_voice,
        target_audience=config.target_audience,
        seo_goals=config.seo_goals,
        business_goals=config.business_goals,
    )


class UpdateProjectRequest(BaseModel):
    website: Optional[HttpUrl] = None
    business_name: Optional[str] = None
    business_type: Optional[str] = None
    country: Optional[str] = None
    language: Optional[str] = None
    tone_of_voice: Optional[str] = None
    target_audience: Optional[str] = None
    seo_goals: Optional[list[str]] = None
    business_goals: Optional[list[str]] = None
    competitors: Optional[list[str]] = None
    seo_plugin: Optional[str] = None


def _bg_sitemap_sync(website: str, user_id: int, project_name: str) -> None:
    db = SessionLocal()
    try:
        pages = fetch_sitemap_urls(website)
        now = datetime.utcnow()
        for page in pages:
            existing = (
                db.query(SitePage)
                .filter(
                    SitePage.user_id == user_id,
                    SitePage.project_name == project_name,
                    SitePage.url == page["url"],
                )
                .first()
            )
            if existing:
                existing.slug = page["slug"]
                existing.synced_at = now
            else:
                db.add(SitePage(
                    user_id=user_id,
                    project_name=project_name,
                    url=page["url"],
                    slug=page["slug"],
                    synced_at=now,
                ))
        db.commit()
    except Exception:
        pass
    finally:
        db.close()


@router.patch("/{name}", status_code=200)
def update_project(
    body: UpdateProjectRequest,
    background_tasks: BackgroundTasks,
    context: ProjectContext = Depends(get_project_context),
    current_user: User = Depends(get_current_user),
):
    config_file = context.project_dir / "config" / "project.yaml"
    updates: dict = {}
    if body.website is not None:
        updates["website"] = str(body.website)
        background_tasks.add_task(_bg_sitemap_sync, str(body.website), current_user.id, context.name)
    if body.business_name is not None:
        updates["business_name"] = body.business_name
    if body.business_type is not None:
        updates["business_type"] = body.business_type
    if body.country is not None:
        updates["country"] = body.country
    if body.language is not None:
        updates["language"] = body.language
    if body.tone_of_voice is not None:
        updates["tone_of_voice"] = body.tone_of_voice
    if body.target_audience is not None:
        updates["target_audience"] = body.target_audience
    if body.seo_goals is not None:
        updates["seo_goals"] = body.seo_goals
    if body.business_goals is not None:
        updates["business_goals"] = body.business_goals
    if body.competitors is not None:
        updates["competitors"] = body.competitors
    if body.seo_plugin is not None:
        updates["seo_plugin"] = body.seo_plugin
    if updates:
        update_project_yaml(config_file, updates)
    return {"name": context.name, **updates}


@router.delete("/{name}", status_code=200)
def delete_project(
    name: str,
    user_dir: Path = Depends(get_user_projects_dir),
):
    project_dir = user_dir / name
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail=f"Project '{name}' not found.")
    shutil.rmtree(project_dir)
    return {"deleted": name}


@router.get("/{name}/validate", response_model=ValidationResult)
def validate_project(
    name: str,
    loader: ProjectLoader = Depends(get_project_loader),
):
    try:
        config = loader.load(name)
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ProjectConfigError as e:
        return ValidationResult(project=name, valid=False, errors=[str(e)], warnings=[])

    report = validate_config(name, config)
    return ValidationResult(
        project=name,
        valid=report.valid,
        errors=report.errors,
        warnings=report.warnings,
    )
