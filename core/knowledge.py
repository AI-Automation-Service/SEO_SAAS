from pathlib import Path

from loguru import logger


class KnowledgeLoader:
    def __init__(self, projects_dir: Path):
        self.projects_dir = projects_dir

    def load(self, project_name: str) -> dict[str, str]:
        knowledge_dir = self.projects_dir / project_name / "knowledge"

        if not knowledge_dir.exists():
            logger.warning(
                f"Knowledge directory not found for project '{project_name}'. "
                f"Expected: {knowledge_dir}"
            )
            return {}

        knowledge: dict[str, str] = {}
        for md_file in sorted(knowledge_dir.glob("*.md")):
            content = md_file.read_text(encoding="utf-8").strip()
            # Strip heading line to check if remaining content is just a placeholder comment
            lines = [l for l in content.splitlines() if not l.startswith("#")]
            meaningful = "\n".join(lines).strip()
            if not meaningful or meaningful.startswith("<!--"):
                logger.debug(f"Skipping empty/placeholder knowledge file: {md_file.name}")
                continue
            knowledge[md_file.stem] = content
            logger.debug(f"Loaded knowledge: {md_file.name}")

        if not knowledge:
            logger.warning(f"No knowledge content found for project '{project_name}'")

        return knowledge
