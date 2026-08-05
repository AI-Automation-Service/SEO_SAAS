"""
agents/composer.py — Assembles system prompts from registry configuration.

Reads shared_docs and output_mode from the agent registry.
Prompt assembly delegates to base._load_skill (uses the shared _SKILL_CACHE).
Response_format building delegates to base._resolve_response_format (single implementation).

Usage (wired into BaseAgent in Stage 3):
    from agents.composer import compose
    prompt, response_format = compose("seo-meta", contract=MetaResponse)

Usage (standalone — for testing or tooling):
    prompt, _ = compose("seo-plan")   # Markdown agent; response_format is None
"""
from __future__ import annotations

from typing import Type

from pydantic import BaseModel

from agents.base import (
    _build_fallback_hint,
    _load_skill,
    _resolve_response_format,
)
from agents.registry import get as registry_get


def compose(
    agent_name: str,
    contract: Type[BaseModel] | None = None,
) -> tuple[str, dict | None]:
    """
    Build the system prompt and OpenAI response_format dict for an agent.

    Returns:
        (system_prompt, response_format)

    response_format is:
        - json_schema dict        when output_mode=="structured" and contract is provided
        - {"type":"json_object"}  when output_mode=="json_mode"
        - None                    when output_mode=="markdown"

    For output_mode=="structured", the contract parameter is required.
    For output_mode=="json_mode" with a contract, a one-line fallback field hint is
    appended to the prompt (derived from the contract at runtime, never written by hand).
    """
    config = registry_get(agent_name)
    prompt = _load_skill(agent_name)

    # For json_mode fallback with a contract: append one-line field hint.
    if config.output_mode == "json_mode" and contract is not None:
        hint = _build_fallback_hint(contract)
        if hint:
            prompt = prompt + f"\n\n---\n\n{hint}"

    return prompt, _resolve_response_format(config.output_mode, config.name, contract)
