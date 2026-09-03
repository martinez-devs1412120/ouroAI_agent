"""api/database.py — lazy database connection.

The app MUST be importable and runnable even when no Postgres is
available — that's the constraint from the spec, and it matches
real-world onboarding (devs don't have Postgres running on every
laptop). The lazy-engine design below means importing this module
never tries to connect; the connection only happens when get_db()
is called and a route actually asks for a session.

When the database is real, FastAPI's dependency-injection will call
get_db() on every request, the engine connects on first use, and
sessions are short-lived (one per request)."""

from __future__ import annotations

from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from api.config import settings

_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


def get_engine() -> Engine:
    """Lazily create the SQLAlchemy engine. The first call connects;
    subsequent calls reuse the same engine. If Postgres isn't reachable
    the FIRST call raises; idle imports do not."""
    global _engine
    if _engine is None:
        # echo=settings.debug so SQL only shows up in dev. Pool of 5 +
        # 10s timeout is the sane default for a small API.
        _engine = create_engine(
            settings.database_url,
            echo=settings.debug,
            pool_size=5,
            pool_pre_ping=True,
            pool_recycle=10,
            connect_args={"connect_timeout": 5},
        )
    return _engine


def get_session_factory() -> sessionmaker:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
    return _SessionLocal


def get_db() -> Iterator[Session]:
    """FastAPI dependency. Yields a session, closes it after the request.
    Use as:  db: Session = Depends(get_db)"""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
