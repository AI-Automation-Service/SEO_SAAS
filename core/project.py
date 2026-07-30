from pathlib import Path

import yaml

from core.models.project import ProjectConfig
from shared.exceptions import ProjectConfigError, ProjectNotFoundError

PROJECTS_DIR = Path(__file__).parent.parent / "projects"


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
