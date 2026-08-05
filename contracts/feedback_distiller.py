"""
contracts/feedback_distiller.py — Output contract for the feedback-distiller agent.

The feedback-distiller analyses subscriber approval/rejection patterns over up to 30
recent feedback entries and distils them into up to 10 actionable content-style rules.
These rules are stored in ProjectPreferences and injected into future agent prompts to
personalise output for each subscriber.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class FeedbackDistillerResponse(BaseModel):
    rules: list[str] = Field(
        description=(
            "Up to 10 concrete, actionable style/content rules derived from the subscriber's "
            "approval and rejection history. Each rule is a direct instruction for an AI agent "
            "(e.g. 'Always open with a direct answer in the first sentence'). "
            "Return an empty list [] when no clear patterns can be derived."
        )
    )

    @field_validator("rules")
    @classmethod
    def validate_rules(cls, v: list[str]) -> list[str]:
        cleaned = [r.strip() for r in v if r.strip()]
        return cleaned[:10]
