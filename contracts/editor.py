"""
contracts/editor.py — Output contract for the seo-editor agent.

The seo-editor receives the analyzer's recommendation list and applies exactly those
changes to the page's HTML content. It also always generates suggested meta title and
description, even when is_theme_controlled=True (meta fields are always writable).

The router uses changes_made to build the human-readable change summary,
new_content to update WordPress, and the meta fields for Yoast/RankMath updates.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

ChangeType = Literal[
    "direct_answer",
    "heading_structure",
    "internal_link",
    "schema",
    "faq_opportunity",
    "aeo_structure",
    "author_date",
    "content_freshness",
    "images_alt",
]
ChangeStatus = Literal["applied", "skipped"]


class ChangeEntry(BaseModel):
    type: ChangeType = Field(description="The type of SEO change attempted.")
    status: ChangeStatus = Field(
        description="applied=change was made, skipped=change was not applicable or already present."
    )
    location: str = Field(description="Brief description of where in the content the change was applied.")
    description: str = Field(description="One sentence describing exactly what was added or modified.")


class EditorResponse(BaseModel):
    action_needed: bool = Field(
        description="True if at least one change was applied to the content."
    )
    suggested_meta_title: str = Field(
        description=(
            "Optimised meta title for the page. Maximum 60 characters. "
            "Must contain the primary keyword. Returns the existing title unchanged "
            "if it is already well-optimised."
        )
    )
    suggested_meta_description: str = Field(
        description=(
            "Optimised meta description for the page. 140–155 characters. "
            "Answers search intent and ends with a value proposition or call to action. "
            "Returns the existing description unchanged if it is already well-optimised."
        )
    )
    changes_made: list[ChangeEntry] = Field(
        description="One entry per recommendation processed. Empty list when action_needed is false."
    )
    new_content: str = Field(
        description=(
            "The COMPLETE modified page HTML. Must be identical to the input html_content "
            "when is_theme_controlled is true or when no changes were applied."
        )
    )
    confidence: Literal["high", "medium", "low"] = Field(
        description="Editor's confidence in the output quality."
    )
    no_action_reason: str | None = Field(
        description=(
            "Explanation when no content changes were made "
            "(e.g. page is already optimised, or is_theme_controlled). "
            "Null when action_needed is true."
        )
    )

    @field_validator("suggested_meta_title")
    @classmethod
    def strip_meta_title(cls, v: str) -> str:
        return v.strip()

    @field_validator("suggested_meta_description")
    @classmethod
    def strip_meta_desc(cls, v: str) -> str:
        return v.strip()
