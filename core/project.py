from pathlib import Path
from typing import Optional

import yaml

from core.models.project import ProjectConfig
from shared.exceptions import ProjectConfigError, ProjectNotFoundError

PROJECTS_DIR = Path(__file__).parent.parent / "projects"


def load_project_context(user_id: int, project_name: str):
    """
    Load a ProjectContext for use outside of FastAPI request scope (e.g. cron jobs).
    Returns None if the project does not exist.
    """
    from core.config import load_config
    from core.knowledge import KnowledgeLoader
    from core.models.context import ProjectContext

    config = load_config()
    user_dir = config.projects_dir / str(user_id)
    loader = ProjectLoader(user_dir)
    kl = KnowledgeLoader(user_dir)
    try:
        project_config = loader.load(project_name)
    except (ProjectNotFoundError, ProjectConfigError):
        return None
    return ProjectContext(
        name=project_name,
        config=project_config,
        knowledge=kl.load(project_name),
        project_dir=user_dir / project_name,
    )


class ProjectLoader:
    def __init__(self, projects_dir: Path = PROJECTS_DIR):
        self.projects_dir = projects_dir

    def load(self, project_name: str) -> ProjectConfig:
        project_dir = self.projects_dir / project_name
        if not project_dir.exists():
            raise ProjectNotFoundError(
                f"Project '{project_name}' not found. "
                f"Expected directory: {project_dir}"
            )

        config_file = project_dir / "config" / "project.yaml"
        if not config_file.exists():
            raise ProjectConfigError(
                f"project.yaml missing for '{project_name}'. "
                f"Expected: {config_file}"
            )

        try:
            raw = yaml.safe_load(config_file.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            raise ProjectConfigError(
                f"Invalid YAML in project.yaml for '{project_name}': {e}"
            )

        if not raw:
            raise ProjectConfigError(
                f"project.yaml is empty for '{project_name}'"
            )

        try:
            return ProjectConfig(**raw)
        except Exception as e:
            raise ProjectConfigError(
                f"project.yaml validation failed for '{project_name}': {e}"
            )

    def list_projects(self) -> list[str]:
        if not self.projects_dir.exists():
            return []
        return sorted(
            d.name
            for d in self.projects_dir.iterdir()
            if d.is_dir() and (d / "config" / "project.yaml").exists()
        )
