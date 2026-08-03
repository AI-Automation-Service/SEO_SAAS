from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, server_default=text('false'), default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UserApiKey(Base):
    """Fernet-encrypted per-user API key storage. One row per (user, service) pair."""

    __tablename__ = "user_api_keys"
    __table_args__ = (UniqueConstraint("user_id", "service", name="uq_user_service"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    service: Mapped[str] = mapped_column(String, nullable=False)
    encrypted_value: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Keyword(Base):
    """Per-project keyword with GSC metrics, planner data, and cluster assignments."""

    __tablename__ = "keywords"
    __table_args__ = (
        UniqueConstraint("user_id", "project_name", "keyword", name="uq_user_project_keyword"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    project_name: Mapped[str] = mapped_column(String, nullable=False, index=True)

    # Core
    keyword: Mapped[str] = mapped_column(String, nullable=False)
    # standard / question / branded / competitor
    keyword_type: Mapped[str] = mapped_column(String, default="standard")

    # Cluster assignment (set by AI agent)
    cluster: Mapped[str | None] = mapped_column(String, nullable=True)
    is_hub: Mapped[bool] = mapped_column(Boolean, default=False)

    # Intent & funnel
    # informational / commercial / navigational / transactional
    intent: Mapped[str | None] = mapped_column(String, nullable=True)
    # tofu / mofu / bofu
    funnel_stage: Mapped[str | None] = mapped_column(String, nullable=True)

    # Status & action (computed + overridable)
    # covered / quick_win / opportunity / gap / watch
    status: Mapped[str] = mapped_column(String, default="gap")
    # new_pillar / optimize_pillar / add_spoke / rewrite / watch / none
    action: Mapped[str] = mapped_column(String, default="none")

    # Keyword Planner data
    volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    competition: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0.0–1.0

    # GSC data
    clicks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    impressions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    position: Mapped[float | None] = mapped_column(Float, nullable=True)
    ctr: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Page data
    existing_url: Mapped[str | None] = mapped_column(String, nullable=True)
    suggested_url: Mapped[str | None] = mapped_column(String, nullable=True)

    # Flags
    snippet_opportunity: Mapped[bool] = mapped_column(Boolean, default=False)
    competitor_gap: Mapped[bool] = mapped_column(Boolean, default=False)

    # gsc / planner / both / manual / sitemap
    source: Mapped[str] = mapped_column(String, default="manual")
    # page / post / unknown — set for sitemap-derived keywords
    page_type: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProjectKnowledge(Base):
    """Per-project knowledge base — injected as context into every AI agent prompt."""

    __tablename__ = "project_knowledge"
    __table_args__ = (
        UniqueConstraint("user_id", "project_name", name="uq_project_knowledge"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    project_name: Mapped[str] = mapped_column(String, nullable=False)

    about: Mapped[str | None] = mapped_column(String, nullable=True)
    products_services: Mapped[str | None] = mapped_column(String, nullable=True)
    target_audience: Mapped[str | None] = mapped_column(String, nullable=True)
    brand_voice: Mapped[str | None] = mapped_column(String, nullable=True)
    competitors_notes: Mapped[str | None] = mapped_column(String, nullable=True)
    seo_context: Mapped[str | None] = mapped_column(String, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class StrategyOutput(Base):
    """Persisted AI-generated strategy output per project per type."""

    __tablename__ = "strategy_outputs"
    __table_args__ = (
        UniqueConstraint("user_id", "project_name", "strategy_type", name="uq_strategy_output"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    project_name: Mapped[str] = mapped_column(String, nullable=False)
    strategy_type: Mapped[str] = mapped_column(String, nullable=False)  # plan / content / architecture / competitor
    output: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SitePage(Base):
    """URLs extracted from the site's XML sitemap."""

    __tablename__ = "site_pages"
    __table_args__ = (
        UniqueConstraint("user_id", "project_name", "url", name="uq_sitepage"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    project_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    url: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, nullable=False)
    page_type: Mapped[str] = mapped_column(String, default="unknown")  # page / post / unknown
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PageChange(Base):
    """Stores before/after content for every WordPress page improvement. Enables rollback."""

    __tablename__ = "page_changes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    project_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    cluster_name: Mapped[str] = mapped_column(String, nullable=False)
    wp_post_id: Mapped[int] = mapped_column(Integer, nullable=False)
    wp_post_url: Mapped[str] = mapped_column(String, nullable=False)
    wp_post_type: Mapped[str] = mapped_column(String, default="post")  # post / page
    original_content: Mapped[str] = mapped_column(Text, nullable=False)
    new_content: Mapped[str] = mapped_column(Text, nullable=False)
    change_summary: Mapped[str] = mapped_column(Text, nullable=False)
    changes_made: Mapped[list | None] = mapped_column(JSON, nullable=True)
    statistics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    meta_updates: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # pending / approved / rolled_back / no_action
    status: Mapped[str] = mapped_column(String, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
