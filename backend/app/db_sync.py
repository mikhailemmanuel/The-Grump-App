"""
Synchronous SQLAlchemy engine + session for Celery workers.

The async engine (asyncpg) cannot be used inside sync Celery tasks,
so we create a parallel sync engine using psycopg2.

Requires: psycopg2-binary
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings


def _build_sync_url() -> str:
    """Convert DATABASE_URL to sync psycopg2 with SSL for external hosts."""
    url = settings.database_url
    url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    if "localhost" not in url and "sslmode" not in url:
        sep = "&" if "?" in url else "?"
        url += f"{sep}sslmode=require"
    return url


SYNC_DATABASE_URL = _build_sync_url()
engine = create_engine(SYNC_DATABASE_URL, pool_pre_ping=True, pool_size=5)
SyncSessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
