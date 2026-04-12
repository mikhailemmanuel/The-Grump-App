#!/usr/bin/env python3
"""Standalone migration script for production deployment.

Runs Alembic migrations without importing the full app.
This avoids import-time side effects (engine creation, geoalchemy2, etc.).

IMPORTANT: Uses os._exit() instead of sys.exit() to avoid Fly.io
interpreting Python's SystemExit cleanup as an abnormal exit (-1).
"""
import os
import traceback


def main() -> int:
    """Run migrations. Returns 0 on success, 1 on failure."""
    print("=== FoodGrump Migration Script ===", flush=True)

    import sys
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, app_dir)
    os.chdir(app_dir)

    print(f"Working dir: {os.getcwd()}", flush=True)

    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        print("ERROR: DATABASE_URL not set", flush=True)
        return 1

    # Convert to sync psycopg2 driver
    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    if sync_url.startswith("postgresql://"):
        sync_url = sync_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    # Ensure SSL for Supabase / external Postgres
    if "sslmode" not in sync_url:
        separator = "&" if "?" in sync_url else "?"
        sync_url += f"{separator}sslmode=require"

    print(f"DB host: {sync_url.split('@')[1].split('/')[0] if '@' in sync_url else 'unknown'}", flush=True)

    # Test connection
    print("Testing database connection...", flush=True)
    try:
        from sqlalchemy import create_engine, text, inspect
        engine = create_engine(sync_url, pool_pre_ping=True, pool_size=1, max_overflow=0)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print(f"Connection OK: {result.scalar()}", flush=True)
    except Exception as e:
        print(f"ERROR: Cannot connect to database: {e}", flush=True)
        traceback.print_exc()
        return 1

    # Check migration state
    print("Checking migration state...", flush=True)
    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        has_alembic = "alembic_version" in existing_tables

        if has_alembic:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT version_num FROM alembic_version"))
                versions = [row[0] for row in result]
                if "001_initial" in versions:
                    print("  Migration 001_initial already applied — nothing to do.", flush=True)
                    engine.dispose()
                    print("=== Migrations complete! ===", flush=True)
                    return 0

        # Clean partial state if needed
        has_our_tables = "venues" in existing_tables
        if has_our_tables:
            print("  Partial state detected — cleaning up...", flush=True)
            with engine.connect() as conn:
                for t in ["scrape_jobs", "custom_list_items", "custom_lists",
                          "saved_venues", "want_to_go", "venue_summaries",
                          "review_photos", "user_reviews", "users",
                          "city_rankings", "reservation_links", "recommendations", "venues"]:
                    conn.execute(text(f'DROP TABLE IF EXISTS "{t}" CASCADE'))
                for en in ["scrape_status", "list_entity_type", "verdict_type",
                           "platform_type", "source_type", "entity_type"]:
                    conn.execute(text(f"DROP TYPE IF EXISTS {en} CASCADE"))
                if has_alembic:
                    conn.execute(text("DELETE FROM alembic_version"))
                conn.commit()
            print("  Cleanup done.", flush=True)
        else:
            # Check orphan types
            with engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT typname FROM pg_type WHERE typname IN "
                    "('entity_type','source_type','platform_type','verdict_type','list_entity_type','scrape_status')"
                ))
                existing_types = [row[0] for row in result]
                if existing_types:
                    for en in existing_types:
                        conn.execute(text(f"DROP TYPE IF EXISTS {en} CASCADE"))
                    if has_alembic:
                        conn.execute(text("DELETE FROM alembic_version"))
                    conn.commit()
                    print(f"  Cleaned orphan types: {existing_types}", flush=True)
    except Exception as e:
        print(f"WARNING: State check failed (non-fatal): {e}", flush=True)

    # Run Alembic
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
        return 1
    finally:
        try:
            engine.dispose()
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    # Use os._exit() to avoid Fly.io misinterpreting Python's SystemExit
    # cleanup as an abnormal termination (exit code -1).
    rc = 1
    try:
        rc = main()
    except Exception:
        traceback.print_exc()
        rc = 1
    finally:
        os._exit(rc)
