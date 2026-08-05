"""
contracts/meta.py — Output contract for the seo-meta agent.

This file is the REFERENCE IMPLEMENTATION for all SEO OS contracts.
When creating a new contract, use this file as your structural template.

The seo-meta agent generates optimised meta title and description for a page.
It is called when is_theme_controlled=True or the page is a posts listing page,
where full HTML editing is not possible but meta fields are writable.

Usage in router:
    raw = SkillAgent("seo-meta", openai_key, model="gpt-4o-mini").run(
        user_message, timeout=45, output_mode="structured", contract=MetaResponse
    )
    response = MetaResponse.model_validate_json(raw)
    # Access fields via attributes — validators already stripped whitespace:
    title = response.suggested_meta_title
    description = response.suggested_meta_description
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

    suggested_meta_title: str = Field(
        description=(
            "The optimised meta title for the page. Must contain the primary keyword, "
            "ideally near the start. Must be within Google's display range."
        )
    )

    suggested_meta_description: str = Field(
        description=(
            "The optimised meta description for the page. Must include the primary keyword "
            "naturally, have a clear call to action or value proposition, and fit within "
            "Google's display range."
        )
    )

    # ── Required fields (continued) ───────────────────────────────────────────

    change_notes: list[str] = Field(
        description=(
            "Brief notes explaining what was changed and why. "
            "Return an empty list [] when no notes are needed. "
            "Used in the subscriber-facing change summary."
        )
    )

    # ── Validators ────────────────────────────────────────────────────────────

    @field_validator("suggested_meta_title")
    @classmethod
    def validate_meta_title(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("suggested_meta_title must not be empty")
        if len(v) < 30:
            raise ValueError(
                f"suggested_meta_title is too short ({len(v)} chars) — minimum 30 characters"
            )
        if len(v) > 60:
            raise ValueError(
                f"suggested_meta_title is too long ({len(v)} chars) — maximum 60 characters"
            )
        return v

    @field_validator("suggested_meta_description")
    @classmethod
    def validate_meta_description(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("suggested_meta_description must not be empty")
        if len(v) < 100:
            raise ValueError(
                f"suggested_meta_description is too short ({len(v)} chars) — minimum 100 characters"
            )
        if len(v) > 165:
            raise ValueError(
                f"suggested_meta_description is too long ({len(v)} chars) — maximum 165 characters"
            )
        return v

    @field_validator("change_notes")
    @classmethod
    def validate_change_notes(cls, v: list[str]) -> list[str]:
        # Strip whitespace; drop empty strings silently (not a hard failure)
        return [note.strip() for note in v if note.strip()]


# ── Architecture notes (for future contract authors) ──────────────────────────
#
# 1. FIELD NAMES — the Pydantic model is the only place field names are defined.
#    They must NOT appear in SKILL.md, identity.md, or any prompt file.
#    With Structured Outputs, OpenAI enforces the schema at the API level.
#
# 2. VALIDATORS should check structure and constraints, not domain correctness.
#    "Is this a 30–65 char string?" is a validator.
#    "Is this title SEO-optimised?" is not — that is the agent's job.
#
# 3. STRICT MODE COMPATIBILITY — every field must be either required or nullable:
#    - Required (always returned, empty collection when not applicable):
#        change_notes: list[str]   # model returns [] when no notes
#    - Nullable (may be legitimately absent):
#        redirect_url: str | None = None
#    - FORBIDDEN: Field(default_factory=...) on non-nullable fields (strict mode breaks)
#
# 4. NESTED MODELS are fine for complex structures. Example:
#
#    class SignalScore(BaseModel):
#        score: int = Field(ge=0, le=100)
#        reason: str
#
#    class AnalyzerResponse(BaseModel):
#        keyword_signal: SignalScore
#        readability_signal: SignalScore
#
# 5. CONSTRAINED STRINGS must use Literal[...] for OpenAI-level enforcement:
#
#    from typing import Literal
#    severity: Literal["low", "medium", "high", "critical"]
