import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def _make_engine():
    url = os.environ.get("DATABASE_URL", "sqlite:///./seo_os.db")
    kwargs = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}
    return create_engine(url, **kwargs)


engine = _make_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def create_tables() -> None:
    from core.db import models  # noqa: F401 — import triggers model registration
    Base.metadata.create_all(bind=engine)
    _migrate_columns()


def _migrate_columns() -> None:
    """Add columns that don't exist yet without dropping the table."""
    from sqlalchemy import text as sql_text

    _migrations = [
        # users
        "ALTER TABLE users ADD COLUMN onboarding_complete BOOLEAN DEFAULT TRUE",
        # keywords
        "ALTER TABLE keywords ADD COLUMN page_type TEXT",
        # site_pages
        "ALTER TABLE site_pages ADD COLUMN page_type TEXT DEFAULT 'unknown'",
        # page_changes — v2 routing fields
        "ALTER TABLE page_changes ADD COLUMN action_type TEXT DEFAULT 'page_edit'",
        "ALTER TABLE page_changes ADD COLUMN platform TEXT DEFAULT 'wordpress'",
        "ALTER TABLE page_changes ADD COLUMN source_agent TEXT",
        "ALTER TABLE page_changes ADD COLUMN plan_phase TEXT",
        "ALTER TABLE page_changes ADD COLUMN cron_job_id INTEGER",
        # page_changes — new_draft fields
        "ALTER TABLE page_changes ADD COLUMN draft_title TEXT",
        "ALTER TABLE page_changes ADD COLUMN draft_slug TEXT",
        "ALTER TABLE page_changes ADD COLUMN draft_word_count INTEGER",
        # page_changes — Shopify fields
        "ALTER TABLE page_changes ADD COLUMN shopify_resource_id INTEGER",
        "ALTER TABLE page_changes ADD COLUMN shopify_resource_type TEXT",
        # page_changes — plagiarism fields
        "ALTER TABLE page_changes ADD COLUMN plagiarism_flag BOOLEAN DEFAULT FALSE",
        "ALTER TABLE page_changes ADD COLUMN plagiarism_score REAL",
        "ALTER TABLE page_changes ADD COLUMN plagiarism_report TEXT",
        "ALTER TABLE page_changes ADD COLUMN plagiarism_status TEXT DEFAULT 'skipped'",
        # page_changes — subscriber interaction
        "ALTER TABLE page_changes ADD COLUMN rejection_reason TEXT",
        "ALTER TABLE page_changes ADD COLUMN applied_by TEXT",
        # users — capability flags
        "ALTER TABLE users ADD COLUMN capabilities TEXT",
    ]

    with engine.connect() as conn:
        for stmt in _migrations:
            try:
                conn.execute(sql_text(stmt))
                conn.commit()
            except Exception:
                pass  # column already exists — idempotent
