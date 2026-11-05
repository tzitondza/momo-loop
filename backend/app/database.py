"""PostgreSQL database setup for auth and saved scenarios."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Load backend/.env then project-root .env
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ROOT_DIR = _BACKEND_DIR.parent
load_dotenv(_BACKEND_DIR / ".env")
load_dotenv(_ROOT_DIR / ".env")

DEFAULT_DATABASE_URL = "postgresql+psycopg://momo:momo@127.0.0.1:5432/momo_loop"


def _normalize_database_url(url: str) -> str:
    """Accept common hosted URLs (postgres://, postgresql://) for SQLAlchemy+psycopg."""
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://") and "+psycopg" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


DATABASE_URL = _normalize_database_url(os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL))

engine_kwargs: dict = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
