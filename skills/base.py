from pathlib import Path

from shared.exceptions import SkillError

SKILLS_DIR = Path(__file__).parent


class SkillLoader:
    def __init__(self, skills_dir: Path = SKILLS_DIR):
        self.skills_dir = skills_dir

    def load(self, skill_name: str) -> str:
        skill_file = self.skills_dir / skill_name / "SKILL.md"
        if not skill_file.exists():
            raise SkillError(
                f"Skill '{skill_name}' not found. Expected: {skill_file}"
            )
        return skill_file.read_text(encoding="utf-8")

    def list_skills(self) -> list[str]:
        return sorted(
            d.name
            for d in self.skills_dir.iterdir()
            if d.is_dir() and (d / "SKILL.md").exists()
        )
