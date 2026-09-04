"""
SQLAlchemy engine, session factory, and dependency helpers.

SQLite only (spec constraint: no other infrastructure). The engine is
pointed at `settings.database_url`, which defaults to a file under
./data/ relative to the process CWD.

Two ways to get a session:

- `get_db()` — a FastAPI dependency that yields a session and closes
  it after the request. Use this in API routes.
- `get_session()` — a plain context manager for use outside a request
  (e.g. inside a service). Use this in repositories/services.
"""

from contextlib import contextmanager
from typing import Generator, Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency: yields a session for the lifetime of a request
    and always closes it, even on error.
    """

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


@contextmanager
def get_session() -> Iterator[Session]:
    """
    Plain context manager for use outside a request (e.g. inside a
    service). Yields a session and always closes it.
    """

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


def init_db() -> None:
    """
    Create all tables that don't exist yet. No Alembic — the spec
    explicitly avoids migration tooling for this hackathon.
    """

    Base.metadata.create_all(bind=engine)
