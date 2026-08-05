"""
contracts/article.py — Output contracts for the seo-article-writer agent.

The article writer uses a three-phase pipeline. Each phase uses a different contract:

  Phase 1 (ArticlePhase1Response): outline + first third of article (intro + 3 H2s)
  Phase 2 (ArticlePhase2Response): middle body sections
  Phase 3 (ArticlePhase3Response): FAQ section + Conclusion

Because one agent produces three different JSON shapes (one per call), the registry holds
ArticlePhase1Response as the primary contract (for compose() compatibility), while the
router explicitly passes the phase-appropriate contract on each SkillAgent.run() call.

Usage in article.py router:
    phase1 = ArticlePhase1Response.model_validate_json(
        agent.run(p1_msg, output_mode="structured", contract=ArticlePhase1Response, ...)
    )
    phase2 = ArticlePhase2Response.model_validate_json(
        agent.run(p2_msg, output_mode="structured", contract=ArticlePhase2Response, ...)
    )
    phase3 = ArticlePhase3Response.model_validate_json(
        agent.run(p3_msg, output_mode="structured", contract=ArticlePhase3Response, ...)
    )
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

SchemaType = Literal["Article", "BlogPosting", "NewsArticle"]


class ArticlePhase1Response(BaseModel):
    """Outline + first third of the article (intro + 3 H2 sections)."""

    meta_title: str = Field(
        description="SEO meta title, 50–60 characters, containing the primary keyword."
    )
    meta_description: str = Field(
        description="Meta description, 140–160 characters, keyword + clear value proposition."
    )
    slug: str = Field(
        description="URL slug: lowercase, hyphens, no stop words."
    )
    h1: str = Field(
        description="Article headline — contains the primary keyword, closely mirrors meta_title."
    )
    schema_type: SchemaType = Field(
        description="Recommended JSON-LD schema type for this article."
    )
    sections_outline: list[str] = Field(
        description="Headings of the 3 H2 sections covered in Phase 1 (plain text, no tags)."
    )
    content_phase1: str = Field(
        description="Full HTML for Phase 1: intro + 3 H2 sections. HTML tags only, no Markdown."
    )
    sections_remaining: list[str] = Field(
        description="Headings of the H2 sections still to be written in Phase 2 (plain text, no tags)."
    )


class ArticlePhase2Response(BaseModel):
    """Middle body H2 sections (continuing from Phase 1)."""

    content_phase2: str = Field(
        description="Full HTML for the middle body sections. HTML tags only, no Markdown."
    )
    schema_json_ld: str = Field(
        description=(
            "Complete <script type='application/ld+json'>...</script> block. "
            "Used as fallback if the dedicated seo-schema call fails."
        )
    )


class ArticlePhase3Response(BaseModel):
    """FAQ section (5 H3 Q&A items) + Conclusion."""

    content_phase3: str = Field(
        description=(
            "Full HTML for the FAQ section and Conclusion. "
            "Exactly 5 FAQ H3 questions followed by paragraph answers, then a Conclusion H2. "
            "HTML tags only, no Markdown."
        )
    )
