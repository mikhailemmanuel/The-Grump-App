#!/usr/bin/env python3
"""Standalone migration script for production deployment.

Runs Alembic migrations without importing the full app.
This avoids import-time side effects (engine creation, geoalchemy2, etc.).
"""
import os
import sys
import traceback

def main():
    print("=== FoodGrump Migration Script ===", flush=True)

    # Ensure we can import app modules
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, app_dir)
    os.chdir(app_dir)

    print(f"Working dir: {os.getcwd()}", flush=True)
    print(f"Python path: {sys.path[:3]}", flush=True)

    # Read DATABASE_URL directly from env (don't import app.config to avoid side effects)
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        print("ERROR: DATABASE_URL not set", flush=True)
        sys.exit(1)

    # Convert to sync psycopg2 driver
    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    if sync_url.startswith("postgresql://"):
        sync_url = sync_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    # Ensure SSL for Supabase / external Postgres
    if "sslmode" not in sync_url:
        separator = "&" if "?" in sync_url else "?"
        sync_url += f"{separator}sslmode=require"

    print(f"DB host: {sync_url.split('@')[1].split('/')[0] if '@' in sync_url else 'unknown'}", flush=True)

    # Test connection first
    print("Testing database connection...", flush=True)
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(sync_url, pool_pre_ping=True)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print(f"Connection OK: {result.scalar()}", flush=True)
        engine.dispose()
    except Exception as e:
        print(f"ERROR: Cannot connect to database: {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)

    # Run Alembic migrations
    print("Running Alembic migrations...", flush=True)
    try:
        from alembic.config import Config
        from alembic import command

        alembic_cfg = Config(os.path.join(app_dir, "alembic.ini"))
        alembic_cfg.set_main_option("sqlalchemy.url", sync_url)
        alembic_cfg.set_main_option("script_location", os.path.join(app_dir, "alembic"))

        command.upgrade(alembic_cfg, "head")
        print("=== Migrations complete! ===", flush=True)
    except Exception as e:
        print(f"ERROR: Migration failed: {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
