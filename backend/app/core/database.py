"""
app/core/database.py

Async SQLAlchemy 2.0 database setup.

Design decisions:
  - AsyncEngine + async_sessionmaker: FastAPI is async-native; blocking DB calls
    would waste the event loop.
  - expire_on_commit=False: prevents lazy-loading errors after commit in async
    code where the session may already be closed.
  - pool_pre_ping=True: detect stale connections in the pool without impacting
    healthy connections.
  - NullPool for tests: avoids shared state between test cases.
"""
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models.

    All models must inherit from this class so Alembic can discover them
    via ``target_metadata = Base.metadata``.
    """
    pass


def build_engine(database_url: str | None = None):
    """Build an async SQLAlchemy engine.

    Args:
        database_url: Override for testing (e.g. SQLite).
    """
    url = database_url or settings.DATABASE_URL
    kwargs: dict = {"echo": settings.APP_ENV == "development", "pool_pre_ping": True}
    if not url.startswith("sqlite"):
        kwargs["pool_size"]    = 10
        kwargs["max_overflow"] = 20
    return create_async_engine(url, **kwargs)


# Module-level engine and session factory (singleton).
engine = build_engine()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncSession:  # type: ignore[override]
    """FastAPI dependency that yields a DB session per request.

    Ensures the session is always closed, even on exceptions.
    The caller controls commit/rollback — services call db.commit().
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
