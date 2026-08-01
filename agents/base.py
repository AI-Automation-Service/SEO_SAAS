from pathlib import Path

from openai import OpenAI

SKILLS_DIR = Path(__file__).parent.parent / "skills"


class SkillAgent:
    def __init__(self, skill_name: str, openai_key: str, model: str = "gpt-4o"):
        skill_path = SKILLS_DIR / skill_name / "SKILL.md"
        if not skill_path.exists():
            raise FileNotFoundError(f"Skill not found: {skill_name}")
        self.system_prompt = skill_path.read_text(encoding="utf-8")
        self.client = OpenAI(api_key=openai_key)
        self.model = model

    def run(self, user_message: str, timeout: int = 180) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_message},
            ],
            timeout=timeout,
        )
        return response.choices[0].message.content or ""
