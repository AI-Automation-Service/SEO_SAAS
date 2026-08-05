"""
contracts/analyzer.py — Output contract for the seo-analyzer agent.

The seo-analyzer evaluates a WordPress page against 9 AEO/GEO SEO signals and outputs
a structured improvement plan. It is always called as Step 1 in the improve pipeline;
its output is passed directly to the seo-editor as the recommendations list.

The recommendations array MUST contain exactly 9 items in this canonical order:
  direct_answer, heading_structure, internal_link, schema, author_date,
  aeo_structure, faq_opportunity, content_freshness, images_alt
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

SignalType = Literal[
    "direct_answer",
    "heading_structure",
    "internal_link",
    "schema",
    "author_date",
    "aeo_structure",
    "faq_opportunity",
    "content_freshness",
    "images_alt",
]
SignalStatus = Literal["needed", "not_needed", "skipped"]
Severity = Literal["high", "medium", "low"]
PageType = Literal["blog_post", "article", "service", "landing"]
ConfidenceLevel = Literal["high", "medium", "low"]

_CANONICAL_ORDER: list[str] = [
    "direct_answer", "heading_structure", "internal_link", "schema",
    "author_date", "aeo_structure", "faq_opportunity", "content_freshness", "images_alt",
]


class AnalyzerStatistics(BaseModel):
    word_count: int = Field(description="Visible word count (all HTML tags stripped).")
    h1_count: int = Field(description="Number of <h1> tags in the full page.")
    h2_count: int = Field(description="Number of <h2> tags in the full page.")
    internal_link_count: int = Field(description="Total <a href> links in main content (not nav/footer).")
    hub_link_count: int = Field(description="Number of links whose href matches the hub_url path.")
    has_article_schema: bool = Field(description="True if a valid Article/BlogPosting/NewsArticle schema block exists.")
    author_visible: bool = Field(description="True if author name appears as visible text in main content.")
    date_visible: bool = Field(description="True if any date appears as visible text in main content.")
    images_missing_alt: int = Field(description="Count of <img> elements in main content without descriptive alt text.")


class Recommendation(BaseModel):
    type: SignalType = Field(description="The SEO signal being evaluated.")
    status: SignalStatus = Field(description="needed=action required, not_needed=already satisfied, skipped=not applicable.")
    severity: Severity = Field(description="Impact level if status is needed.")
    reason: str = Field(description="One sentence explaining the status assignment.")
    target_url: str | None = Field(
        description="The hub_url when type is internal_link and status is needed; null otherwise."
    )


class AnalyzerResponse(BaseModel):
    action_needed: bool = Field(
        description="True if at least one recommendation has status 'needed'."
    )
    page_type: PageType = Field(
        description="Detected page type: blog_post, article, service, or landing."
    )
    confidence: ConfidenceLevel = Field(
        description="Confidence in the analysis: high=full HTML, medium=partial, low=near-empty page."
    )
    summary: str = Field(
        description="2–3 sentence plain-English summary of the page's current state and what it needs."
    )
    statistics: AnalyzerStatistics = Field(
        description="Raw metrics computed from the page HTML."
    )
    recommendations: list[Recommendation] = Field(
        description=(
            "Exactly 9 recommendations in canonical order: "
            "direct_answer, heading_structure, internal_link, schema, author_date, "
            "aeo_structure, faq_opportunity, content_freshness, images_alt."
        )
    )
    no_action_reason: str | None = Field(
        description=(
            "Explanation of why no action is needed when action_needed is false "
            "(all recommendations are not_needed or skipped). Null when action_needed is true."
        )
    )

    @field_validator("recommendations")
    @classmethod
    def validate_recommendations_order(cls, v: list[Recommendation]) -> list[Recommendation]:
        if len(v) != 9:
            raise ValueError(f"expected exactly 9 recommendations, got {len(v)}")
        actual_types = [r.type for r in v]
        if actual_types != _CANONICAL_ORDER:
            raise ValueError(
                f"recommendations must be in canonical order {_CANONICAL_ORDER}, got {actual_types}"
            )
        return v
