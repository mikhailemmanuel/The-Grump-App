"""Alembic environment configuration — uses SYNC engine for migrations.

Designed to work both:
- Locally: `alembic upgrade head` (reads from app.config)
- In production: via scripts/migrate.py which passes URL directly via config
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool, MetaData

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Try to import app models for metadata; fall back to empty metadata
# (the migration files are self-contained and don't need ORM metadata)
target_metadata: MetaData
try:
    # Ensure app is importable
    _app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _app_dir not in sys.path:
        sys.path.insert(0, _app_dir)

    from app.database import Base
    import app.models  # noqa: F401
    target_metadata = Base.metadata
except Exception:
    # If imports fail (e.g., geoalchemy2 issues, missing deps),
    # use empty metadata — migration files are self-contained
    target_metadata = MetaData()


def _get_url() -> str:
    """Get database URL — prefer alembic config (set by migrate.py), fall back to env."""
    url = config.get_main_option("sqlalchemy.url")
    if url and "localhost" not in url and "password" not in url:
        # URL was set by migrate.py — already sync + SSL
        return url
    # Fall back to env var
    url = os.environ.get("DATABASE_URL", url or "")
    url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    if "sslmode" not in url:
        sep = "&" if "?" in url else "?"
        url += f"{sep}sslmode=require"
    return url


def run_migrations_offline() -> None:
    url = _get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = _get_url()
    connectable = create_engine(url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
