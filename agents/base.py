from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Type

from openai import OpenAI
from pydantic import BaseModel

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

SKILLS_DIR = Path(__file__).parent.parent / "skills"
SHARED_DIR = SKILLS_DIR / "shared"
_SKILL_CACHE: dict[str, str] = {}
_SCHEMA_CACHE: dict[type, dict] = {}
_logger = logging.getLogger(__name__)

_STUB_MARKERS = ("CONTENT TO BE DEFINED HERE", "<!-- PLACEHOLDER")


# ── Schema utilities ───────────────────────────────────────────────────────────

def _enforce_strict_schema(schema: dict) -> dict:
    """
    Recursively add additionalProperties: false to every object in the schema.
    OpenAI Structured Outputs strict mode requires this at every nesting level.
    Pydantic's model_json_schema() does not add it automatically.
    Handles anyOf/oneOf/allOf (used by Pydantic for nullable fields).
    """
    schema = dict(schema)
    if schema.get("type") == "object":
        schema["additionalProperties"] = False
        if "properties" in schema:
            schema["properties"] = {
                k: _enforce_strict_schema(v)
                for k, v in schema["properties"].items()
            }
    if "$defs" in schema:
        schema["$defs"] = {
            k: _enforce_strict_schema(v)
            for k, v in schema["$defs"].items()
        }
    if schema.get("type") == "array" and "items" in schema:
        schema["items"] = _enforce_strict_schema(schema["items"])
    for union_key in ("anyOf", "oneOf", "allOf"):
        if union_key in schema:
            schema[union_key] = [_enforce_strict_schema(s) for s in schema[union_key]]
    return schema


def _get_strict_schema(contract: Type[BaseModel]) -> dict:
    """Return the strict-mode JSON schema for a contract, cached by class."""
    if contract not in _SCHEMA_CACHE:
        _SCHEMA_CACHE[contract] = _enforce_strict_schema(contract.model_json_schema())
    return _SCHEMA_CACHE[contract]


def _build_fallback_hint(contract: Type[BaseModel]) -> str:
    """
    Generate a one-line field hint from a contract's required fields.
    Used only on the json_mode fallback path when a contract exists.
    Derived from the Pydantic model at runtime — never written manually.
    """
    try:
        schema = contract.model_json_schema()
        required_fields: list[str] = schema.get("required", [])
        if not required_fields:
            return ""
        return f"Respond with a JSON object containing these fields: {', '.join(required_fields)}"
    except Exception:
        return ""


def _resolve_mode(output_mode: str | None, json_mode: bool) -> str:
    """Resolve effective output mode. output_mode takes priority; json_mode=True is the compat alias."""
    return output_mode or ("json_mode" if json_mode else "markdown")


def _resolve_response_format(
    mode: str,
    name: str,
    contract: Type[BaseModel] | None,
) -> dict | None:
    """
    Build the OpenAI response_format dict for a given mode.
    Returns None for markdown agents (no response_format).
    Single implementation used by BaseAgent._call() and composer.py.
    """
    if mode == "structured":
        if contract is None:
            raise ValueError(
                f"Agent '{name}': output_mode='structured' requires a contract."
            )
        return {
            "type": "json_schema",
            "json_schema": {
                "name": name.replace("-", "_"),
                "strict": True,
                "schema": _get_strict_schema(contract),
            },
        }
    if mode == "json_mode":
        return {"type": "json_object"}
    if mode == "markdown":
        return None
    raise ValueError(
        f"Agent '{name}': unknown output_mode {mode!r}. "
        f"Valid values: 'structured', 'json_mode', 'markdown'."
    )


# ── Prompt assembly ────────────────────────────────────────────────────────────

