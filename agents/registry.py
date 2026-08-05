"""
agents/registry.py — Single source of truth for all agent configuration.

Every agent in SEO OS that goes through SkillAgent/BaseAgent is registered here.
No router hard-codes a model name, timeout, or shared document list.

output_mode values:
    "structured"  — OpenAI Structured Outputs (standard for all Pydantic agents)
    "json_mode"   — json_object fallback (model predates SO, or contract not yet written)
    "markdown"    — no response_format; agent returns Markdown prose

Strict mode contract rule (for output_mode="structured"):
    All fields must be either required (no default) or nullable (Type | None = None).
    No Field(default_factory=...) on non-nullable fields.
    See contracts/README.md for the full rules.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Type

from pydantic import BaseModel

from contracts.meta import MetaResponse

# ── Shared-doc list constants — named to avoid repeated literals ───────────────

_JSON_ONLY = ["json-output-discipline"]
_SEO_JSON  = ["seo-standards", "json-output-discipline"]
_SEO_NAV   = ["seo-standards", "internal-linking"]
_FULL_EDIT = ["writing-rules", "eeat-framework", "seo-standards", "internal-linking", "json-output-discipline"]
_FULL_WRITE = ["writing-rules", "eeat-framework", "seo-standards", "internal-linking", "content-safety", "json-output-discipline"]


@dataclass
class AgentConfig:
    name: str
    model: str
    temperature: float
    timeout: int
    max_tokens: int
    output_mode: Literal["structured", "json_mode", "markdown"]
    shared_docs: list[str]
    capabilities: list[str]
    description: str
    contract: Type[BaseModel] | None = field(default=None)

    def __post_init__(self) -> None:
        valid_modes = {"structured", "json_mode", "markdown"}
        if self.output_mode not in valid_modes:
            raise ValueError(
                f"Agent '{self.name}': invalid output_mode {self.output_mode!r}. "
                f"Valid values: {sorted(valid_modes)}"
            )


# ── Agent entries ──────────────────────────────────────────────────────────────

_ENTRIES: list[AgentConfig] = [

    # ── JSON-output agents — standard Structured Outputs path ──────────────────

    AgentConfig(
        name="seo-meta",
        model="gpt-4o-mini",
        temperature=0.3,
        timeout=45,
        max_tokens=600,
        output_mode="structured",
        shared_docs=_SEO_JSON,
        contract=MetaResponse,
        capabilities=["AI_WRITER"],
        description="Generates optimised meta title and description for theme-controlled or archive pages.",
    ),

    AgentConfig(
        name="seo-analyzer",
        model="gpt-4o-mini",
        temperature=0.3,
        timeout=60,
        max_tokens=1200,
        output_mode="json_mode",   # TODO: migrate to "structured" → create contracts/analyzer.py
        shared_docs=["eeat-framework", "seo-standards", "json-output-discipline"],
        contract=None,
        capabilities=["AI_WRITER"],
        description="Analyzes page content against 9 SEO signals and outputs a structured improvement plan.",
    ),

    AgentConfig(
        name="seo-editor",
        model="gpt-4o",
        temperature=0.55,
        timeout=120,
        max_tokens=4000,
        output_mode="json_mode",   # TODO: migrate to "structured" → create contracts/editor.py
        shared_docs=_FULL_EDIT,
        contract=None,
        capabilities=["AI_WRITER"],
        description="Rewrites page HTML to improve on-page SEO signals while preserving content intent.",
    ),

    AgentConfig(
        name="seo-cluster",
        model="gpt-4o-mini",
        temperature=0.3,
        timeout=60,
        max_tokens=2000,
        output_mode="json_mode",   # TODO: migrate to "structured" → create contracts/cluster.py
        shared_docs=_JSON_ONLY,
        contract=None,
        capabilities=["AI_WRITER"],
        description="Groups keywords into hub-and-spoke clusters and assigns primary/secondary intent.",
    ),

    AgentConfig(
        name="seo-schema",
        model="gpt-4o-mini",
        temperature=0.3,
        timeout=60,
        max_tokens=1000,
        output_mode="json_mode",   # TODO: migrate to "structured" → create contracts/schema.py
        shared_docs=_JSON_ONLY,
        contract=None,
        capabilities=["AI_WRITER"],
        description="Generates JSON-LD schema markup for a page based on its type and content.",
    ),

    AgentConfig(
        name="seo-article-writer",
        model="gpt-4o",
        temperature=0.7,           # at cap; do not increase
        timeout=180,
        max_tokens=2500,
        output_mode="json_mode",   # TODO: migrate to "structured" → create contracts/article.py
        shared_docs=_FULL_WRITE,
        contract=None,
        capabilities=["AI_WRITER"],
        description="Writes long-form SEO articles in three phases: outline, draft, optimise.",
    ),

    AgentConfig(
        name="humanizer",
        model="gpt-4o-mini",
        temperature=0.7,           # at cap; do not increase
        timeout=60,
        max_tokens=3000,
        output_mode="json_mode",   # TODO: migrate to "structured" → create contracts/humanizer.py
        shared_docs=["writing-rules", "json-output-discipline"],
        contract=None,
        capabilities=["AI_WRITER"],
        description="Rewrites AI-generated text to remove detectable AI patterns while preserving meaning.",
    ),

    AgentConfig(
        name="feedback-distiller",
        model="gpt-4o-mini",
        temperature=0.3,
        timeout=45,
        max_tokens=500,
        output_mode="json_mode",   # TODO: migrate to "structured" → create contracts/feedback_distiller.py
        shared_docs=_JSON_ONLY,
        contract=None,
        capabilities=["AI_WRITER", "FEEDBACK_LOOP"],
        description="Distils subscriber approval/rejection patterns into persistent preference rules.",
    ),

    # ── Shopify variant agents ─────────────────────────────────────────────────

    AgentConfig(
        name="seo-analyzer-shopify",
        model="gpt-4o-mini",
        temperature=0.3,
        timeout=60,
        max_tokens=1200,
        output_mode="json_mode",
        shared_docs=_SEO_JSON,
        contract=None,
        capabilities=["AI_WRITER", "SHOPIFY"],
        description="Analyzes Shopify page content for SEO signals (Shopify variant of seo-analyzer).",
    ),

    AgentConfig(
        name="seo-editor-shopify",
        model="gpt-4o",
        temperature=0.55,
        timeout=120,
        max_tokens=4000,
        output_mode="json_mode",
        shared_docs=["writing-rules", "seo-standards", "json-output-discipline"],
        contract=None,
        capabilities=["AI_WRITER", "SHOPIFY"],
        description="Edits Shopify page content for SEO (Shopify variant of seo-editor).",
    ),

    AgentConfig(
        name="seo-meta-shopify",
        model="gpt-4o-mini",
        temperature=0.3,
        timeout=45,
        max_tokens=600,
        output_mode="json_mode",
        shared_docs=_SEO_JSON,
        contract=None,
        capabilities=["AI_WRITER", "SHOPIFY"],
        description="Generates meta title and description for Shopify pages (Shopify variant of seo-meta).",
    ),

    # ── Markdown-output agents (no response_format) ───────────────────────────

    AgentConfig(
        name="seo-plan",
        model="gpt-4o",
        temperature=0.65,
        timeout=180,
        max_tokens=4000,
        output_mode="markdown",
        shared_docs=_SEO_NAV,
        contract=None,
        capabilities=["AI_WRITER"],
        description="Generates a structured SEO execution plan for a project.",
    ),

    AgentConfig(
        name="content-strategy",
        model="gpt-4o",
        temperature=0.65,
        timeout=180,
        max_tokens=4000,
        output_mode="markdown",
        shared_docs=["writing-rules", "eeat-framework", "seo-standards", "internal-linking", "content-safety"],
        contract=None,
        capabilities=["AI_WRITER"],
        description="Produces a content strategy and gap analysis for a keyword cluster.",
    ),

    AgentConfig(
        name="site-architecture",
        model="gpt-4o",
        temperature=0.65,
        timeout=180,
        max_tokens=4000,
        output_mode="markdown",
        shared_docs=_SEO_NAV,
        contract=None,
        capabilities=["AI_WRITER"],
        description="Designs a recommended site architecture and internal link structure.",
    ),

    AgentConfig(
        name="seo-flow",
        model="gpt-4o",
        temperature=0.65,
        timeout=120,
        max_tokens=4000,
        output_mode="markdown",
        shared_docs=_SEO_NAV,
        contract=None,
        capabilities=["AI_WRITER"],
        description="Maps the user journey and conversion flow for a target keyword.",
    ),

    AgentConfig(
        name="seo-page",
        model="gpt-4o",
        temperature=0.65,
        timeout=120,
        max_tokens=4000,
        output_mode="markdown",
        shared_docs=["writing-rules", "eeat-framework", "seo-standards"],
        contract=None,
        capabilities=["AI_WRITER"],
        description="Generates a page brief with recommended structure and content angle.",
    ),

    AgentConfig(
        name="seo-technical",
        model="gpt-4o",
        temperature=0.3,
        timeout=120,
        max_tokens=3000,
        output_mode="markdown",
        shared_docs=[],
        contract=None,
        capabilities=["AI_WRITER"],
        description="Interprets technical SEO audit data and produces a prioritized action report.",
    ),

    AgentConfig(
        name="seo-competitor-pages",
        model="gpt-4o",
        temperature=0.65,
        timeout=180,
        max_tokens=4000,
        output_mode="markdown",
        shared_docs=["eeat-framework", "seo-standards"],
        contract=None,
        capabilities=["AI_WRITER"],
        description="Analyzes competitor page structures and recommends differentiation strategies.",
    ),
]

# ── Build and validate REGISTRY ────────────────────────────────────────────────

_names = [e.name for e in _ENTRIES]
assert len(_names) == len(set(_names)), (
    f"Duplicate agent names in registry: "
    f"{[n for n in _names if _names.count(n) > 1]}"
)

REGISTRY: dict[str, AgentConfig] = {e.name: e for e in _ENTRIES}


def get(name: str) -> AgentConfig:
    """Look up an agent by name. Raises KeyError with known-agent list for unknown agents."""
    try:
        return REGISTRY[name]
    except KeyError:
        raise KeyError(
            f"Agent '{name}' is not registered. "
            f"Known agents: {sorted(REGISTRY)}"
        )
