from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl

from api.dependencies import get_knowledge_loader, get_project_loader, get_project_context, get_scaffolder
from api.models.responses import (
    ProjectCreated,
    ProjectDetail,
    ProjectSummary,
    ValidationResult,
)
from core.knowledge import KnowledgeLoader
from core.models.context import ProjectContext
from core.project import ProjectLoader
from core.project_writer import update_project_yaml
from core.scaffold import ProjectScaffolder
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


@router.post("", response_model=ProjectCreated, status_code=201)
def create_project(
    body: CreateProjectRequest,
    scaffolder: ProjectScaffolder = Depends(get_scaffolder),
):
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
    )


class UpdateProjectRequest(BaseModel):
    website: HttpUrl


@router.patch("/{name}", status_code=200)
def update_project(
    body: UpdateProjectRequest,
    context: ProjectContext = Depends(get_project_context),
):
    config_file = context.project_dir / "config" / "project.yaml"
    update_project_yaml(config_file, {"website": str(body.website)})
    return {"name": context.name, "website": str(body.website)}


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