def _compose_system_prompt(skill_dir: Path, shared_docs: list[str]) -> str:
    """Assemble a multi-layer system prompt from platform identity, agent identity,
    domain expertise, and shared documents."""
    parts: list[str] = []

    # Layer 0: platform identity (unconditional — never registered per-agent)
    platform_identity = SHARED_DIR / "platform-identity.md"
    if platform_identity.exists():
        parts.append(platform_identity.read_text(encoding="utf-8"))

    # Layer 1: agent identity
    identity = skill_dir / "identity.md"
    if identity.exists():
        parts.append(identity.read_text(encoding="utf-8"))

    # Layer 2: domain expertise (SKILL.md)
    parts.append((skill_dir / "SKILL.md").read_text(encoding="utf-8"))

    # Layer 3: shared documents (in declared order)
    for doc_name in shared_docs:
        doc_file = SHARED_DIR / f"{doc_name}.md"
        if not doc_file.exists():
            continue
        content = doc_file.read_text(encoding="utf-8")
        if any(marker in content for marker in _STUB_MARKERS):
            _logger.warning(
                "Shared doc '%s.md' contains placeholder content — skipping to avoid "
                "loading stub instructions into the system prompt.",
                doc_name,
            )
            continue
        parts.append(content)

    return "\n\n---\n\n".join(parts)


def _load_skill(skill_name: str) -> str:
    if skill_name not in _SKILL_CACHE:
        skill_dir = SKILLS_DIR / skill_name

        # Priority 1: Registry — the single source of truth for all registered agents.
        # Any agent in the registry uses its declared shared_docs regardless of output_mode.
        # Deferred import avoids a module-level circular dependency.
        from agents.registry import REGISTRY  # noqa: PLC0415
        if skill_name in REGISTRY:
            config = REGISTRY[skill_name]
            _SKILL_CACHE[skill_name] = _compose_system_prompt(skill_dir, config.shared_docs)

        # Priority 2: agent.json sidecar (for skills not yet in the registry)
        elif (skill_dir / "agent.json").exists():
            config_dict = json.loads((skill_dir / "agent.json").read_text(encoding="utf-8"))
            shared_docs: list[str] = config_dict.get("shared_docs", [])
            _SKILL_CACHE[skill_name] = _compose_system_prompt(skill_dir, shared_docs)

        # Priority 3: Direct SKILL.md (legacy skills not in registry or agent.json)
        else:
            skill_path = skill_dir / "SKILL.md"
            if not skill_path.exists():
                raise FileNotFoundError(f"Skill not found: {skill_name}")
            _SKILL_CACHE[skill_name] = skill_path.read_text(encoding="utf-8")

    return _SKILL_CACHE[skill_name]


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
        output_mode: str | None = None,
        contract: Type[BaseModel] | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        extra_messages: list[dict] | None = None,
    ) -> tuple[str, dict]:
        """
        Call the model. Returns (content, usage_meta).
        usage_meta contains input_tokens, output_tokens, cost_usd, duration_ms.

        output_mode takes priority over the deprecated json_mode flag.
        json_mode=True is equivalent to output_mode="json_mode" (kept for compat).
        """
        messages = [{"role": "system", "content": self.system_prompt}]
        if extra_messages:
            messages.extend(extra_messages)
        messages.append({"role": "user", "content": user_message})

        effective_mode = _resolve_mode(output_mode, json_mode)
        rf = _resolve_response_format(effective_mode, self.skill_name, contract)

        kwargs: dict = {}
        if rf is not None:
            kwargs["response_format"] = rf
        if max_tokens:
            kwargs["max_tokens"] = max_tokens

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


# ── Legacy ─────────────────────────────────────────────────────────────────────

class SkillAgent(BaseAgent):
    """
    Original single-call agent. Kept for backward compatibility with existing routers.
    Inherits __init__ from BaseAgent. run() is a thin wrapper around _call() that
    drops the usage_meta and returns only the content string.
    """

    def run(
        self,
        user_message: str,
        timeout: int = 180,
        json_mode: bool = False,
        output_mode: str | None = None,
        contract: Type[BaseModel] | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> str:
        content, _ = self._call(
            user_message,
            timeout=timeout,
            json_mode=json_mode,
            output_mode=output_mode,
            contract=contract,
            temperature=temperature,
            max_tokens=max_tokens,
        )
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
