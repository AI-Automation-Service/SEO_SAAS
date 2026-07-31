from fastapi import Depends

from core.config import AppConfig, load_config
from core.knowledge import KnowledgeLoader
from core.project import ProjectLoader
from core.scaffold import ProjectScaffolder


def get_config() -> AppConfig:
    return load_config()


def get_project_loader(config: AppConfig = Depends(get_config)) -> ProjectLoader:
    return ProjectLoader(config.projects_dir)


def get_knowledge_loader(config: AppConfig = Depends(get_config)) -> KnowledgeLoader:
    return KnowledgeLoader(config.projects_dir)


def get_scaffolder(config: AppConfig = Depends(get_config)) -> ProjectScaffolder:
    return ProjectScaffolder(config.projects_dir)
