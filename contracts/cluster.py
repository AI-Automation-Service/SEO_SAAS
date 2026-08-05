"""
contracts/cluster.py — Output contract for the seo-cluster agent.

The seo-cluster agent groups keywords into pillar-cluster (hub-spoke) topic clusters.
It is called in batches of up to 150 keywords and may be called multiple times for large
keyword sets; results are merged by the router across batches.

Output: two parallel arrays.
  - keywords: one entry per input keyword with cluster assignment + intent metadata.
  - clusters: one entry per cluster with the canonical hub keyword and URL.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ClusterKeyword(BaseModel):
    keyword: str = Field(description="Exact keyword string — must match the input exactly.")
    cluster: str = Field(description="Human-readable cluster name (2–4 words, Title Case).")
    cluster_id: str = Field(description="Kebab-case cluster identifier (lowercase, hyphens).")
    is_hub: bool = Field(description="True for the single hub keyword per cluster.")
    intent: Literal["informational", "commercial", "transactional", "navigational"] = Field(
        description="Primary search intent for this keyword."
    )
    funnel_stage: Literal["tofu", "mofu", "bofu"] = Field(
        description="Funnel stage: tofu=awareness, mofu=consideration, bofu=decision."
    )
    suggested_url: str = Field(
        description="Canonical URL path for this keyword's cluster (e.g. /ai-consulting)."
    )
    confidence: Literal["high", "medium", "low"] = Field(
        description="Confidence in the cluster assignment: high=clear, medium=some ambiguity, low=weak signals."
    )


class ClusterGroup(BaseModel):
    cluster: str = Field(description="Human-readable cluster name (2–4 words, Title Case).")
    cluster_id: str = Field(description="Kebab-case cluster identifier — matches ClusterKeyword.cluster_id.")
    hub_keyword: str = Field(description="The single hub keyword for this cluster (exact match to is_hub keyword).")
    intent: Literal["informational", "commercial", "transactional", "navigational"] = Field(
        description="Primary search intent for the cluster."
    )
    funnel_stage: Literal["tofu", "mofu", "bofu"] = Field(
        description="Funnel stage for the cluster."
    )
    suggested_url: str = Field(
        description="Canonical URL path for this cluster (shared by all keywords in the cluster)."
    )


class ClusterResponse(BaseModel):
    keywords: list[ClusterKeyword] = Field(
        description="One entry per input keyword. Every input keyword must appear exactly once."
    )
    clusters: list[ClusterGroup] = Field(
        description="One entry per cluster. Each cluster has exactly one hub keyword."
    )
