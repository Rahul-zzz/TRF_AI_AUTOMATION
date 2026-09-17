"""Engine/session management. SQLite file lives under data/ by default."""

from __future__ import annotations

import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config.settings import SETTINGS
from database.models import Base

_engine = None
_SessionLocal = None


def get_engine(db_path: str | None = None):
    global _engine
    if _engine is None:
        path = db_path or SETTINGS.database_path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        _engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    return _engine


def get_session_factory(db_path: str | None = None):
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(db_path), expire_on_commit=False)
    return _SessionLocal


def init_db(db_path: str | None = None):
    """Create all tables if they do not already exist. Never drops data."""
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    return engine


@contextmanager
def session_scope(db_path: str | None = None):
    """Provide a transactional scope for a series of operations."""
    session_factory = get_session_factory(db_path)
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_engine_for_testing():
    """Used only by tests to point at a fresh in-memory/tempfile DB."""
    global _engine, _SessionLocal
    _engine = None
    _SessionLocal = None
