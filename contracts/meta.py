"""
contracts/meta.py — Output contract for the seo-meta agent.

This file is the REFERENCE IMPLEMENTATION for all SEO OS contracts.
When creating a new contract, use this file as your structural template.

The seo-meta agent generates optimised meta title and description for a page.
It is called when is_theme_controlled=True or the page is a posts listing page,
where full HTML editing is not possible but meta fields are writable.

Usage in router:
    raw = SkillAgent("seo-meta", openai_key, model="gpt-4o-mini").run(
        user_message, timeout=45, json_mode=True, max_tokens=600
    )
    response = MetaResponse.model_validate_json(raw)
    # Access fields via attributes:
    meta_title = response.meta_title
    meta_description = response.meta_description
"""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class MetaResponse(BaseModel):
    """
    Structured output from the seo-meta agent.

    All validators raise ValueError with a clear, actionable message so
    the router can log the exact constraint that was violated and, if retrying,
    append it to the next call's user message.
    """

    # ── Required fields ──────────────────────────────────────────────────────

    meta_title: str = Field(
        description=(
            "The optimised meta title for the page. Must contain the primary keyword, "
            "ideally near the start. Must be within Google's display range."
        )
    )

    meta_description: str = Field(
        description=(
            "The optimised meta description for the page. Must include the primary keyword "
            "naturally, have a clear call to action or value proposition, and fit within "
            "Google's display range."
        )
    )

    # ── Optional fields ───────────────────────────────────────────────────────

    change_notes: list[str] = Field(
        default_factory=list,
        description=(
            "Brief notes explaining what was changed and why. "
            "Used in the subscriber-facing change summary."
        ),
    )

    # ── Validators ────────────────────────────────────────────────────────────

    @field_validator("meta_title")
    @classmethod
    def validate_meta_title(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("meta_title must not be empty")
        if len(v) < 30:
            raise ValueError(
                f"meta_title is too short ({len(v)} chars) — minimum 30 characters"
            )
        if len(v) > 65:
            raise ValueError(
                f"meta_title is too long ({len(v)} chars) — maximum 65 characters"
            )
        return v

    @field_validator("meta_description")
    @classmethod
    def validate_meta_description(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("meta_description must not be empty")
        if len(v) < 100:
            raise ValueError(
                f"meta_description is too short ({len(v)} chars) — minimum 100 characters"
            )
        if len(v) > 165:
            raise ValueError(
                f"meta_description is too long ({len(v)} chars) — maximum 165 characters"
            )
        return v

    @field_validator("change_notes")
    @classmethod
    def validate_change_notes(cls, v: list[str]) -> list[str]:
        # Strip whitespace; drop empty strings silently (not a hard failure)
        return [note.strip() for note in v if note.strip()]


# ── Architecture notes (for future contract authors) ──────────────────────────
#
# 1. FIELD NAMES must match exactly what the agent is prompted to return.
#    If the field name here changes, the SKILL.md must NOT be updated with
#    the new name — update the prompt task instruction in the router instead.
#
# 2. VALIDATORS should check structure and constraints, not domain correctness.
#    "Is this a 30–65 char string?" is a validator.
#    "Is this title SEO-optimised?" is not — that is the agent's job.
#
# 3. OPTIONAL FIELDS should use Field(default=None) or Field(default_factory=list).
#    Never make a field Optional without a default — Pydantic will still require it.
#
# 4. NESTED MODELS are fine for complex structures. Example for a future contract:
#
#    class SignalScore(BaseModel):
#        score: int = Field(ge=0, le=100)
#        reason: str
#
#    class AnalyzerResponse(BaseModel):
#        keyword_signal: SignalScore
#        readability_signal: SignalScore
#
# 5. ENUMS constrain string fields to known values:
#
#    from enum import Enum
#    class Severity(str, Enum):
#        LOW = "low"
#        MEDIUM = "medium"
#        HIGH = "high"
#        CRITICAL = "critical"
#
#    severity: Severity  # Pydantic rejects any value not in the enum
