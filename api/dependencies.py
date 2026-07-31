from fastapi import Depends, HTTPException

from core.config import AppConfig, load_config
from core.knowledge import KnowledgeLoader
from core.models.context import ProjectContext
from core.project import ProjectLoader
from core.scaffold import ProjectScaffolder
from core.secrets import SecretManager
from shared.exceptions import ProjectConfigError, ProjectNotFoundError


def get_config() -> AppConfig:
    return load_config()


def get_project_loader(config: AppConfig = Depends(get_config)) -> ProjectLoader:
    return ProjectLoader(config.projects_dir)


def get_knowledge_loader(config: AppConfig = Depends(get_config)) -> KnowledgeLoader:
    return KnowledgeLoader(config.projects_dir)


def get_scaffolder(config: AppConfig = Depends(get_config)) -> ProjectScaffolder:
    return ProjectScaffolder(config.projects_dir)


def get_secret_manager() -> SecretManager:
    return SecretManager()


def get_project_context(
    name: str,
    config: AppConfig = Depends(get_config),
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
        project_dir=config.projects_dir / name,
    )
