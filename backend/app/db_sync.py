"""
Synchronous SQLAlchemy engine + session for Celery workers.

The async engine (asyncpg) cannot be used inside sync Celery tasks,
so we create a parallel sync engine using psycopg2.

Requires: psycopg2-binary
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings

SYNC_DATABASE_URL = settings.database_url.replace(
    "postgresql+asyncpg", "postgresql+psycopg2"
)

engine = create_engine(SYNC_DATABASE_URL, pool_pre_ping=True, pool_size=5)
SyncSessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
