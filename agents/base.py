from pathlib import Path

from openai import OpenAI

SKILLS_DIR = Path(__file__).parent.parent / "skills"
_SKILL_CACHE: dict[str, str] = {}


class SkillAgent:
    def __init__(self, skill_name: str, openai_key: str, model: str = "gpt-4o"):
        skill_path = SKILLS_DIR / skill_name / "SKILL.md"
        if skill_name not in _SKILL_CACHE:
            if not skill_path.exists():
                raise FileNotFoundError(f"Skill not found: {skill_name}")
            _SKILL_CACHE[skill_name] = skill_path.read_text(encoding="utf-8")
        self.system_prompt = _SKILL_CACHE[skill_name]
        self.client = OpenAI(api_key=openai_key)
        self.model = model

    def run(
        self,
        user_message: str,
        timeout: int = 180,
        json_mode: bool = False,
        temperature: float = 0.0,
    ) -> str:
        kwargs: dict = {}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_message},
            ],
            timeout=timeout,
            temperature=temperature,
            **kwargs,
        )
        return response.choices[0].message.content or ""
