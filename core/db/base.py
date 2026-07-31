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
