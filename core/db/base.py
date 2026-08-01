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
    with engine.connect() as conn:
        # onboarding_complete: existing users default TRUE (already set up), new users FALSE via ORM
        try:
            conn.execute(sql_text(
                "ALTER TABLE users ADD COLUMN onboarding_complete BOOLEAN DEFAULT TRUE"
            ))
            conn.commit()
        except Exception:
            pass  # column already exists
