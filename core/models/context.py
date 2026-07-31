from pathlib import Path

from pydantic import BaseModel

from core.models.project import ProjectConfig


class ProjectContext(BaseModel):
    name: str
    config: ProjectConfig
    knowledge: dict[str, str]
    project_dir: Path

    model_config = {"arbitrary_types_allowed": True}

    @property
    def data_dir(self) -> Path:
        return self.project_dir / "data"

    @property
    def reports_dir(self) -> Path:
        return self.project_dir / "reports"

    @property
    def content_dir(self) -> Path:
        return self.project_dir / "content"

    @property
    def audits_dir(self) -> Path:
        return self.project_dir / "audits"

    @property
    def logs_dir(self) -> Path:
        return self.project_dir / "logs"
