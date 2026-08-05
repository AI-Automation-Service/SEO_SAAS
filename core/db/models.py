from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base


class CronJob(Base):
    """Scheduled job definition per project."""

    __tablename__ = "cron_jobs"
    __table_args__ = (
        UniqueConstraint("user_id", "project_name", "job_type", name="uq_cron_job"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    project_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    # gsc_sync / ranking_monitor / content_refresh / content_calendar / cluster_improve / meta_audit
    job_type: Mapped[str] = mapped_column(String, nullable=False)
    frequency_days: Mapped[int] = mapped_column(Integer, default=7)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CronRun(Base):
    """Log of individual cron job executions."""

    __tablename__ = "cron_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cron_job_id: Mapped[int] = mapped_column(Integer, ForeignKey("cron_jobs.id"), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    changes_created: Mapped[int] = mapped_column(Integer, default=0)
    auto_applied: Mapped[int] = mapped_column(Integer, default=0)
    # running / success / error
    status: Mapped[str] = mapped_column(String, default="running")
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)


class ProjectFeedback(Base):
    """Subscriber feedback on individual PageChanges (approve/reject + optional comment)."""

    __tablename__ = "project_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    project_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    change_id: Mapped[int] = mapped_column(Integer, ForeignKey("page_changes.id"), nullable=False)
    # approve / reject
    verdict: Mapped[str] = mapped_column(String, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProjectPreferences(Base):
    """Distilled style/content rules extracted from subscriber feedback history."""

    __tablename__ = "project_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "project_name", name="uq_project_prefs"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    project_name: Mapped[str] = mapped_column(String, nullable=False)
    # List of up to 10 distilled rules as JSON
    rules: Mapped[list | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AIHistory(Base):
    """Logs every agent AI call: tokens, cost, duration, outcome."""

    __tablename__ = "ai_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    project_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    agent_name: Mapped[str] = mapped_column(String, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    # success / error
    status: Mapped[str] = mapped_column(String, default="success")
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    # links to a PageChange if this call produced one
    change_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("page_changes.id"), nullable=True)
    # groups Phase 1 + Phase 2 calls for the same article
    article_job_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


_ALL_CAPABILITIES = [
    "AI_WRITER", "GSC", "GA4", "CRON", "DATAFORSEO", "SEMRUSH", "AHREFS", "MOZ",
    "COMPETITOR", "FLOW", "PLAGIARISM_CHECK", "AUTOPILOT", "FEEDBACK_LOOP",
    "MULTI_PROJECT", "SHOPIFY", "API_ACCESS",
]

_DEFAULT_CAPABILITIES: dict = {cap: True for cap in _ALL_CAPABILITIES}


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, server_default=text('false'), default=False)
    plan: Mapped[str] = mapped_column(String, default="free")
    max_projects: Mapped[int] = mapped_column(Integer, default=3)
    # JSON dict of capability flags — all enabled by default (single-user platform)
    capabilities: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def get_capabilities(self) -> dict:
        if self.capabilities:
            return {**_DEFAULT_CAPABILITIES, **self.capabilities}
        return dict(_DEFAULT_CAPABILITIES)

    def has_capability(self, flag: str) -> bool:
        return self.get_capabilities().get(flag, True)


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
    """Stores before/after content for every CMS change. Enables approval, rollback, and autopilot."""

    __tablename__ = "page_changes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    project_name: Mapped[str] = mapped_column(String, nullable=False, index=True)

    # Routing
    # page_edit / meta_edit / new_draft / product_edit / collection_edit
    action_type: Mapped[str] = mapped_column(String, default="page_edit")
    # wordpress / shopify
    platform: Mapped[str] = mapped_column(String, default="wordpress")
    source_agent: Mapped[str | None] = mapped_column(String, nullable=True)
    # foundation / expansion / scale / authority
    plan_phase: Mapped[str | None] = mapped_column(String, nullable=True)
    cron_job_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Cluster / keyword context
    cluster_name: Mapped[str] = mapped_column(String, nullable=False)

    # WordPress fields
    wp_post_id: Mapped[int] = mapped_column(Integer, nullable=False)
    wp_post_url: Mapped[str] = mapped_column(String, nullable=False)
    wp_post_type: Mapped[str] = mapped_column(String, default="post")  # post / page

    # Content
    original_content: Mapped[str] = mapped_column(Text, nullable=False)
    new_content: Mapped[str] = mapped_column(Text, nullable=False)
    change_summary: Mapped[str] = mapped_column(Text, nullable=False)
    changes_made: Mapped[list | None] = mapped_column(JSON, nullable=True)
    statistics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    meta_updates: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # new_draft fields
    draft_title: Mapped[str | None] = mapped_column(String, nullable=True)
    draft_slug: Mapped[str | None] = mapped_column(String, nullable=True)
    draft_word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Shopify fields
    shopify_resource_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    shopify_resource_type: Mapped[str | None] = mapped_column(String, nullable=True)

    # Plagiarism
    plagiarism_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    plagiarism_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    plagiarism_report: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # clean / flagged / rewritten / skipped
    plagiarism_status: Mapped[str] = mapped_column(String, default="skipped")

    # Subscriber interaction
    rejection_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    # subscriber / autopilot
    applied_by: Mapped[str | None] = mapped_column(String, nullable=True)

    # pending / approved / rolled_back / no_action
    status: Mapped[str] = mapped_column(String, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
