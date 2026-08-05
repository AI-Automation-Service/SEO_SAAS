import time
from pathlib import Path
from typing import TYPE_CHECKING

from openai import OpenAI

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

SKILLS_DIR = Path(__file__).parent.parent / "skills"
_SKILL_CACHE: dict[str, str] = {}


def _load_skill(skill_name: str) -> str:
    if skill_name not in _SKILL_CACHE:
        skill_path = SKILLS_DIR / skill_name / "SKILL.md"
        if not skill_path.exists():
            raise FileNotFoundError(f"Skill not found: {skill_name}")
        _SKILL_CACHE[skill_name] = skill_path.read_text(encoding="utf-8")
    return _SKILL_CACHE[skill_name]


# ── Legacy ─────────────────────────────────────────────────────────────────────

class SkillAgent:
    """Original single-call agent. Kept for backward compatibility with existing routers."""

    def __init__(self, skill_name: str, openai_key: str, model: str = "gpt-4o"):
        self.system_prompt = _load_skill(skill_name)
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


# ── v2 SDK ─────────────────────────────────────────────────────────────────────

class BaseAgent:
    """
    Root of the v2 agent hierarchy.
    Handles: BYOK OpenAI init, skill cache, raw _call(), usage logging stub.
    """

    def __init__(self, skill_name: str, openai_key: str, model: str = "gpt-4o"):
        self.skill_name = skill_name
        self.system_prompt = _load_skill(skill_name)
        self.client = OpenAI(api_key=openai_key)
        self.model = model

    def _call(
        self,
        user_message: str,
        *,
        timeout: int = 180,
        json_mode: bool = False,
        temperature: float = 0.0,
        extra_messages: list[dict] | None = None,
    ) -> tuple[str, dict]:
        """
        Call the model. Returns (content, usage_meta).
        usage_meta contains input_tokens, output_tokens, cost_usd, duration_ms.
        """
        messages = [{"role": "system", "content": self.system_prompt}]
        if extra_messages:
            messages.extend(extra_messages)
        messages.append({"role": "user", "content": user_message})

        kwargs: dict = {}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        t0 = time.monotonic()
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            timeout=timeout,
            temperature=temperature,
            **kwargs,
        )
        duration_ms = int((time.monotonic() - t0) * 1000)

        usage = response.usage
        input_tokens = usage.prompt_tokens if usage else 0
        output_tokens = usage.completion_tokens if usage else 0
        cost_usd = _estimate_cost(self.model, input_tokens, output_tokens)

        content = response.choices[0].message.content or ""
        return content, {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost_usd,
            "duration_ms": duration_ms,
        }

    def _log_usage(
        self,
        db: "Session",
        user_id: int,
        project_name: str,
        usage_meta: dict,
        *,
        status: str = "success",
        error_detail: str | None = None,
        change_id: int | None = None,
        article_job_id: str | None = None,
    ) -> None:
        """Log AI usage to AIHistory table. Silently skips if table not yet created."""
        try:
            from core.db.models import AIHistory
            db.add(AIHistory(
                agent_name=self.skill_name,
                model=self.model,
                input_tokens=usage_meta.get("input_tokens", 0),
                output_tokens=usage_meta.get("output_tokens", 0),
                cost_usd=usage_meta.get("cost_usd", 0.0),
                duration_ms=usage_meta.get("duration_ms", 0),
                status=status,
                error_detail=error_detail,
                user_id=user_id,
                project_name=project_name,
                change_id=change_id,
                article_job_id=article_job_id,
            ))
            db.commit()
        except Exception:
            pass  # table may not exist yet during migration window


class SEOAgent(BaseAgent):
    """
    Adds the three-block context assembly used by all SEO-aware agents.
    Subclasses call build_context() to compose their user message.
    """

    def build_context(
        self,
        knowledge: str = "",
        preferences: list[str] | None = None,
        plan_context: str = "",
    ) -> str:
        """
        Assembles the standard three-block context header.
        Omits empty blocks. Omits preferences block entirely if no rules recorded.
        """
        parts: list[str] = []
        if knowledge:
            parts.append(f"## Business Knowledge\n{knowledge.strip()}")
        if preferences:
            rules = "\n".join(f"- {r}" for r in preferences)
            parts.append(f"## Subscriber Preferences\n{rules}")
        if plan_context:
            parts.append(f"## Execution Plan Context\n{plan_context.strip()}")
        return "\n\n".join(parts)


class ActionAgent(SEOAgent):
    """
    Produces a PageChange in the Change Queue.
    Subclasses implement _build_message() and _parse_result().
    """

    # Subclasses set this to the capability flag name (e.g. "AI_WRITER")
    required_capability: str | None = None

    def check_capability(self, capabilities: dict) -> None:
        """Raise ValueError if required capability flag is not enabled."""
        if self.required_capability and not capabilities.get(self.required_capability, True):
            raise ValueError(
                f"Capability '{self.required_capability}' is not enabled for this account."
            )


class AdvisoryAgent(SEOAgent):
    """
    Produces a Markdown report only — no Change Queue interaction.
    """

    def run_advisory(
        self,
        user_message: str,
        *,
        timeout: int = 180,
        db: "Session | None" = None,
        user_id: int | None = None,
        project_name: str = "",
    ) -> str:
        content, usage_meta = self._call(user_message, timeout=timeout)
        if db and user_id:
            self._log_usage(db, user_id, project_name, usage_meta)
        return content


# ── Cost estimation ────────────────────────────────────────────────────────────

_COST_PER_1K: dict[str, tuple[float, float]] = {
    # model: (input $/1K tokens, output $/1K tokens)
    "gpt-4o":           (0.0025, 0.010),
    "gpt-4o-mini":      (0.00015, 0.0006),
    "gpt-4.1":          (0.002, 0.008),
    "gpt-4.1-mini":     (0.0004, 0.0016),
}


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    rates = _COST_PER_1K.get(model, (0.002, 0.008))
    return round(input_tokens / 1000 * rates[0] + output_tokens / 1000 * rates[1], 6)
